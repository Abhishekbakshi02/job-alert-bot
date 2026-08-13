"""
Adapter between our resume schema and the precise pixel-measured LaTeX
template - with a pure-Python backup renderer if LaTeX itself fails for
any reason (toolchain hiccup, unexpected compile error, timeout, etc.).
Two independent rendering paths means an attachment essentially always
goes out, even if the primary path has a bad day.
"""

from latex_renderer import render_resume
from simple_pdf_fallback import render_resume_simple


def _adapt(resume: dict) -> dict:
    education = resume.get("education") or {}
    if not isinstance(education, dict):
        education = {}

    return {
        "name": resume.get("name", ""),
        "contact": {
            "email": resume.get("email", ""),
            "linkedin_label": resume.get("linkedin", ""),
            "phone": resume.get("phone", ""),
            "location": resume.get("location", ""),
        },
        "summary": resume.get("summary", ""),
        "skills": resume.get("skills") or [],
        "experience": [
            {
                "title": f"{job.get('title', '')} | {job.get('company', '')}".strip(" |"),
                "dates": job.get("dates", ""),
                "bullets": job.get("bullets") or [],
                "tech_stack": job.get("techStack", ""),
            }
            for job in (resume.get("experience") or [])
        ],
        "projects": [
            {
                "title": proj.get("name") or proj.get("title", ""),
                "dates": proj.get("dates", ""),
                "bullets": proj.get("bullets") or [],
                "tech_stack": proj.get("techStack", ""),
            }
            for proj in (resume.get("projects") or [])
        ],
        "education": [
            {
                "institute": education.get("school", ""),
                "dates": education.get("dates", ""),
                "degree": education.get("degree", ""),
                "extra": education.get("gpa", ""),
            }
        ],
    }


def build_resume_pdf(resume: dict, output_path: str) -> None:
    try:
        render_resume(_adapt(resume), output_path)
    except Exception as e:
        print(f"[WARN] LaTeX resume rendering failed ({e}) - using simpler backup renderer instead")
        render_resume_simple(resume, output_path)
