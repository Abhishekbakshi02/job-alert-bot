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


TAILOR_PROMPT_TEMPLATE = """ You are tailoring a resume for **ONE specific job posting**. Your task is to identify the most relevant requirements in the job description, tailor the resume to those requirements, and answer any application questions included in the posting.

The final resume content must sound like it was written by a real person who understands the work they have done. It should not sound AI-generated, overly polished, or copied directly from the job description.

## WHAT YOU NEED TO GENERATE

Only generate the sections listed below. Do NOT generate the candidate's name, email, phone number, education, job titles, company names, employment dates, or a separate skills/tech stack section. These details are already fixed and will be merged separately.

The following three sections must be adapted to the specific job:

### 1. SUMMARY

Rewrite the summary to highlight the candidate's most relevant experience, skills, and knowledge for this particular role.

- Start with the experience or technical knowledge that is most relevant to the job.
- Use simple, natural English that clearly communicates what the candidate knows and has worked on.
- Keep it professional but conversational in tone.
- Avoid generic statements that could appear on anyone's resume.
- Do not exaggerate experience or describe the candidate as an expert unless the source material supports it.
- Make every sentence meaningful. Do not add words just to make the summary longer.

### 2. EXPERIENCE_BULLETS

For every job listed in the candidate's experience, select and reorder the **3–5 most relevant bullets** based on the job description.

- Keep the jobs in the same order as provided.
- Select bullets that demonstrate experience or skills related to the target role.
- Reword existing bullets only when necessary to make them clearer or more relevant.
- Use terminology from the job description naturally, but never copy entire sentences just to match keywords.
- Explain what the candidate actually worked on, how they used a tool or technology, and what the work involved.
- Keep the original meaning and facts unchanged.
- Do not turn ordinary responsibilities into impressive-sounding achievements.
- Every bullet should communicate a clear piece of work or practical knowledge.

### 3. PROJECTS

Read the PROJECT KNOWLEDGE BASE carefully and select the **1–2 projects** that best match the job requirements.

For each selected project:

- Include its original title and dates from the knowledge base.
- Write **5–6 resume-style bullet points**.
- Focus on the technical work, implementation details, tools used, and problems addressed.
- Explain the work in a way that shows the candidate understands how the project works.
- Prefer practical explanations over complicated technical language.
- Reorder the bullets so the most relevant technical work appears first.
- Use only information explicitly available in the project knowledge base.
- Do not add features, responsibilities, technologies, results, or metrics that are not documented.

Include a project-specific `techStack` field containing a comma-separated list of only the tools and technologies mentioned in the knowledge base for that project. Do not create a separate tech stack section.

## WRITING STYLE — VERY IMPORTANT

The resume must use **simple, clear, natural English**. It should sound like a technically capable person explaining their own work, not an AI generating professional-sounding sentences.

Follow these guidelines throughout the summary, experience bullets, projects, and application answers:

1. **Use everyday English.** Prefer simple and commonly used words over fancy vocabulary. The goal is clarity, not impressive-sounding language.

2. **Show actual understanding.** Describe what the candidate did and how they worked with a technology. A recruiter should be able to understand the candidate's practical knowledge from reading the bullet.

3. **Avoid AI-sounding language.** Do not use unnecessarily polished, corporate, or exaggerated phrases such as:
   - "Spearheaded the development of..."
   - "Leveraged cutting-edge technologies..."
   - "Demonstrated a strong ability to..."
   - "Played a pivotal role in..."
   - "Engineered robust and scalable solutions..."
   - "Orchestrated end-to-end implementation..."
   
   Use straightforward alternatives such as "Built", "Developed", "Used", "Worked on", "Implemented", "Created", "Analysed", and "Improved", wherever accurate.

4. **Avoid unnecessary technical jargon.** Use technical terms when they are relevant to the job, but do not make simple work sound complicated.

5. **Do not stuff keywords.** Include relevant job-description keywords naturally within sentences. Never insert technologies or terms simply to improve ATS matching.

6. **Keep sentences direct.** Each bullet should communicate one clear idea. Avoid long sentences containing multiple clauses and unnecessary explanations.

7. **Do not exaggerate.** The candidate should sound knowledgeable and confident, but never like someone claiming to have more experience than they actually do.

8. **Maintain consistency.** Use the same natural writing style across all sections. Do not make the summary sound human while making the experience bullets sound like AI-generated corporate content.

### Example of the expected writing style

Avoid:

"Leveraged Python and advanced machine learning methodologies to develop a sophisticated predictive analytics solution, enabling data-driven business decisions."

Prefer:

"Used Python and machine learning to analyse data, identify patterns, and build models that helped with business forecasting."

The second version is more direct and makes the actual work easier to understand. Follow this style throughout the resume.

## ONE-PAGE RESUME REQUIREMENT — CRITICAL

The final resume must fit on **one complete page**, and the page should look properly filled rather than having large empty spaces at the bottom.

This is a very important requirement.

- Generate enough relevant content to support a full one-page resume.
- Use the available summary, experience, and project sections effectively.
- Give sufficient detail to technical experience and projects instead of making every bullet unnecessarily short.
- Select the strongest relevant bullets and projects to make the best use of the available space.
- Avoid repeating the same information across the summary, experience, and projects.
- Do not add irrelevant content, generic statements, or filler sentences just to occupy space.
- Do not invent experience, achievements, tools, or metrics to fill the page.
- Maintain readability. A full page should not mean excessively long sentences or overly dense paragraphs.

**Priority:** Aim for a well-filled, balanced, one-page resume while preserving accuracy, relevance, and readability. Never sacrifice factual accuracy just to fill space.

## APPLICATION QUESTIONS

Read the complete job description and identify any explicit questions or instructions directed at applicants.

Examples include:
- Why do you want to work with us?
- Why are you interested in this role?
- Describe your relevant experience.
- What makes you a good fit for this position?
- Tell us about a project you have worked on.

Answer every such question using only the information available in the candidate's resume and project knowledge base.

For these answers:

- Use simple, natural English, as if the candidate were answering during a real conversation.
- Keep the answers direct and relevant to the question.
- Show genuine understanding of the candidate's work and experience.
- Avoid formal introductions, generic enthusiasm, corporate phrases, and textbook-style answers.
- Do not begin by repeating the question.
- Do not claim experience, interests, or achievements that are not supported by the provided information.

Return an empty array if the job description contains no application questions.

## STRICT FACTUAL RULES — NON-NEGOTIABLE

1. NEVER invent a skill, technology, tool, achievement, employer, responsibility, or metric that is not already present in the candidate's resume or project knowledge base.
2. `experience_bullets` MUST contain exactly `{experience_count}` arrays, one for each job in the same order as provided. Each array MUST contain 3–5 bullet strings.
3. `projects` MUST contain 1–2 entries. Each entry MUST have:
   - `title`: Original project title from the knowledge base.
   - `dates`: Dates from the knowledge base.
   - `bullets`: 5–6 relevant bullet strings.
   - `techStack`: Comma-separated string of tools and technologies explicitly mentioned for that project.
4. `application_questions` MUST contain every relevant question found in the job description, along with its answer. Return an empty list if none are found.
5. Do not include any fixed personal, education, employment-identification, or general skills-section information in the generated content.
6. Preserve the actual meaning of all experience and project details. Rewording is allowed; changing facts is not.
7. Do not add a section or field that is not part of the required output structure.

## INPUT

**JOB DESCRIPTION:**
{job_description}

**CANDIDATE'S RESUME CONTEXT:**
{resume_context}

**PROJECT KNOWLEDGE BASE:**
{knowledge_base}

**NUMBER OF JOBS:**
{experience_count}

## OUTPUT FORMAT

Return ONLY valid JSON. Do not include Markdown code fences, explanations, notes, or commentary.

Use exactly this structure:

{
  "summary": "Tailored professional summary",
  "experience_bullets": [
    ["Bullet 1", "Bullet 2", "Bullet 3"],
    ["Bullet 1", "Bullet 2", "Bullet 3"]
  ],
  "projects": [
    {
      "title": "Project title",
      "dates": "Project dates",
      "bullets": [
        "Bullet 1",
        "Bullet 2",
        "Bullet 3",
        "Bullet 4",
        "Bullet 5"
      ],
      "techStack": "Tool 1, Tool 2, Tool 3"
    }
  ],
  "application_questions": [
    {
      "question": "Question from the job description",
      "answer": "Natural, truthful answer"
    }
  ]
} """


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
