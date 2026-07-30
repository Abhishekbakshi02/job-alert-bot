"""
Fetches job listings from a company's Workable-hosted career page.
Workable exposes a free, public, no-auth JSON endpoint:
    GET https://www.workable.com/api/accounts/{account_slug}?details=true
"""

import requests
from title_filter import title_matches


def fetch_workable_jobs(account_slug: str) -> list[dict]:
    url = f"https://www.workable.com/api/accounts/{account_slug}"
    response = requests.get(url, params={"details": "true"}, timeout=15)
    response.raise_for_status()
    raw_jobs = response.json().get("jobs", [])

    normalized = []
    for job in raw_jobs:
        location = job.get("location") or {}
        location_name = location.get("location_str") or "Not specified"
        normalized.append({
            "title": job.get("title", ""),
            "location": {"name": location_name},
            "absolute_url": job.get("url", ""),
            "content": job.get("description", ""),
        })
    return normalized


def find_candidate_jobs(account_slug: str) -> list[dict]:
    all_jobs = fetch_workable_jobs(account_slug)
    return [job for job in all_jobs if title_matches(job["title"])]
