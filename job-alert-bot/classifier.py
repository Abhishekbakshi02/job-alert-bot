"""
Sends a company's candidate jobs to the LLM for classification against
the experience/location filters. Large batches are automatically split
into smaller chunks (MAX_JOBS_PER_BATCH each) so no single request gets
too big and slow. Uses llm_client's multi-provider fallback chain, so
one provider's daily quota running out doesn't stall the whole run.
"""

import re
import json
CLASSIFY_MAX_TOKENS = 15000

from llm_client import call_llm, CLASSIFY_PROVIDERS

MAX_JOBS_PER_BATCH = 3

BATCH_PROMPT_TEMPLATE = """You are screening {count} job postings against two STRICT requirements. Respond using ONLY a JSON array, no other text before or after it - one object per job, IN THE SAME ORDER as given below.

Requirement 1 (Experience): the role must be for freshers / entry-level / candidates with 0-1 years of professional experience. Reject roles asking for 2+ years, or titled "Senior", "Staff", "Lead", "Principal", or similar.

Requirement 2 (Location): the role must be EITHER fully remote and open to candidates globally, OR based in India. Trust each job's "Official Listed Location" as the source of truth - use its description only to add detail, not to override it. Reject roles restricted to a specific country other than India, and reject on-site/hybrid roles located outside India.

A job only matches if BOTH requirements are satisfied.

{jobs_text}

Respond with ONLY a JSON array of exactly {count} objects, in the same order as above, each shaped like:
{{"matches": true or false, "reason": "one short sentence explaining why"}}
"""


def _classify_chunk(jobs: list[dict], max_retries: int = 5) -> list[dict]:
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


def check_jobs_batch(jobs: list[dict], max_retries: int = 5) -> list[dict]:
    if not jobs:
        return []

    all_results = []
    for start in range(0, len(jobs), MAX_JOBS_PER_BATCH):
        chunk = jobs[start:start + MAX_JOBS_PER_BATCH]
        all_results.extend(_classify_chunk(chunk, max_retries))
    return all_results
