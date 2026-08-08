"""
Adapter between our resume_data.json / Gemini-tailored schema and the
precise pixel-measured template in resume_template.py. Keeps
resume_tailor.py's tested prompt/schema completely unchanged - this is
the only place that knows about the template's specific field names.
"""
from latex_renderer import render_resume


def _adapt(resume: dict) -> dict:
    return {
        "name": resume["name"],
        "contact": {
            "email": resume["email"],
            "linkedin_label": resume["linkedin"],
            "phone": resume["phone"],
            "location": resume["location"],
        },
        "summary": resume["summary"],
        "skills": resume["skills"],
        "experience": [
            {
                "title": f"{job['title']} | {job['company']}",
                "dates": job["dates"],
                "bullets": job["bullets"],
                "tech_stack": job["techStack"],
            }
            for job in resume["experience"]
        ],
        "projects": [
            {
                "title": proj["name"],
                "dates": proj["dates"],
                "bullets": proj["bullets"],
                "tech_stack": proj["techStack"],
            }
            for proj in resume["projects"]
        ],
        "education": [
            {
                "institute": resume["education"]["school"],
                "dates": resume["education"]["dates"],
                "degree": resume["education"]["degree"],
                "extra": resume["education"]["gpa"],
            }
        ],
    }


def build_resume_pdf(resume: dict, output_path: str) -> None:
    """Same interface main.py already calls - now backed by the precise template."""
    render_resume(_adapt(resume), output_path)
