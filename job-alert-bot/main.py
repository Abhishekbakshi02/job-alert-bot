"""
The main entry point - this is what GitHub Actions runs every day.

Companies are loaded from companies.json. A company only gets removed
automatically if its URL is confirmed dead (404 / unresolvable domain).
For every genuine job match, a resume tailored to that job's description
is generated and attached to the notification email.

If Gemini itself proves unavailable (retries exhausted), a circuit
breaker stops making further Gemini calls for the rest of the run -
dead-link cleanup keeps running cheaply, but no more time is wasted
retrying a call that will predictably keep failing.
"""

import os
import re
import json
import time
import requests

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


def is_dead_url_error(e: Exception) -> bool:
    if isinstance(e, requests.exceptions.HTTPError):
        return e.response is not None and e.response.status_code == 404
    if isinstance(e, requests.exceptions.ConnectionError):
        return True
    return False


def _safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")[:60]


def main():
    with open(RESUME_DATA_FILE) as f:
        resume_data = json.load(f)
    os.makedirs(RESUME_OUTPUT_DIR, exist_ok=True)

    companies = load_companies()
    seen = load_seen()
    new_seen = set(seen)
    still_valid = []
    gemini_down = False

    for company in companies:
        company_name, career_url = company["name"], company["url"]

        try:
            candidates = get_jobs_for_url(career_url)
        except Exception as e:
            if is_dead_url_error(e):
                print(f"[REMOVED] {company_name}: URL appears dead ({e}) - removing from list")
                continue
            print(f"[WARN] Failed to fetch {company_name}: {e}")
            still_valid.append(company)
            continue

        still_valid.append(company)
        print(f"[INFO] Checked {company_name}: {len(candidates)} title match(es)")

        if gemini_down:
            continue  # dead-link cleanup still runs; skip anything needing Gemini

        new_candidates = [job for job in candidates if job["absolute_url"] not in seen]
        if not new_candidates:
            continue

        try:
            results = check_jobs_batch([
                {
                    "title": job["title"],
                    "location": job["location"]["name"],
                    "content": job.get("content", ""),
                }
                for job in new_candidates
            ])
        except GeminiUnavailable as e:
            print(f"[WARN] Gemini appears unavailable ({e}) - stopping further Gemini "
                  f"calls for the rest of this run. Remaining companies get re-checked next run.")
            gemini_down = True
            continue
        except Exception as e:
            print(f"[WARN] Could not classify jobs at {company_name}: {e}")
            continue

        for job, result in zip(new_candidates, results):
            new_seen.add(job["absolute_url"])

            if not result.get("matches"):
                print(f"[SKIP] {job['title']} at {company_name} - {result.get('reason')}")
                continue

            time.sleep(3)  # brief pause before the second Gemini call (resume tailoring)
            resume_path = None
            try:
                tailor_result = tailor_resume(resume_data, job["title"], job.get("content", ""))
                resume_path = os.path.join(
                    RESUME_OUTPUT_DIR,
                    f"Resume_{_safe_filename(company_name)}_{_safe_filename(job['title'])}.pdf",
                )
                build_resume_pdf(tailor_result["resume"], resume_path)
                print(f"[INFO] Keyword coverage for '{job['title']}': {tailor_result['coverage_percent']}% "
                      f"({len(tailor_result['matched_keywords'])} of the JD's key requirements matched)")
            except GeminiUnavailable as e:
                print(f"[WARN] Gemini appears unavailable while tailoring ({e}) - stopping "
                      f"further Gemini calls for the rest of this run.")
                gemini_down = True
                resume_path = None
            except Exception as e:
                print(f"[WARN] Resume tailoring failed for '{job['title']}' at {company_name}: {e}")
                resume_path = None

            send_job_alert(
                title=job["title"],
                company=company_name,
                location=job["location"]["name"],
                url=job["absolute_url"],
                reason=result.get("reason", ""),
                resume_path=resume_path,
            )
            suffix = "with tailored resume" if resume_path else "resume tailoring failed - sent without attachment"
            print(f"[MATCH] Emailed: {job['title']} at {company_name} ({suffix})")

    save_seen(new_seen)

    if len(still_valid) != len(companies):
        removed_count = len(companies) - len(still_valid)
        save_companies(still_valid)
        print(f"[INFO] Removed {removed_count} dead compan(ies) from companies.json")


if __name__ == "__main__":
    main()
