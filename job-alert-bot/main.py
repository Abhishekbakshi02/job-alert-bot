"""
The main entry point - this is what GitHub Actions runs every day.
"""

from fetchers.greenhouse import find_candidate_jobs
from classifier import check_job
from notifier import send_job_alert
from seen_jobs import load_seen, save_seen

GREENHOUSE_COMPANIES = [
    ("Greenhouse", "greenhouse"),
    ("NewsBreak", "newsbreak"),
]


def main():
    seen = load_seen()
    new_seen = set(seen)

    for company_name, board_token in GREENHOUSE_COMPANIES:
        try:
            candidates = find_candidate_jobs(board_token)
        except Exception as e:
            print(f"[WARN] Failed to fetch {company_name}: {e}")
            continue

        print(f"[INFO] Checked {company_name}: {len(candidates)} title match(es)")

        for job in candidates:
            job_key = job["absolute_url"]
            if job_key in seen:
                continue  # already handled this one in a previous run

            try:
                result = check_job(
                    title=job["title"],
                    location=job["location"]["name"],
                    content=job.get("content", ""),
                )
            except Exception as e:
                print(f"[WARN] Could not classify '{job['title']}' at {company_name}: {e}")
                continue  # leave it un-seen so we retry it next run

            new_seen.add(job_key)

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


if __name__ == "__main__":
    main()
