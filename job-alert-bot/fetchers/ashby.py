"""
Fetches job listings from a company's Ashby-hosted career page.
Ashby exposes a free, public, no-auth JSON API:
    GET https://api.ashbyhq.com/posting-api/job-board/{company_slug}
"""

import requests
from title_filter import title_matches


def fetch_ashby_jobs(company_slug: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    raw_jobs = response.json().get("jobs", [])

    normalized = []
    for job in raw_jobs:
        location_name = job.get("location") or "Not specified"
        description = job.get("descriptionHtml") or job.get("description", "")
        normalized.append({
            "title": job.get("title", ""),
            "location": {"name": location_name},
            "absolute_url": job.get("jobUrl") or job.get("applyUrl", ""),
            "content": description,
        })
    return normalized


def find_candidate_jobs(company_slug: str) -> list[dict]:
    all_jobs = fetch_ashby_jobs(company_slug)
    return [job for job in all_jobs if title_matches(job["title"])]
