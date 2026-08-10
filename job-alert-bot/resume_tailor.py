"""
Given a confirmed job match, asks the LLM to:
1. Tailor the resume (summary, experience selection, and projects chosen
   fresh from the knowledge base) to the job description.
2. Answer any explicit application questions found IN the job
   description text itself (not a separate application form - see the
   module docstring note below on that distinction).
3. Compute a transparent keyword-coverage percentage against the JD's
   own key requirements.

Uses llm_client's multi-provider fallback chain.

NOTE on application questions: this only catches questions written
directly into the job posting's own description text (which some
companies do include, e.g. "In your application, please address: ...").
It does NOT scrape a separate application FORM's custom questions -
those live on a different page/endpoint per ATS platform (often
JS-rendered) and would need dedicated per-platform work to extract,
which hasn't been built yet.
"""

import os
import re
import json

from llm_client import call_llm, TAILOR_PROVIDERS

KNOWLEDGE_BASE_FILE = "knowledge_base.md"


def _load_knowledge_base() -> str:
    if not os.path.exists(KNOWLEDGE_BASE_FILE):
        return "(no knowledge base file found - projects section will be empty)"
    with open(KNOWLEDGE_BASE_FILE) as f:
        return f.read()


TAILOR_PROMPT_TEMPLATE = """You are tailoring a resume for ONE specific job posting, identifying that job's key requirements, and answering any application questions found in the posting text itself.

THREE resume sections must actively adapt to THIS job:
- SUMMARY: rewrite it to lead with what's most relevant to this specific role (still fully truthful).
- PROJECTS: read the PROJECT KNOWLEDGE BASE below (free-form notes on the candidate's various projects) and select whichever 1-2 projects are most relevant to this job. Write 5-6 resume-style bullet points for each selected project, in the same concise, action-verb-led style as the resume's EXPERIENCE bullets. Use ONLY facts, tools, and outcomes actually stated in the knowledge base - never invent anything beyond what's written there, even if it would sound more impressive.
- EXPERIENCE: reorder and reword bullets within each job so the most relevant ones lead.

PROJECT KNOWLEDGE BASE (free-form notes - select and write up 1-2 of these as resume projects):
{knowledge_base}

STRICT RULES - NON-NEGOTIABLE:
1. NEVER invent a skill, tool, achievement, employer, or metric that is not already present in the resume JSON OR the knowledge base above.
2. You MAY reorder bullets within an experience entry to put the most relevant ones first.
3. You MAY reorder the "skills" list entries.
4. You MAY reword a bullet's phrasing to use terminology closer to the job description - but the underlying fact/claim must stay exactly true to the original.
5. You MAY rewrite the "summary" field freely, as long as every claim in it is still fully supported by the resume content and knowledge base.
6. You MAY omit bullets or entire skill categories from EXPERIENCE that are not relevant to this job (target: fills the page well, close to 1 full page). Omitting is fine; inventing is never fine.
7. Do NOT omit either of the two "experience" entries - both real jobs must always remain. Aim for 4-5 of the most relevant bullets per job (never fewer than 3).
8. Write "projects" as a NEW array (1-2 entries) built entirely from your selection out of the knowledge base above. Give each project a "title", "dates" (from the knowledge base), "bullets" (5-6), and "techStack" (comma-separated string of tools actually mentioned in the knowledge base for that project).
9. Do NOT change: name, email, linkedin, phone, location, company names, job titles, dates, education, or any techStack string in EXPERIENCE.
10. APPLICATION QUESTIONS: scan the job description text below for any explicit questions or instructions directed at applicants (e.g. "In your cover letter, tell us...", "Please answer: why this role?"). If you find any, answer each one truthfully in simple, natural, human-sounding English (not corporate-sounding), based ONLY on the resume JSON and knowledge base content - never invent an answer that isn't grounded in real facts about the candidate. If the job description contains no explicit questions, return an empty list for this.

Candidate's real resume (JSON, excluding projects - those come from the knowledge base):
{resume_json}

Job Title: {job_title}
Job Description:
{job_description}

Return ONLY this JSON structure, no other text, no markdown fences:
{{
  "tailored_resume": <the tailored resume with "projects" freshly written from the knowledge base>,
  "jd_key_requirements": [<8-15 short strings - the specific skills/tools/requirements this job description asks for>],
  "application_answers": [{{"question": "...", "answer": "..."}}]
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
    """Returns {'resume': dict, 'coverage_percent': int, 'matched_keywords': list, 'application_answers': list}"""
    resume_without_projects = {k: v for k, v in resume_data.items() if k != "projects"}

    prompt = TAILOR_PROMPT_TEMPLATE.format(
        knowledge_base=_load_knowledge_base(),
        resume_json=json.dumps(resume_without_projects, indent=2),
        job_title=job_title,
        job_description=job_description[:6000],
    )

    raw_text = call_llm(prompt, providers=TAILOR_PROVIDERS, max_retries=max_retries)
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(cleaned)

    tailored = parsed["tailored_resume"]
    jd_requirements = parsed.get("jd_key_requirements", [])
    application_answers = parsed.get("application_answers", [])

    for locked_field in ("name", "email", "linkedin", "phone", "location", "education"):
        tailored[locked_field] = resume_data[locked_field]

    coverage, matched = _compute_keyword_coverage(tailored, jd_requirements)
    return {
        "resume": tailored,
        "coverage_percent": coverage,
        "matched_keywords": matched,
        "application_answers": application_answers,
    }
