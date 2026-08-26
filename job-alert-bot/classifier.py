"""
Sends a company's candidate jobs to the LLM for classification against
the experience/location filters. Batch size is 1 (one job per call) -
this also means the whole content-length budget per call is available
for a single job, so truncation can be much more generous than when
multiple jobs shared one request.
"""

import re
import json

from llm_client import call_llm, CLASSIFY_PROVIDERS
from gemini_errors import GeminiUnavailable

MAX_JOBS_PER_BATCH = 1
CLASSIFY_MAX_TOKENS = 1000
CONTENT_TRUNCATE_CHARS = 12000  # generous now that each call only holds 1 job

BATCH_PROMPT_TEMPLATE = """You are screening {count} job posting(s) against STRICT requirements. Read the ENTIRE job description below carefully before deciding - requirements are often stated later in the posting (e.g. in a "Qualifications" section), not just in the title or opening paragraph. Respond using ONLY a JSON array, no other text before or after it - one object per job, IN THE SAME ORDER as given below.

Requirement 1 (Experience): the role must be for freshers / entry-level / early-career candidates with 0-2 years of professional experience (0 or 1 years are acceptable). Scan the WHOLE description for ANY stated years-of-experience requirement, wherever it appears. Reject the role if:
  - it asks for MORE than 2 years of experience, stated ANYWHERE in the posting (e.g. "3+ years", "5+ years", "minimum 4 years") - even if the title itself doesn't say "Senior"
  - the title contains "Senior", "Staff", "Lead", "Principal", "Manager", "Director", or similar seniority indicators
  - it is an internship / intern position
  - it is an "AI Trainer" / "Voice Trainer" / "AI Voice Trainer" / data-labeling/annotation role (these are not software engineering roles, even if "AI" appears in the title)

Requirement 2 (Location): the role must be EITHER fully remote and open to candidates globally, OR based in India. Trust each job's "Official Listed Location" as the source of truth - use its description only to add detail, not to override it. Reject roles restricted to a specific country other than India, and reject on-site/hybrid roles located outside India.

A job only matches if BOTH requirements are satisfied. If genuinely uncertain after reading carefully, prefer REJECTING over accepting - a missed relevant job is bad, but a false match wastes the candidate's attention on something they don't qualify for.

Your "reason" must cite the SPECIFIC evidence from the text that drove your decision (e.g. quote or closely paraphrase the actual experience/location line you found) - not a generic restatement of the rule.

{jobs_text}

Respond with ONLY a JSON array of exactly {count} objects, in the same order as above, each shaped like:
{{"matches": true or false, "reason": "one short sentence citing the specific evidence"}}
"""


def _classify_chunk(jobs: list[dict], max_retries: int = 3) -> list[dict]:
    jobs_text = "\n\n".join(
        f"--- Job {i + 1} ---\n"
        f"Title: {job['title']}\n"
        f"Official Listed Location: {job['location']}\n"
        f"Description: {job['content'][:CONTENT_TRUNCATE_CHARS]}"
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
    Returns a list of {"matches": bool, "reason": str} - may be SHORTER
    than `jobs` if a later job failed to classify; whatever succeeded is
    kept, never discarded wholesale. A total-outage (GeminiUnavailable)
    still propagates to trigger the circuit breaker in main.py.
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
