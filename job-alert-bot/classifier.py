"""
Sends a company's candidate jobs to Gemini for classification against
the experience/location filters. Large batches are automatically split
into smaller chunks (MAX_JOBS_PER_BATCH each) so no single request gets
too big and slow - a company with 19 matches makes 4 fast calls instead
of 1 huge, unpredictably slow one.
"""

import os
import re
import json
import time
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

MAX_JOBS_PER_BATCH = 6

BATCH_PROMPT_TEMPLATE = """You are screening {count} job postings against two STRICT requirements. Respond using ONLY a JSON array, no other text before or after it - one object per job, IN THE SAME ORDER as given below.

Requirement 1 (Experience): the role must be for freshers / entry-level / candidates with 0-1 years of professional experience. Reject roles asking for 2+ years, or titled "Senior", "Staff", "Lead", "Principal", or similar.

Requirement 2 (Location): the role must be EITHER fully remote and open to candidates globally, OR based in India. Trust each job's "Official Listed Location" as the source of truth - use its description only to add detail, not to override it. Reject roles restricted to a specific country other than India, and reject on-site/hybrid roles located outside India.

A job only matches if BOTH requirements are satisfied.

{jobs_text}

Respond with ONLY a JSON array of exactly {count} objects, in the same order as above, each shaped like:
{{"matches": true or false, "reason": "one short sentence explaining why"}}
"""


def _classify_chunk(jobs: list[dict], max_retries: int) -> list[dict]:
    jobs_text = "\n\n".join(
        f"--- Job {i + 1} ---\n"
        f"Title: {job['title']}\n"
        f"Official Listed Location: {job['location']}\n"
        f"Description: {job['content'][:4000]}"
        for i, job in enumerate(jobs)
    )
    prompt = BATCH_PROMPT_TEMPLATE.format(count=len(jobs), jobs_text=jobs_text)

    for attempt in range(max_retries):
        response = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )

        if response.status_code == 429:
            wait_seconds = 15 * (attempt + 1)
            print(f"[INFO] Gemini rate limit hit, waiting {wait_seconds}s (retry {attempt + 1}/{max_retries})")
            time.sleep(wait_seconds)
            continue

        if response.status_code in (500, 502, 503, 504):
            wait_seconds = 10 * (attempt + 1)
            print(f"[INFO] Gemini returned {response.status_code} (temporary issue), "
                  f"waiting {wait_seconds}s (retry {attempt + 1}/{max_retries})")
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        results = json.loads(cleaned)

        if len(results) != len(jobs):
            raise ValueError(f"Expected {len(jobs)} results back, got {len(results)}")

        time.sleep(2)
        return results

    raise RuntimeError(f"Gemini call failed after {max_retries} retries")


def check_jobs_batch(jobs: list[dict], max_retries: int = 5) -> list[dict]:
    """Automatically splits into chunks of at most MAX_JOBS_PER_BATCH."""
    if not jobs:
        return []

    all_results = []
    for start in range(0, len(jobs), MAX_JOBS_PER_BATCH):
        chunk = jobs[start:start + MAX_JOBS_PER_BATCH]
        all_results.extend(_classify_chunk(chunk, max_retries))
    return all_results
