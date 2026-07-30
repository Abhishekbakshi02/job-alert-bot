"""
The main entry point - this is what GitHub Actions runs every day.

Companies are loaded from companies.json (not hardcoded here). A company
only gets automatically REMOVED from that file if its URL is confirmed
dead - a 404, or a domain that doesn't resolve at all. Temporary issues
(rate limits, server errors, timeouts, "no supported platform detected")
are logged as warnings but the company stays in the list, since those
aren't proof the link is actually broken.
"""

import requests

from platform_detector import get_jobs_for_url
from classifier import check_jobs_batch
from notifier import send_job_alert
from seen_jobs import load_seen, save_seen
from companies import load_companies, save_companies


def is_dead_url_error(e: Exception) -> bool:
    """True only for errors that mean the URL itself is broken or wrong."""
    if isinstance(e, requests.exceptions.HTTPError):
        return e.response is not None and e.response.status_code == 404
    if isinstance(e, requests.exceptions.ConnectionError):
        return True
    return False


def main():
    companies = load_companies()
    seen = load_seen()
    new_seen = set(seen)
    still_valid = []

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
        except Exception as e:
            print(f"[WARN] Could not classify jobs at {company_name}: {e}")
            continue

        for job, result in zip(new_candidates, results):
            new_seen.add(job["absolute_url"])

            if result.get("matches"):
                send_job_alert(
                    title=job["title"],
                    company=company_name,
                    location=job["location"]["name"],
                    url=job["absolute_url"],
                    reason=result.get("reason", ""),
                )
                print(f"[MATCH] Emailed: {job['title']} at {company_name}")
            else:
                print(f"[SKIP] {job['title']} at {company_name} - {result.get('reason')}")

    save_seen(new_seen)

    if len(still_valid) != len(companies):
        removed_count = len(companies) - len(still_valid)
        save_companies(still_valid)
        print(f"[INFO] Removed {removed_count} dead compan(ies) from companies.json")


if __name__ == "__main__":
    main()
