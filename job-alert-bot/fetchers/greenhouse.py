"""
Fetches job listings from a company's Greenhouse-hosted career page and
filters for titles matching our target roles.

Greenhouse exposes a free, public, no-auth-needed JSON API for any company
that uses it to host their careers page:

    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

Passing content=true means the FULL job description comes back in the same
response - no need to separately follow the link and scrape a second page
for Greenhouse-hosted companies. (Custom-built career sites won't have this
shortcut - those need a second fetch, which we'll build separately.)
"""

import requests

TARGET_TITLE_KEYWORDS = [
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "llm engineer",
    "applied ai",
    "applied ml",
]


def fetch_greenhouse_jobs(board_token: str) -> list[dict]:
    """Fetch every published job for one Greenhouse-hosted company."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    response = requests.get(url, params={"content": "true"}, timeout=15)
    response.raise_for_status()
    return response.json()["jobs"]


def title_matches(title: str) -> bool:
    """Cheap first-pass filter - just checks the title, no AI call needed."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in TARGET_TITLE_KEYWORDS)


def find_candidate_jobs(board_token: str) -> list[dict]:
    """
    Returns only the jobs whose TITLE looks relevant.
    This is step 1 of 2 - these candidates still need to go through the
    AI experience/location check (step 2) before we decide to email.
    """
    all_jobs = fetch_greenhouse_jobs(board_token)
    return [job for job in all_jobs if title_matches(job["title"])]


if __name__ == "__main__":
    import sys
    token = sys.argv[1] if len(sys.argv) > 1 else "greenhouse"
    candidates = find_candidate_jobs(token)
    print(f"Found {len(candidates)} title-matching job(s) for '{token}':\n")
    for job in candidates:
        print(f"- {job['title']}  |  {job['location']['name']}")
        print(f"  {job['absolute_url']}\n")
