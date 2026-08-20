"""
The main entry point - this is what GitHub Actions runs every day.

Fetching runs in parallel across companies. Classification and resume
tailoring stay sequential - they share an AI rate-limit budget.

A matched job is only marked "seen" AFTER its email successfully sends -
not before. If sending fails for any reason, the match stays un-seen
and gets retried on the next run, rather than being silently lost.

Seen jobs are saved once per company, not after every individual job.
If processing fails part-way through a company, all successfully
processed jobs from that company are saved as one batch before moving
to the next company.
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
    # ---------------------------------------------------------
    # Load resume data
    # ---------------------------------------------------------
    with open(RESUME_DATA_FILE) as f:
        resume_data = json.load(f)

    os.makedirs(RESUME_OUTPUT_DIR, exist_ok=True)

    # ---------------------------------------------------------
    # Load companies and already-seen jobs
    # ---------------------------------------------------------
    companies = load_companies()
    seen = load_seen()

    # Keep the complete set in memory during the run.
    # We only write it to disk once per company.
    new_seen = set(seen)

    still_valid = []
    gemini_down = False

    # ---------------------------------------------------------
    # STEP 1: Fetch all companies in parallel
    # ---------------------------------------------------------
    print(
        f"[INFO] Fetching {len(companies)} companies "
        f"(up to {MAX_FETCH_WORKERS} at a time)..."
    )

    fetch_results = [None] * len(companies)

    with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:

        futures = [
            executor.submit(_fetch_one, i, company)
            for i, company in enumerate(companies)
        ]

        for future in as_completed(futures):
            index, company, candidates, fetch_error = future.result()

            fetch_results[index] = (
                company,
                candidates,
                fetch_error,
            )

    # ---------------------------------------------------------
    # STEP 2: Process companies sequentially
    # ---------------------------------------------------------
    for company, candidates, fetch_error in fetch_results:

        company_name = company["name"]
        career_url = company["url"]

        # -----------------------------------------------------
        # Handle fetch errors
        # -----------------------------------------------------
        if fetch_error is not None:

            if is_dead_url_error(fetch_error):

                print(
                    f"[REMOVED] {company_name}: "
                    f"URL appears dead ({fetch_error}) - "
                    f"removing from list"
                )

                continue

            print(
                f"[WARN] Failed to fetch "
                f"{company_name}: {fetch_error}"
            )

            still_valid.append(company)
            continue

        still_valid.append(company)

        print(
            f"[INFO] Checked {company_name}: "
            f"{len(candidates)} title match(es)"
        )

        # -----------------------------------------------------
        # If Gemini is already unavailable, don't make more AI
        # calls for the rest of this run.
        # -----------------------------------------------------
        if gemini_down:
            continue

        # -----------------------------------------------------
        # Only process jobs that haven't been seen before
        # -----------------------------------------------------
        new_candidates = [
            job
            for job in candidates
            if job["absolute_url"] not in seen
        ]

        if not new_candidates:
            continue

        # -----------------------------------------------------
        # CLASSIFICATION
        # -----------------------------------------------------
        try:

            results = check_jobs_batch(
                [
                    {
                        "title": job["title"],
                        "location": job["location"]["name"],
                        "content": job.get("content", ""),
                    }
                    for job in new_candidates
                ]
            )

        except GeminiUnavailable as e:

            print(
                f"[WARN] AI provider(s) unavailable ({e}) - "
                f"stopping further AI calls for the rest of this run. "
                f"Remaining companies get re-checked next run."
            )

            gemini_down = True
            continue

        except Exception as e:

            print(
                f"[WARN] Could not classify jobs "
                f"at {company_name}: {e}"
            )

            # Nothing was successfully classified/processed.
            # Do NOT change seen_jobs.
            continue

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # company_seen contains jobs successfully handled for
        # THIS company during THIS run.
        #
        # It stays in memory while processing the company.
        # We save it only once:
        #
        #   1. When the company finishes normally
        #   2. When an individual job fails
        #
        # This prevents one disk write per job.
        # -----------------------------------------------------
        company_seen = set()

        # -----------------------------------------------------
        # PROCESS EACH JOB
        # -----------------------------------------------------
        for job, result in zip(new_candidates, results):

            try:

                # -------------------------------------------------
                # NON-MATCHING JOB
                #
                # This job was successfully classified and found
                # irrelevant, so it can safely be marked as seen.
                # -------------------------------------------------
                if not result.get("matches"):

                    company_seen.add(
                        job["absolute_url"]
                    )

                    print(
                        f"[SKIP] {job['title']} at "
                        f"{company_name} - "
                        f"{result.get('reason')}"
                    )

                    continue

                # -------------------------------------------------
                # MATCHING JOB
                # -------------------------------------------------
                time.sleep(3)

                resume_path = None
                application_answers = []

                # -------------------------------------------------
                # Generate tailored resume
                # -------------------------------------------------
                try:

                    tailor_result = tailor_resume(
                        resume_data,
                        job["title"],
                        job.get("content", ""),
                    )

                    resume_path = os.path.join(
                        RESUME_OUTPUT_DIR,
                        (
                            f"Resume_"
                            f"{_safe_filename(company_name)}_"
                            f"{_safe_filename(job['title'])}.pdf"
                        ),
                    )

                    build_resume_pdf(
                        tailor_result["resume"],
                        resume_path,
                    )

                    application_answers = (
                        tailor_result["application_answers"]
                    )

                    if tailor_result["used_fallback"]:

                        print(
                            f"[INFO] Used untailored fallback resume "
                            f"for '{job['title']}' - AI tailoring "
                            f"failed, but a complete resume was "
                            f"still attached"
                        )

                    else:

                        print(
                            f"[INFO] Keyword coverage for "
                            f"'{job['title']}': "
                            f"{tailor_result['coverage_percent']}% "
                            f"("
                            f"{len(tailor_result['matched_keywords'])} "
                            f"of the JD's key requirements matched"
                            f")"
                        )

                except Exception as e:

                    print(
                        f"[WARN] Could not produce a resume PDF "
                        f"for '{job['title']}' at "
                        f"{company_name}: {e}"
                    )

                    # Resume failure does NOT stop the job.
                    # Email can still be sent without attachment.
                    resume_path = None

                # -------------------------------------------------
                # SEND EMAIL
                # -------------------------------------------------
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

                    # ---------------------------------------------
                    # IMPORTANT:
                    #
                    # Only mark the job as seen AFTER the email
                    # successfully sends.
                    # ---------------------------------------------
                    company_seen.add(
                        job["absolute_url"]
                    )

                    suffix = (
                        "with tailored resume"
                        if resume_path
                        else
                        "resume tailoring failed - "
                        "sent without attachment"
                    )

                    if application_answers:
                        suffix += (
                            f", {len(application_answers)} "
                            f"application question(s) answered"
                        )

                    print(
                        f"[MATCH] Emailed: "
                        f"{job['title']} at {company_name} "
                        f"({suffix})"
                    )

                except Exception as e:

                    # -------------------------------------------------
                    # EMAIL FAILED
                    #
                    # IMPORTANT:
                    # Do NOT add this job to company_seen.
                    #
                    # Therefore it will NOT be saved to seen_jobs.json
                    # and will be retried next run.
                    # -------------------------------------------------
                    print(
                        f"[WARN] Failed to send email for "
                        f"'{job['title']}' at {company_name}: {e} - "
                        f"not marking as seen, will retry next run"
                    )

                    # ---------------------------------------------
                    # Save everything that succeeded BEFORE this
                    # failed job.
                    #
                    # This is ONE I/O operation for the company,
                    # not one operation per job.
                    # ---------------------------------------------
                    new_seen.update(company_seen)
                    save_seen(new_seen)

                    print(
                        f"[INFO] Saved "
                        f"{len(company_seen)} successfully "
                        f"processed job(s) for {company_name}"
                    )

                    # ---------------------------------------------
                    # Stop this company and move to next company.
                    # ---------------------------------------------
                    break

            except Exception as e:

                # -------------------------------------------------
                # UNEXPECTED ERROR
                #
                # If something unexpected happens while processing
                # this job, save all jobs successfully processed
                # before it and move to the next company.
                # -------------------------------------------------
                print(
                    f"[ERROR] Unexpected failure processing "
                    f"'{job['title']}' at {company_name}: {e}"
                )

                new_seen.update(company_seen)
                save_seen(new_seen)

                print(
                    f"[INFO] Saved "
                    f"{len(company_seen)} successfully "
                    f"processed job(s) for {company_name}"
                )

                break

        else:

            # -----------------------------------------------------
            # The 'for' loop completed normally.
            #
            # No job caused a break.
            #
            # Save all successfully processed jobs for this company
            # in ONE operation.
            # -----------------------------------------------------
            new_seen.update(company_seen)
            save_seen(new_seen)

            print(
                f"[INFO] Saved "
                f"{len(company_seen)} processed job(s) "
                f"for {company_name}"
            )

    # ---------------------------------------------------------
    # Remove dead companies from companies.json
    # ---------------------------------------------------------
    if len(still_valid) != len(companies):

        removed_count = (
            len(companies) - len(still_valid)
        )

        save_companies(still_valid)

        print(
            f"[INFO] Removed {removed_count} dead "
            f"compan(ies) from companies.json"
        )


if __name__ == "__main__":
    main()
