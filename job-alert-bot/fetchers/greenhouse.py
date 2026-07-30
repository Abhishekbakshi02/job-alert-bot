"""
Fetches job listings from a company's Greenhouse-hosted career page.
"""

import requests
from title_filter import title_matches


def fetch_greenhouse_jobs(board_token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    response = requests.get(url, params={"content": "true"}, timeout=15)
    response.raise_for_status()
    return response.json()["jobs"]


def find_candidate_jobs(board_token: str) -> list[dict]:
    all_jobs = fetch_greenhouse_jobs(board_token)
    return [job for job in all_jobs if title_matches(job["title"])]
