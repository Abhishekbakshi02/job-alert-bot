"""
Sends a job's title, location, and description to Gemini and asks it to
judge the two hard filters: experience level and location.
"""

import os
import re
import json
import time
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

PROMPT_TEMPLATE = """You are screening ONE job posting against two STRICT requirements. Respond using ONLY the JSON format specified below - no other text before or after it.

Requirement 1 (Experience): the role must be for freshers / entry-level / candidates with 0-1 years of professional experience. Reject roles asking for 2+ years, or titled "Senior", "Staff", "Lead", "Principal", or similar.

Requirement 2 (Location): the role must be EITHER fully remote and open to candidates globally, OR based in India. Trust the "Official Listed Location" field below as the source of truth - use the description text only to add detail, not to override it. Reject roles restricted to a specific country other than India, and reject on-site/hybrid roles located outside India.

A job only matches if BOTH requirements are satisfied.

Job Title: {title}
Official Listed Location: {location}
Job Description:
{content}

Respond with ONLY this JSON, nothing else:
{{"matches": true or false, "reason": "one short sentence explaining why"}}
"""


def check_job(title: str, location: str, content: str, max_retries: int = 5) -> dict:
    """Returns {'matches': bool, 'reason': str}. Retries with backoff on rate limits."""
    prompt = PROMPT_TEMPLATE.format(title=title, location=location, content=content[:6000])

    for attempt in range(max_retries):
        response = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )

        if response.status_code == 429:
            wait_seconds = 15 * (attempt + 1)
            print(f"[INFO] Gemini rate limit hit, waiting {wait_seconds}s (retry {attempt + 1}/{max_retries})")
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        time.sleep(6)  # small pause so we don't immediately trip the per-minute limit again
        return json.loads(cleaned)

    raise RuntimeError(f"Gemini rate limit persisted after {max_retries} retries")
