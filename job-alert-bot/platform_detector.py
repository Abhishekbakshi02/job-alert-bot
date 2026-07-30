"""
Given ANY company career page URL, figures out which ATS platform (if
any) hosts it and fetches that company's job listings - so we don't 
have to manually look up a "board token" again. Just give it the URL.
"""

import re
import requests
from urllib.parse import urlparse

from fetchers import greenhouse, lever, ashby
from fetchers.jsonld import find_candidate_jobs_via_jsonld

ATS_DOMAIN_PATTERNS = {
    "greenhouse.io": ("Greenhouse", greenhouse),
    "lever.co": ("Lever", lever),
    "ashbyhq.com": ("Ashby", ashby),
}


def _extract_slug(url: str) -> str:
    path_parts = [p for p in urlparse(url).path.split("/") if p]
    return path_parts[0] if path_parts else ""


def _detect_from_url(url: str):
    domain = urlparse(url).netloc.lower()
    for pattern, (platform, module) in ATS_DOMAIN_PATTERNS.items():
        if pattern in domain:
            slug = _extract_slug(url)
            if slug:
                return platform, module, slug
    return None


def _detect_from_page(response):
    final_result = _detect_from_url(response.url)
    if final_result:
        return final_result

    html = response.text
    for pattern, (platform, module) in ATS_DOMAIN_PATTERNS.items():
        match = re.search(rf'https?://[^"\'\s]*{re.escape(pattern)}[^"\'\s]*', html)
        if match:
            slug = _extract_slug(match.group(0))
            if slug:
                return platform, module, slug
    return None


def get_jobs_for_url(url: str) -> list:
    direct = _detect_from_url(url)
    if direct:
        platform, module, slug = direct
        print(f"[INFO] Detected {platform} directly from URL (slug: '{slug}')")
        return module.find_candidate_jobs(slug)

    response = requests.get(url, timeout=15, allow_redirects=True)
    response.raise_for_status()

    detected = _detect_from_page(response)
    if detected:
        platform, module, slug = detected
        print(f"[INFO] Detected {platform} embedded in the page (slug: '{slug}')")
        return module.find_candidate_jobs(slug)

    jsonld_jobs = find_candidate_jobs_via_jsonld(url)
    if jsonld_jobs is not None:
        print(f"[INFO] No known ATS platform, but found structured job data on the page")
        return jsonld_jobs

    raise ValueError(
        "No supported ATS platform detected and no structured job data found - "
        "this company's career page needs manual/custom handling."
    )
