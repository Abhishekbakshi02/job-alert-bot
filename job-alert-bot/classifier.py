"""
Sends a company's candidate jobs to the LLM for classification against
the experience/location filters. Large batches are automatically split
into smaller chunks (MAX_JOBS_PER_BATCH each) so no single request gets
too big and slow. Uses llm_client's multi-provider fallback chain, so
one provider's daily quota running out doesn't stall the whole run.

Output here is small (a compact JSON array of matches/reasons), so a
small max_tokens budget is used.
"""

import re
import json

from llm_client import call_llm, CLASSIFY_PROVIDERS
from gemini_errors import GeminiUnavailable

MAX_JOBS_PER_BATCH = 1
CLASSIFY_MAX_TOKENS = 1000

BATCH_PROMPT_TEMPLATE = """You are screening {count} job postings against two STRICT requirements. Respond using ONLY a JSON array, no other text before or after it - one object per job, IN THE SAME ORDER as given below.

Requirement 1 (Experience): the role must be for freshers / entry-level / candidates with 0-1 years of professional experience. Reject roles asking for 2+ years, or titled "Senior", "Staff", "Lead", "Principal", or similar.

Requirement 2 (Location): the role must be EITHER fully remote and open to candidates globally, OR based in India. Trust each job's "Official Listed Location" as the source of truth - use its description only to add detail, not to override it. Reject roles restricted to a specific country other than India, and reject on-site/hybrid roles located outside India.

A job only matches if BOTH requirements are satisfied.

{jobs_text}

Respond with ONLY a JSON array of exactly {count} objects, in the same order as above, each shaped like:
{{"matches": true or false, "reason": "one short sentence explaining why"}}
"""


def _classify_chunk(jobs: list[dict], max_retries: int = 3) -> list[dict]:
    jobs_text = "\n\n".join(
        f"--- Job {i + 1} ---\n"
        f"Title: {job['title']}\n"
        f"Official Listed Location: {job['location']}\n"
        f"Description: {job['content'][:4000]}"
        for i, job in enumerate(jobs)
    )
    prompt = BATCH_PROMPT_TEMPLATE.format(count=len(jobs), jobs_text=jobs_text)

    raw_text = call_llm(prompt, providers=CLASSIFY_PROVIDERS, max_retries=max_retries, max_tokens=CLASSIFY_MAX_TOKENS)
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    results = json.loads(cleaned)

    if len(results) != len(jobs):
        raise ValueError(f"Expected {len(jobs)} results back, got {len(results)}")

    return results


def check_jobs_batch(jobs: list[dict], max_retries: int = 3) -> list[dict]:
    """
    jobs: list of {"title": str, "location": str, "content": str}
    Returns a list of {"matches": bool, "reason": str} - IN THE SAME
    ORDER as the input, but may be SHORTER than `jobs` if a later chunk
    failed to classify. Whatever was already successfully classified is
    still returned (never discarded) - main.py's zip() naturally only
    processes that many, leaving the rest to retry next run instead of
    losing an entire company's progress over one bad job.

    A GeminiUnavailable (both providers completely down) still
    propagates, since that should stop AI calls for the whole rest of
    the run (the circuit breaker in main.py), not just this company.
    """
    if not jobs:
        return []

    all_results = []
    for start in range(0, len(jobs), MAX_JOBS_PER_BATCH):
        chunk = jobs[start:start + MAX_JOBS_PER_BATCH]
        try:
            all_results.extend(_classify_chunk(chunk, max_retries))
        except GeminiUnavailable:
            raise
        except Exception as e:
            print(f"[WARN] Classification failed at job {start + 1} of {len(jobs)}: {e} - "
                  f"keeping the {len(all_results)} result(s) already classified for this "
                  f"company, remaining job(s) will be retried next run")
            break

    return all_results
