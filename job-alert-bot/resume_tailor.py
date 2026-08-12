"""
Given a confirmed job match, asks the LLM to:
1. Tailor the resume (summary, experience bullet selection, and
   projects chosen fresh from the knowledge base) to the job.
2. Answer any explicit application questions found in the job
   description text itself.
3. Compute a transparent keyword-coverage percentage.

Everything in tailor_resume() - including building the prompt itself -
runs inside the retry loop's try/except, so ANY failure at ANY point
(malformed resume_data.json, a bad LLM response, a network error, all
providers down) lands on the guaranteed fallback path below, never an
uncaught exception. The fallback itself is also defensive (uses .get()
everywhere, has its own inner try/except), so it can't fail either.
"""

import os
import re
import json

from llm_client import call_llm, TAILOR_PROVIDERS

KNOWLEDGE_BASE_FILE = "knowledge_base.md"
TAILOR_MAX_TOKENS = 4000


def _load_knowledge_base() -> str:
    if not os.path.exists(KNOWLEDGE_BASE_FILE):
        return "(no knowledge base file found)"
    with open(KNOWLEDGE_BASE_FILE) as f:
        return f.read()


TAILOR_PROMPT_TEMPLATE = """You are tailoring a resume for ONE specific job posting, identifying its key requirements, and answering any application questions in the posting text.

Only generate what's below - do NOT include name, email, phone, education, job titles, company names, dates, or techStack anywhere in your response. Those are fixed and get merged in separately - regenerating them would only waste your output space.

THREE things must actively adapt to THIS job:
- SUMMARY: rewrite it to lead with what's most relevant to this role (still fully truthful, grounded in the resume/knowledge base below).
- EXPERIENCE_BULLETS: for each job listed below (in the same order), select and reorder 3-5 of its most relevant bullets - reword lightly if it helps match the job's terminology, but keep every claim exactly true.
- PROJECTS: read the PROJECT KNOWLEDGE BASE below and select whichever 1-2 projects fit this job best. Write 5-6 resume-style bullets for each, using ONLY facts stated in the knowledge base - never invent beyond what's written.

Candidate's summary, skills, and experience (title/company for context only - do not repeat them in your output):
{resume_context}

PROJECT KNOWLEDGE BASE:
{knowledge_base}

STRICT RULES - NON-NEGOTIABLE:
1. NEVER invent a skill, tool, achievement, employer, or metric not already present in the context or knowledge base above.
2. "experience_bullets" MUST be an array of exactly {experience_count} arrays (one per job, same order as listed), each with 3-5 bullet strings pulled/reworded from that job's real bullets - never fewer than 3.
3. "projects" MUST have 1-2 entries, each with "title", "dates" (from the knowledge base), "bullets" (5-6 strings), and "techStack" (comma-separated string of tools mentioned in the knowledge base for it).
4. APPLICATION QUESTIONS: scan the job description for explicit questions/instructions directed at applicants (e.g. "tell us why you want this role"). Answer each truthfully in simple, human-sounding English, grounded only in the context/knowledge base above. Empty list if none found.

Job Title: {job_title}
Job Description:
{job_description}

Return ONLY this JSON, no other text, no markdown fences:
{{
  "summary": "...",
  "experience_bullets": [["bullet", "bullet", "bullet"], ["bullet", "bullet", "bullet"]],
  "projects": [{{"title": "...", "dates": "...", "bullets": ["...", "..."], "techStack": "..."}}],
  "jd_key_requirements": ["...", "..."],
  "application_answers": [{{"question": "...", "answer": "..."}}]
}}
"""


def _build_resume_context(resume_data: dict) -> dict:
    return {
        "summary": resume_data.get("summary", ""),
        "skills": resume_data.get("skills", []),
        "experience": [
            {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "bullets": job.get("bullets", []),
            }
            for job in resume_data.get("experience", [])
        ],
    }


def _merge_tailored_output(resume_data: dict, model_output: dict) -> dict:
    experience_list = resume_data.get("experience", [])
    experience_bullets = model_output.get("experience_bullets", [])
    if len(experience_bullets) != len(experience_list):
        raise ValueError(
            f"Expected {len(experience_list)} experience bullet-lists, got {len(experience_bullets)}"
        )

    merged_experience = [
        {**job, "bullets": bullets}
        for job, bullets in zip(experience_list, experience_bullets)
    ]

    projects = model_output.get("projects", [])
    if not projects:
        raise ValueError("Model returned zero projects")

    return {
        "name": resume_data.get("name", ""),
        "email": resume_data.get("email", ""),
        "linkedin": resume_data.get("linkedin", ""),
        "phone": resume_data.get("phone", ""),
        "location": resume_data.get("location", ""),
        "education": resume_data.get("education", {}),
        "summary": model_output.get("summary", resume_data.get("summary", "")),
        "skills": resume_data.get("skills", []),
        "experience": merged_experience,
        "projects": projects,
    }


