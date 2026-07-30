"""
The main entry point - this is what GitHub Actions runs every day.
"""

from platform_detector import get_jobs_for_url
from classifier import check_jobs_batch
from notifier import send_job_alert
from seen_jobs import load_seen, save_seen

# Just (Display Name, career page URL) - nothing else needed.
COMPANIES = [
    ("NewsBreak", "https://job-boards.greenhouse.io/newsbreak"),
    ("QuantumLoopAI", "https://apply.workable.com/quantumloopai/"),
    ("OpenAI", "https://jobs.ashbyhq.com/openai"),
    ("Anthropic", "https://jobs.ashbyhq.com/anthropic"),
    ("ElevenLabs", "https://jobs.ashbyhq.com/elevenlabs"),
    ("SafetyWing", "https://jobs.ashbyhq.com/safetywing"),
    ("Supabase", "https://jobs.ashbyhq.com/supabase"),
    ("Modal", "https://jobs.ashbyhq.com/modal"),
    ("Render", "https://jobs.ashbyhq.com/render"),
    ("Tailscale", "https://jobs.ashbyhq.com/tailscale"),
    ("Ramp", "https://jobs.ashbyhq.com/ramp"),
    ("Notion", "https://jobs.ashbyhq.com/notion"),
    ("Retool", "https://jobs.ashbyhq.com/retool"),
    ("Clay", "https://jobs.ashbyhq.com/clay"),
    ("Vapi", "https://jobs.ashbyhq.com/vapi"),
    ("Perplexity", "https://jobs.ashbyhq.com/perplexity-ai"),
    ("Cursor", "https://jobs.ashbyhq.com/anysphere"),
    ("Decagon", "https://jobs.ashbyhq.com/decagon"),
    ("Mercor", "https://jobs.ashbyhq.com/mercor"),
    ("PostHog", "https://jobs.lever.co/posthog"),
    ("Smart Working Solutions", "https://jobs.lever.co/smart-working-solutions"),
    ("H1", "https://jobs.lever.co/h1"),
    ("Plaid", "https://jobs.lever.co/plaid"),
    ("Rippling", "https://jobs.lever.co/rippling"),
    ("Zapier", "https://job-boards.greenhouse.io/zapier"),
    ("Vercel", "https://job-boards.greenhouse.io/vercel"),
    ("Stripe", "https://job-boards.greenhouse.io/stripe"),
    ("Figma", "https://job-boards.greenhouse.io/figma"),
    ("Datadog", "https://job-boards.greenhouse.io/datadog"),
    ("Canva", "https://job-boards.greenhouse.io/canva"),
    ("Clarium","https://jobs.ashbyhq.com/clarium"),
    ("TensorOps","https://job-boards.eu.greenhouse.io/tensorops"),
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
