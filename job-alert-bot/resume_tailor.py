"""
Given a confirmed job match, asks the LLM to reorder/reword/trim the
resume content (never invent) to align with that job's description, and
computes a transparent keyword-coverage percentage against the JD's own
key requirements. Uses llm_client's multi-provider fallback chain.
"""

import re
import json

from llm_client import call_llm

TAILOR_PROMPT_TEMPLATE = """You are tailoring a resume for ONE specific job posting, and identifying that job's key requirements.

STRICT RULES - NON-NEGOTIABLE:
1. NEVER invent a skill, tool, project, achievement, employer, or metric that is not already present in the original resume JSON below.
2. You MAY reorder bullets within an experience/project entry to put the most relevant ones first.
3. You MAY reorder the "skills" list entries.
4. You MAY reword a bullet's phrasing to use terminology closer to the job description - but the underlying fact/claim must stay exactly true to the original.
5. You MAY rewrite the "summary" field freely, as long as every claim in it is still fully supported by the rest of the resume content.
6. You MAY OMIT bullets, entire skill categories, or entire projects that are not relevant to this job, to keep the final resume concise (target: fits on 1 page). Omitting is fine; inventing is never fine.
7. Do NOT omit either of the two "experience" entries - both real jobs must always remain. Aim for 4-5 of the most relevant bullets per job (never fewer than 3) - enough to fill the page well, not just the bare minimum.
8. Do NOT change: name, email, linkedin, phone, location, company names, job titles, dates, education, or any techStack string for entries you keep.

Candidate's real resume (JSON):
{resume_json}

Job Title: {job_title}
Job Description:
{job_description}

Return ONLY this JSON structure, no other text, no markdown fences:
{{
  "tailored_resume": <the tailored resume, same structure as the input resume JSON>,
  "jd_key_requirements": [<8-15 short strings - the specific skills/tools/requirements this job description asks for, e.g. "RAG", "Python", "3+ years experience">]
}}
"""


def _compute_keyword_coverage(tailored_resume: dict, jd_key_requirements: list) -> tuple:
    if not jd_key_requirements:
        return 0, []
    full_text = json.dumps(tailored_resume).lower()
    matched = [kw for kw in jd_key_requirements if kw.lower() in full_text]
    coverage = round(100 * len(matched) / len(jd_key_requirements))
    return coverage, matched


def tailor_resume(resume_data: dict, job_title: str, job_description: str, max_retries: int = 2) -> dict:
    prompt = TAILOR_PROMPT_TEMPLATE.format(
        resume_json=json.dumps(resume_data, indent=2),
        job_title=job_title,
        job_description=job_description[:6000],
    )

    raw_text = call_llm(prompt, max_retries=max_retries)
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(cleaned)

    tailored = parsed["tailored_resume"]
    jd_requirements = parsed.get("jd_key_requirements", [])

    for locked_field in ("name", "email", "linkedin", "phone", "location", "education"):
        tailored[locked_field] = resume_data[locked_field]

    coverage, matched = _compute_keyword_coverage(tailored, jd_requirements)
    return {"resume": tailored, "coverage_percent": coverage, "matched_keywords": matched}
