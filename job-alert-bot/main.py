"""
The main entry point - this is what GitHub Actions runs every day.

Fetching runs in parallel across companies. Classification and resume
tailoring stay sequential - they share an AI rate-limit budget.

A matched job is only marked "seen" AFTER its email successfully sends -
not before. If sending fails for any reason, the match stays un-seen
and gets retried on the next run, rather than being silently lost.
"""

import os
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from platform_detector import get_jobs_for_url
from classifier import check_jobs_batch
from notifier import send_job_alert
from seen_jobs import load_seen, save_seen
from companies import load_companies, save_companies
from resume_tailor import tailor_resume
from resume_builder import build_resume_pdf
from gemini_errors import GeminiUnavailable

RESUME_DATA_FILE = "resume_data.json"
RESUME_OUTPUT_DIR = "tailored_resumes"
MAX_FETCH_WORKERS = 10


def is_dead_url_error(e: Exception) -> bool:
    if isinstance(e, requests.exceptions.HTTPError):
        return e.response is not None and e.response.status_code == 404
    if isinstance(e, requests.exceptions.ConnectionError):
        return True
    return False


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")[:60]


def _fetch_one(index: int, company: dict):
    try:
        candidates = get_jobs_for_url(company["url"])
        return index, company, candidates, None
    except Exception as e:
        return index, company, None, e


def main():
    with open(RESUME_DATA_FILE) as f:
        resume_data = json.load(f)
    os.makedirs(RESUME_OUTPUT_DIR, exist_ok=True)

    companies = load_companies()
    seen = load_seen()
    new_seen = set(seen)
    still_valid = []
    gemini_down = False

    print(f"[INFO] Fetching {len(companies)} companies (up to {MAX_FETCH_WORKERS} at a time)...")
    fetch_results = [None] * len(companies)
    with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:
        futures = [executor.submit(_fetch_one, i, company) for i, company in enumerate(companies)]
        for future in as_completed(futures):
            index, company, candidates, fetch_error = future.result()
            fetch_results[index] = (company, candidates, fetch_error)

    for company, candidates, fetch_error in fetch_results:
        company_name, career_url = company["name"], company["url"]

        if fetch_error is not None:
            if is_dead_url_error(fetch_error):
                print(f"[REMOVED] {company_name}: URL appears dead ({fetch_error}) - removing from list")
                continue
            print(f"[WARN] Failed to fetch {company_name}: {fetch_error}")
            still_valid.append(company)
            continue

        still_valid.append(company)
        print(f"[INFO] Checked {company_name}: {len(candidates)} title match(es)")

        if gemini_down:
            continue

        new_candidates = [job for job in candidates if job["absolute_url"] not in seen]
        if not new_candidates:
            continue

        try:
            results = check_jobs_batch([
                {"title": job["title"], "location": job["location"]["name"], "content": job.get("content", "")}
                for job in new_candidates
            ])
        except GeminiUnavailable as e:
            print(f"[WARN] AI provider(s) unavailable ({e}) - stopping further AI calls "
                  f"for the rest of this run. Remaining companies get re-checked next run.")
            gemini_down = True
            continue
        except Exception as e:
            print(f"[WARN] Could not classify jobs at {company_name}: {e}")
            continue

        for job, result in zip(new_candidates, results):
            if not result.get("matches"):
                new_seen.add(job["absolute_url"])
                print(f"[SKIP] {job['title']} at {company_name} - {result.get('reason')}")
                continue

            time.sleep(3)
            resume_path = None
            application_answers = []
            try:
                tailor_result = tailor_resume(resume_data, job["title"], job.get("content", ""))
                resume_path = os.path.join(
                    RESUME_OUTPUT_DIR,
                    f"Resume_{_safe_filename(company_name)}_{_safe_filename(job['title'])}.pdf",
                )
                build_resume_pdf(tailor_result["resume"], resume_path)
                application_answers = tailor_result["application_answers"]
                if tailor_result["used_fallback"]:
                    print(f"[INFO] Used untailored fallback resume for '{job['title']}' - AI tailoring failed, "
                          f"but a complete resume was still attached")
                else:
                    print(f"[INFO] Keyword coverage for '{job['title']}': {tailor_result['coverage_percent']}% "
                          f"({len(tailor_result['matched_keywords'])} of the JD's key requirements matched)")
            except Exception as e:
                print(f"[WARN] Could not produce a resume PDF for '{job['title']}' at {company_name}: {e}")
                resume_path = None

            try:
                send_job_alert(
                    title=job["title"],
                    company=company_name,
                    location=job["location"]["name"],
                    url=job["absolute_url"],
                    reason=result.get("reason", ""),
                    resume_path=resume_path,
                    application_answers=application_answers,
                )
                new_seen.add(job["absolute_url"])
                suffix = "with tailored resume" if resume_path else "resume tailoring failed - sent without attachment"
                if application_answers:
                    suffix += f", {len(application_answers)} application question(s) answered"
                print(f"[MATCH] Emailed: {job['title']} at {company_name} ({suffix})")
            except Exception as e:
                print(f"[WARN] Failed to send email for '{job['title']}' at {company_name}: {e} - "
                      f"not marking as seen, will retry next run")

    save_seen(new_seen)

    if len(still_valid) != len(companies):
        removed_count = len(companies) - len(still_valid)
        save_companies(still_valid)
        print(f"[INFO] Removed {removed_count} dead compan(ies) from companies.json")


if __name__ == "__main__":
    main()