def _compute_keyword_coverage(tailored_resume: dict, jd_key_requirements: list) -> tuple:
    if not jd_key_requirements:
        return 0, []
    full_text = json.dumps(tailored_resume).lower()
    matched = [kw for kw in jd_key_requirements if kw.lower() in full_text]
    coverage = round(100 * len(matched) / len(jd_key_requirements))
    return coverage, matched


def build_fallback_resume(resume_data: dict) -> dict:
    fallback_project = {
        "title": "AI-Powered Job Discovery & Resume Automation",
        "dates": "July 2026",
        "bullets": ["Built a fully automated job-discovery and resume-tailoring system."],
        "techStack": "Python, GitHub Actions, LLM APIs",
    }
    try:
        kb_text = _load_knowledge_base()
        match = re.search(r"^##\s+(.+?)\n\*\*Timeframe:\*\*\s*(.+?)\n\n(.+?)(?=\n---|\Z)", kb_text, re.DOTALL | re.MULTILINE)
        if match:
            title, dates, body = match.groups()
            bullets = [s.strip() for s in re.split(r"(?<=[.])\s+", body.strip()) if s.strip()][:6]
            if bullets:
                fallback_project = {"title": title.strip(), "dates": dates.strip(), "bullets": bullets, "techStack": "See project description"}
    except Exception:
        pass

    return {
        "name": resume_data.get("name", ""),
        "email": resume_data.get("email", ""),
        "linkedin": resume_data.get("linkedin", ""),
        "phone": resume_data.get("phone", ""),
        "location": resume_data.get("location", ""),
        "education": resume_data.get("education", {}),
        "summary": resume_data.get("summary", ""),
        "skills": resume_data.get("skills", []),
        "experience": resume_data.get("experience", []),
        "projects": [fallback_project],
    }


def tailor_resume(resume_data: dict, job_title: str, job_description: str, max_retries: int = 5, max_parse_attempts: int = 2) -> dict:
    last_error = None
    for parse_attempt in range(max_parse_attempts):
        try:
            resume_context = _build_resume_context(resume_data)
            prompt = TAILOR_PROMPT_TEMPLATE.format(
                resume_context=json.dumps(resume_context, indent=2),
                knowledge_base=_load_knowledge_base(),
                experience_count=len(resume_data.get("experience", [])),
                job_title=job_title,
                job_description=job_description[:6000],
            )

            raw_text = call_llm(prompt, providers=TAILOR_PROVIDERS, max_retries=max_retries, max_tokens=TAILOR_MAX_TOKENS)
            cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(cleaned)
            tailored = _merge_tailored_output(resume_data, parsed)

            jd_requirements = parsed.get("jd_key_requirements", [])
            application_answers = parsed.get("application_answers", [])
            coverage, matched = _compute_keyword_coverage(tailored, jd_requirements)

            return {
                "resume": tailored, "coverage_percent": coverage, "matched_keywords": matched,
                "application_answers": application_answers, "used_fallback": False,
            }
        except Exception as e:
            last_error = e
            print(f"[WARN] Tailoring attempt {parse_attempt + 1}/{max_parse_attempts} failed: {e}")
            continue

    print(f"[WARN] All tailoring attempts failed ({last_error}) - using untailored fallback resume so an attachment still goes out")
    try:
        fallback = build_fallback_resume(resume_data)
    except Exception as e:
        print(f"[WARN] Fallback resume construction hit an unexpected issue ({e}) - using bare minimal defaults")
        fallback = {
            "name": resume_data.get("name", ""), "email": resume_data.get("email", ""),
            "linkedin": resume_data.get("linkedin", ""), "phone": resume_data.get("phone", ""),
            "location": resume_data.get("location", ""), "education": resume_data.get("education", {}),
            "summary": resume_data.get("summary", ""), "skills": resume_data.get("skills", []),
            "experience": resume_data.get("experience", []),
            "projects": [{"title": "Software Engineering Projects", "dates": "2026",
                          "bullets": ["Details available on request."], "techStack": "Python"}],
        }

    return {
        "resume": fallback, "coverage_percent": 0, "matched_keywords": [],
        "application_answers": [], "used_fallback": True,
    }
