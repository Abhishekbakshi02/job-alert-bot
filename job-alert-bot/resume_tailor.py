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


TAILOR_PROMPT_TEMPLATE = """ You are tailoring a resume for **ONE specific job posting**. Your task is to analyse the job description, identify its most important requirements, and tailor the candidate's existing resume content to match the role as closely as possible without changing or exaggerating any facts.

You must also identify and answer any application questions explicitly included in the job posting.

The final content must sound like it was written by a real person who understands their work and technical skills. It must not sound AI-generated, overly formal, excessively polished, or copied directly from the job description.

# 1. WHAT YOU MUST GENERATE

Generate ONLY these four sections:

1. `summary`
2. `experience_bullets`
3. `projects`
4. `application_questions`

Do NOT generate the candidate's name, email, phone number, education, employment job titles, company names, employment dates, or a separate skills section. These details are already fixed and will be merged separately.

**Important:** Project titles, project dates, and project-specific `techStack` MUST be generated as part of the `projects` section. They are not excluded.

The content of all four sections must be tailored to the target job.

# 2. SUMMARY

Rewrite the candidate's summary to highlight the experience, technical knowledge, and skills most relevant to the target position.

Follow these rules:

- Start with the candidate's most relevant experience or technical knowledge.
- Use simple, natural English that clearly communicates what the candidate knows and has worked on.
- Keep it professional but conversational in tone.
- Focus on practical knowledge rather than making generic claims about being highly skilled or passionate.
- Include relevant technologies and concepts naturally.
- Avoid repeating the job description.
- Do not exaggerate the candidate's experience or describe them as an expert unless the source material supports it.
- Keep the summary concise, meaningful, and specific to the role.

The summary should give recruiters a quick understanding of the candidate's actual technical background.

# 3. EXPERIENCE_BULLETS

For every job listed in the candidate's experience, select and reorder the **3–5 most relevant existing bullets** based on the target job description.

Strict requirements:

- Return exactly `{experience_count}` arrays, one for each job.
- Maintain the original order of the jobs.
- Each array must contain 3–5 bullet strings.
- Select bullets from the actual responsibilities and work described for that particular job.
- Reword existing bullets only when necessary to improve clarity and relevance.
- Keep every original claim factually accurate.
- Do not transfer responsibilities or achievements from one job to another.
- Do not turn ordinary responsibilities into impressive-sounding achievements.
- Do not add tools, technologies, responsibilities, or metrics that are not present in the source material.

**Writing approach:**

Explain what the candidate actually did, how they used a particular technology, and what the work involved.

Prefer practical explanations over generic statements about technical capabilities.

For example:

Avoid:
"Leveraged advanced analytical methodologies to facilitate data-driven business decisions."

Prefer:
"Used Python to analyse business data, identify patterns, and prepare reports that supported business decisions."

The second version communicates the actual work more clearly.

# 4. PROJECTS

Carefully examine the complete PROJECT KNOWLEDGE BASE and select the **1–2 projects** that best match the target job.

Choose projects based on their actual technical relevance, not simply because their titles contain matching keywords.

For every selected project, generate:

- `title`: Original project title from the knowledge base.
- `dates`: Project dates exactly as mentioned in the knowledge base.
- `bullets`: 5–6 relevant resume-style bullet points.
- `techStack`: A comma-separated string containing the identifiable technologies used in that project.

## Project bullet requirements

- Explain the actual technical work performed.
- Highlight implementation details, tools, technologies, and problems addressed.
- Show that the candidate understands how the project works.
- Place the most relevant technical contributions first.
- Use natural, straightforward English.
- Avoid unnecessary technical jargon and complicated sentence structures.
- Do not repeat the same information across multiple bullets.
- Do not invent features, architecture, responsibilities, results, or metrics.
- Use only facts explicitly available in the project knowledge base.

Each bullet should communicate a meaningful piece of technical work rather than simply listing technologies.

## TECH STACK EXTRACTION — MANDATORY

This is an important requirement. Do not leave the `techStack` field empty when technologies are identifiable in the project knowledge base.

**Do not depend exclusively on the dedicated Tech Stack field.**

Extract technologies by examining the ENTIRE project description, including:

- Project title.
- Every project bullet.
- Implementation details.
- Tools and platforms mentioned in the description.
- Any separate technology references.

If the dedicated Tech Stack field is empty, missing, says "See project description", or contains a similar placeholder, extract the technologies directly from the project details.

Identify all explicitly mentioned technologies that the candidate actually used, integrated, or worked with, including:

- Programming languages.
- Frameworks and libraries.
- APIs and AI/LLM providers.
- Databases and services.
- Development and automation platforms.
- Cloud and deployment tools.
- External platforms and integrations.
- Relevant standards and technologies.

Do not include generic technical concepts as technologies unless they refer to a specific named tool, platform, or technology.

Do not assume that a technology was used just because it is commonly associated with the type of project.

### Example of Tech Stack extraction

Suppose the project description mentions:

- Built using Python.
- Automated execution through GitHub Actions.
- Integrated Groq and Gemini APIs.
- Used Jinja2 for templating.
- Generated PDFs using LaTeX.
- Integrated with Greenhouse, Lever, Ashby, Workable, SmartRecruiters, and Workday.

The expected output would be:

`"techStack": "Python, GitHub Actions, Groq, Gemini, Jinja2, LaTeX, Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Workday"`

Do not return an empty string simply because the knowledge base does not provide a dedicated technology list.

**Every selected project must have its own correctly populated `techStack` property.**

# 5. WRITING STYLE — EXTREMELY IMPORTANT

The entire resume must use **simple, clear, natural English**.

The objective is to make the candidate sound like a technically capable person who understands their work, not someone who has copied polished sentences from an AI tool.

Follow these instructions throughout the summary, experience bullets, and projects.

### Use simple everyday English

Prefer common words over fancy vocabulary.

Use direct sentences that a person would naturally use when explaining their work during an interview.

### Show understanding instead of using impressive words

Explain what was implemented, how a technology was used, and what the candidate worked on.

The recruiter should be able to understand the candidate's actual knowledge from the content.

### Avoid AI-generated and corporate language

Do not use unnecessarily polished expressions such as:

- "Spearheaded the development of..."
- "Leveraged cutting-edge technologies..."
- "Demonstrated a strong ability to..."
- "Played a pivotal role in..."
- "Engineered robust and scalable solutions..."
- "Orchestrated end-to-end implementation..."
- "Utilized sophisticated methodologies..."
- "Successfully drove business transformation..."

Use straightforward alternatives wherever accurate:

- Built
- Developed
- Used
- Implemented
- Created
- Worked on
- Analysed
- Integrated
- Automated
- Improved
- Designed

### Avoid unnecessary technical jargon

Technical terms should be used when they are relevant to the job and accurately describe the work.

Do not make a simple implementation sound unnecessarily complicated.

### Do not stuff keywords

Use relevant keywords from the job description naturally.

Do not insert technologies or technical terms just to improve ATS matching.

### Keep bullets readable

- Prefer one clear idea per bullet.
- Avoid excessively long sentences.
- Do not combine several unrelated responsibilities into one bullet.
- Avoid repetitive sentence structures.
- Keep the language consistent across all resume sections.

### Example of the expected writing style

Avoid:

"Leveraged Python and advanced machine learning methodologies to develop a sophisticated predictive analytics solution, enabling data-driven business decisions."

Prefer:

"Used Python and machine learning to analyse data, identify patterns, and build models for business forecasting."

The second version is direct, natural, and demonstrates practical understanding.

**The resume should sound professional because the candidate knows their work, not because the language is unnecessarily sophisticated.**

# 6. ONE-PAGE RESUME REQUIREMENT — CRITICAL

The generated content is intended for a **one-page resume**. The page should be properly filled, balanced, and visually complete rather than having a large empty area at the bottom.

This is a very important requirement.

Follow these rules:

- Generate sufficient relevant content to make effective use of the available page.
- Give proper detail to technical experience and selected projects.
- Do not make every bullet unnecessarily short.
- Select the strongest relevant experience and projects.
- Make good use of the available content without repeating information.
- Keep the summary concise so more space is available for practical experience and projects.
- Use meaningful technical details to provide substance.
- Do not add irrelevant responsibilities, generic statements, or filler just to occupy space.
- Never invent achievements, metrics, technologies, or responsibilities to fill the page.

Aim for a well-filled, balanced, readable one-page resume.

**Priority order:**
1. Factual accuracy.
2. Relevance to the target job.
3. Natural and readable English.
4. Effective use of the available page space.

Do not sacrifice accuracy or readability just to fill the page.

# 7. APPLICATION QUESTIONS

Read the complete job description and identify all explicit questions or instructions directed at applicants.

Examples:

- Why do you want to work with us?
- Why are you interested in this position?
- Describe your relevant experience.
- What makes you a good fit for this role?
- Tell us about a project you have worked on.
- Describe your experience with a particular technology.

For every identified question:

- Provide a truthful answer using only the candidate's resume and project knowledge base.
- Use simple, conversational English.
- Make the response sound like the candidate is explaining something in a real interview or conversation.
- Show actual knowledge and experience rather than making generic claims.
- Keep answers direct and relevant.
- Do not begin by repeating the question.
- Avoid corporate language, unnecessary introductions, and forced enthusiasm.
- Do not claim experience, skills, or achievements that are not supported by the provided information.

If no application questions are present, return an empty array.

# 8. STRICT FACTUAL RULES — NON-NEGOTIABLE

1. NEVER invent a skill, technology, tool, achievement, responsibility, employer, or metric.
2. Use only information available in the candidate's resume context and project knowledge base.
3. `summary` must accurately represent the candidate's existing background.
4. `experience_bullets` MUST contain exactly `{experience_count}` arrays, one for each job in the same order as provided.
5. Each experience array MUST contain 3–5 bullet strings selected or reworded from that job's actual experience.
6. `projects` MUST contain 1–2 entries.
7. Every project MUST have `title`, `dates`, `bullets`, and `techStack`.
8. Each project MUST contain 5–6 bullet strings.
9. Every project MUST have a properly populated `techStack` whenever identifiable technologies are present in its knowledge base.
10. Extract `techStack` from the complete project description, not just the dedicated Tech Stack field.
11. Do not use technologies from one project in another project's techStack unless they are explicitly mentioned for both projects.
12. `application_questions` MUST contain every explicit applicant question found in the job description.
13. Do not include any fixed personal details, employment-identification details, education details, or a separate skills section.
14. Do not include information that is not supported by the provided context.
15. Preserve the original meaning of all experience and project details.

When information is insufficient, do not fill the gaps with assumptions. Factual accuracy always takes priority.

# 9. FINAL VALIDATION BEFORE RETURNING OUTPUT

Before generating the final JSON, silently verify the following:

**Content validation:**
- Is the summary specific to this job?
- Are the experience bullets selected from the correct jobs?
- Are the projects genuinely relevant to the target role?
- Does the writing sound natural and human?
- Are there any exaggerated or unsupported claims?

**Tech Stack validation:**
- Does every selected project have a `techStack` property?
- Did you examine the entire project description for technologies?
- Did you extract technologies from bullets when the dedicated Tech Stack field was unavailable?
- Is the techStack non-empty whenever identifiable technologies are present?
- Have you avoided adding assumed or unrelated technologies?

**Structure validation:**
- Does the experience array count exactly match `{experience_count}`?
- Does every experience array contain 3–5 bullets?
- Are there 1–2 selected projects?
- Does each project contain 5–6 bullets?
- Does every project include its original title and dates?
- Are all application questions answered?
- Is the output valid JSON with exactly the required four top-level keys?

Correct any issues before returning the response.

# 10. INPUT

JOB DESCRIPTION:

{job_description}

CANDIDATE'S RESUME CONTEXT:

{resume_context}

PROJECT KNOWLEDGE BASE:

{knowledge_base}

NUMBER OF JOBS:

{experience_count}

# 11. OUTPUT FORMAT

Return ONLY valid JSON.

Do not include Markdown code fences, explanations, notes, or commentary.

Use exactly this structure:

{
  "summary": "Tailored professional summary",
  "experience_bullets": [
    [
      "Bullet 1",
      "Bullet 2",
      "Bullet 3"
    ],
    [
      "Bullet 1",
      "Bullet 2",
      "Bullet 3"
    ]
  ],
  "projects": [
    {
      "title": "Original project title",
      "dates": "Project dates",
      "bullets": [
        "Bullet 1",
        "Bullet 2",
        "Bullet 3",
        "Bullet 4",
        "Bullet 5"
      ],
      "techStack": "Technology 1, Technology 2, Technology 3"
    }
  ],
  "application_questions": [
    {
      "question": "Question from the job description",
      "answer": "Natural, truthful answer"
    }
  ]
}

The example above shows the structure only. The actual number of experience arrays must match `{experience_count}`. """


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
