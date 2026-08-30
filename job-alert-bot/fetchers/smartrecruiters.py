"""
Fetches job listings from a company's SmartRecruiters-hosted career page.
SmartRecruiters exposes a free, public, no-auth Posting API:
    GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings
Full descriptions need one extra call per posting (only done for actual
title-matches, to keep this efficient):
    GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings/{posting_id}

IMPORTANT: the "ref" field on a posting is a link to SmartRecruiters'
internal API (raw JSON, not a browsable page) - confirmed via their own
official docs example. It must NEVER be used as the link shown to the
user. postingUrl / applyUrl / jobAdUrl are the real public-facing pages.
"""

import requests
from title_filter import title_matches


def fetch_smartrecruiters_jobs(company_id: str) -> list[dict]:
    url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    raw_jobs = response.json().get("content", [])

    normalized = []
    for job in raw_jobs:
        location = job.get("location") or {}
        city = location.get("city", "")
        country = location.get("country", "")
        location_name = ", ".join(p for p in (city, country) if p) or "Not specified"

        # Deliberately does NOT include "ref" - that field is an internal
        # API URL, not a public page. See module docstring.
        public_url = job.get("postingUrl") or job.get("applyUrl") or job.get("jobAdUrl") or ""

        normalized.append({
            "title": job.get("name", ""),
            "location": {"name": location_name},
            "absolute_url": public_url,
            "content": "",
            "_id": job.get("id", ""),
        })
    return normalized


def _fetch_description(company_id: str, posting_id: str) -> str:
    url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings/{posting_id}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    sections = response.json().get("jobAd", {}).get("sections", {})
    parts = [s["text"] for s in sections.values() if isinstance(s, dict) and s.get("text")]
    return "\n\n".join(parts)


def find_candidate_jobs(company_id: str) -> list[dict]:
    all_jobs = fetch_smartrecruiters_jobs(company_id)
    candidates = [job for job in all_jobs if title_matches(job["title"]) and job["absolute_url"]]

    for job in candidates:
        try:
            job["content"] = _fetch_description(company_id, job["_id"])
        except Exception:
            pass
        job.pop("_id", None)

    return candidates
