"""
Given a confirmed job match, asks Gemini to reorder and reword the
resume content (never invent) to align with that job's description.
"""

import os
import re
import json
import time
import requests

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

TAILOR_PROMPT_TEMPLATE = """You are tailoring a resume for ONE specific job posting.

STRICT RULES - NON-NEGOTIABLE:
1. NEVER invent a skill, tool, project, achievement, employer, or metric that is not already present in the original resume JSON below.
2. You MAY reorder bullets within an experience/project entry to put the most relevant ones first.
3. You MAY reorder the "skills" list entries.
4. You MAY reword a bullet's phrasing to use terminology closer to the job description - but the underlying fact/claim must stay exactly true to the original.
5. You MAY rewrite the "summary" field freely, as long as every claim in it is still fully supported by the rest of the resume content.
6. Do NOT change: name, email, linkedin, phone, location, company names, job titles, dates, education, or any techStack string.
7. Return the COMPLETE resume as JSON in EXACTLY the same structure as given - same keys, same nesting, same number of entries - with only the allowed fields changed.

Candidate's real resume (JSON):
{resume_json}

Job Title: {job_title}
Job Description:
{job_description}

Return ONLY the complete tailored resume as JSON. No other text, no markdown fences.
"""


def tailor_resume(resume_data: dict, job_title: str, job_description: str, max_retries: int = 5) -> dict:
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
        tailored = json.loads(cleaned)

        # Safety net: force these back to the real values regardless of
        # what Gemini returns, so contact info/education can never drift.
        for locked_field in ("name", "email", "linkedin", "phone", "location", "education"):
            tailored[locked_field] = resume_data[locked_field]

        time.sleep(2)
        return tailored

    raise RuntimeError("Gemini rate limit persisted while tailoring resume")
