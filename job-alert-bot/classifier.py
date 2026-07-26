"""
Sends a job's title + description to Gemini and asks it to judge the two
hard filters: experience level and location. Returns a match/no-match
decision plus a short reason.
"""

import os
import re
import json
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# If this model name ever starts returning 404 errors, Google has retired
# it - check https://ai.google.dev/gemini-api/docs/models for the current
# name and swap it in here. This happens occasionally (roughly once or
# twice a year) with advance notice from Google.
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

PROMPT_TEMPLATE = """You are screening ONE job posting against two STRICT requirements. Read the job description and respond using ONLY the JSON format specified below - no other text before or after it.

Requirement 1 (Experience): the role must be for freshers / entry-level / candidates with 0-1 years of professional experience. Reject roles asking for 2+ years, or titled "Senior", "Staff", "Lead", "Principal", or similar.

Requirement 2 (Location): the role must be EITHER fully remote and open to candidates globally, OR based in India. Reject roles restricted to a specific country other than India (e.g. "must be based in the US"), and reject on-site/hybrid roles located outside India.

A job only matches if BOTH requirements are satisfied.

Job Title: {title}
Job Description:
{content}

Respond with ONLY this JSON, nothing else:
{{"matches": true or false, "reason": "one short sentence explaining why"}}
"""


def check_job(title: str, content: str) -> dict:
    """Returns {'matches': bool, 'reason': str}"""
    prompt = PROMPT_TEMPLATE.format(title=title, content=content[:6000])

    response = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    response.raise_for_status()

    raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)
