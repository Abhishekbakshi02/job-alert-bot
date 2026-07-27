"""
The main entry point - this is what GitHub Actions runs every day.
"""

from fetchers.greenhouse import find_candidate_jobs
from classifier import check_jobs_batch
from notifier import send_job_alert
from seen_jobs import load_seen, save_seen

GREENHOUSE_COMPANIES = [
    ("Greenhouse", "greenhouse"),
    ("Workable","workable"),
    ("NewsBreak", "newsbreak"),
    ("QuantumLoopAI","quantumloopai"),
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

        new_candidates = [job for job in candidates if job["absolute_url"] not in seen]
        if not new_candidates:
            continue  # nothing new to classify at this company

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
            continue  # leave these un-seen so we retry them next run

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


if __name__ == "__main__":
    main()
