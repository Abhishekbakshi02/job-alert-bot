"""
Fetches job listings from a company's Lever-hosted career page.
Lever exposes a free, public, no-auth JSON API:
    GET https://api.lever.co/v0/postings/{company}?mode=json
"""

import requests
from title_filter import title_matches


def fetch_lever_jobs(company_slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{company_slug}"
    response = requests.get(url, params={"mode": "json"}, timeout=15)
    response.raise_for_status()
    raw_jobs = response.json()

    normalized = []
    for job in raw_jobs:
        location_name = job.get("categories", {}).get("location") or "Not specified"
        description = job.get("descriptionPlain") or job.get("description", "")
        normalized.append({
            "title": job.get("text", ""),
            "location": {"name": location_name},
            "absolute_url": job.get("hostedUrl", ""),
            "content": description,
        })
    return normalized


def find_candidate_jobs(company_slug: str) -> list[dict]:
    all_jobs = fetch_lever_jobs(company_slug)
    return [job for job in all_jobs if title_matches(job["title"])]
