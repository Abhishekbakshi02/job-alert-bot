"""
The main entry point - this is what GitHub Actions runs every day.
"""

from platform_detector import get_jobs_for_url
from classifier import check_jobs_batch
from notifier import send_job_alert
from seen_jobs import load_seen, save_seen

# Just (Display Name, career page URL) - nothing else needed.
COMPANIES = [
    ("Greenhouse", "https://job-boards.greenhouse.io/greenhouse"),
    ("NewsBreak", "https://job-boards.greenhouse.io/newsbreak"),
    ("QuantumLoopAI", "https://apply.workable.com/quantumloopai"),
]


def main():
    seen = load_seen()
    new_seen = set(seen)

    for company_name, career_url in COMPANIES:
        try:
            candidates = get_jobs_for_url(career_url)
        except Exception as e:
            print(f"[WARN] Failed to fetch {company_name}: {e}")
            continue

        print(f"[INFO] Checked {company_name}: {len(candidates)} title match(es)")

        new_candidates = [job for job in candidates if job["absolute_url"] not in seen]
        if not new_candidates:
            continue

        try:
            results = check_jobs_batch([
                {"title": j["title"], "location": j["location"]["name"], "content": j.get("content", "")}
                for j in new_candidates
            ])
        except Exception as e:
            print(f"[WARN] Could not classify jobs at {company_name}: {e}")
            continue

        for job, result in zip(new_candidates, results):
            new_seen.add(job["absolute_url"])
            if result.get("matches"):
                send_job_alert(
                    title=job["title"], company=company_name,
                    location=job["location"]["name"], url=job["absolute_url"],
                    reason=result.get("reason", ""),
                )
                print(f"[MATCH] Emailed: {job['title']} at {company_name}")
            else:
                print(f"[SKIP] {job['title']} at {company_name} - {result.get('reason')}")

    save_seen(new_seen)


if __name__ == "__main__":
    main()
