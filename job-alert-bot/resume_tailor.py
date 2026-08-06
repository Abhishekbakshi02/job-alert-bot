"""
Given a confirmed job match, asks Gemini to reorder/reword/trim the
resume content (never invent) to align with that job's description, and
computes a transparent keyword-coverage percentage against the JD's own
key requirements.
"""

import os
import re
import json
import time
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

TAILOR_PROMPT_TEMPLATE = """You are tailoring a resume for ONE specific job posting, and identifying that job's key requirements.

STRICT RULES - NON-NEGOTIABLE:
1. NEVER invent a skill, tool, project, achievement, employer, or metric that is not already present in the original resume JSON below.
2. You MAY reorder bullets within an experience/project entry to put the most relevant ones first.
3. You MAY reorder the "skills" list entries.
4. You MAY reword a bullet's phrasing to use terminology closer to the job description - but the underlying fact/claim must stay exactly true to the original.
5. You MAY rewrite the "summary" field freely, as long as every claim in it is still fully supported by the rest of the resume content.
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


def tailor_resume(resume_data: dict, job_title: str, job_description: str, max_retries: int = 5) -> dict:
    """Returns {'resume': dict, 'coverage_percent': int, 'matched_keywords': list}"""
    prompt = TAILOR_PROMPT_TEMPLATE.format(
        resume_json=json.dumps(resume_data, indent=2),
        job_title=job_title,
        job_description=job_description[:6000],
    )

    for attempt in range(max_retries):
        response = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )

        if response.status_code == 429:
            wait_seconds = 15 * (attempt + 1)
            print(f"[INFO] Gemini rate limit hit while tailoring resume, waiting {wait_seconds}s")
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)

        tailored = parsed["tailored_resume"]
        jd_requirements = parsed.get("jd_key_requirements", [])

        for locked_field in ("name", "email", "linkedin", "phone", "location", "education"):
            tailored[locked_field] = resume_data[locked_field]

        coverage, matched = _compute_keyword_coverage(tailored, jd_requirements)

        time.sleep(2)
        return {"resume": tailored, "coverage_percent": coverage, "matched_keywords": matched}

    raise RuntimeError("Gemini rate limit persisted while tailoring resume")
