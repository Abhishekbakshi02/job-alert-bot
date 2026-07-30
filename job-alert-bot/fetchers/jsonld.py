"""
Generic fallback: many career pages embed schema.org JobPosting structured
data (inside a <script type="application/ld+json"> tag) purely for Google
Jobs / SEO purposes. When present, this lets us read real job listings
straight from the page's initial HTML - no need to know the platform, and
no headless browser required, since search-engine-facing structured data
is always present in the raw page source (unlike content injected by JS
after the page loads).
"""

import json
import re
import requests
from title_filter import title_matches


def find_candidate_jobs_via_jsonld(url: str):
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    html = response.text

    script_blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE,
    )
    if not script_blocks:
        return None

    found_any_jobposting = False
    candidates = []

    for block in script_blocks:
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue

        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("@type") != "JobPosting":
                continue
            found_any_jobposting = True

            title = entry.get("title", "")
            if not title_matches(title):
                continue

            location = "Not specified"
            job_location = entry.get("jobLocation")
            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                if isinstance(address, dict):
                    location = address.get("addressLocality") or address.get("addressCountry") or location
            if entry.get("jobLocationType") == "TELECOMMUTE":
                location = "Remote"

            candidates.append({
                "title": title,
                "location": {"name": location},
                "absolute_url": entry.get("url", url),
                "content": entry.get("description", ""),
            })

    return candidates if found_any_jobposting else None
