"""
Last-resort resume PDF renderer - pure Python (reportlab), no external
toolchain, no subprocess, no font files to locate. Used ONLY if the
LaTeX renderer fails for any reason. Plainer formatting than the LaTeX
version, but it has almost nothing that can go wrong, which is exactly
the point: a slightly less polished resume beats no attachment at all.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable
from reportlab.lib.styles import ParagraphStyle

NAME_STYLE = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER, spaceAfter=4)
CONTACT_STYLE = ParagraphStyle("contact", fontName="Helvetica", fontSize=9, alignment=TA_CENTER, spaceAfter=10)
HEADING_STYLE = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=11, spaceBefore=8, spaceAfter=3)
BODY_STYLE = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13, spaceAfter=3)
BULLET_STYLE = ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5, leading=13, leftIndent=14, spaceAfter=2)


def _s(value) -> str:
    return str(value) if value is not None else ""


def render_resume_simple(resume: dict, output_path: str) -> None:
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    story = []

    story.append(Paragraph(_s(resume.get("name", "")), NAME_STYLE))
    contact = " | ".join(filter(None, [
        _s(resume.get("email", "")), _s(resume.get("linkedin", "")),
        _s(resume.get("phone", "")), _s(resume.get("location", "")),
    ]))
    story.append(Paragraph(contact, CONTACT_STYLE))

    story.append(Paragraph("Summary", HEADING_STYLE))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Paragraph(_s(resume.get("summary", "")), BODY_STYLE))

    story.append(Paragraph("Technical Skills", HEADING_STYLE))
    story.append(HRFlowable(width="100%", thickness=1))
    for skill in (resume.get("skills") or []):
        story.append(Paragraph(f"<b>{_s(skill.get('label',''))}:</b> {_s(skill.get('value',''))}", BODY_STYLE))

    story.append(Paragraph("Experience", HEADING_STYLE))
    story.append(HRFlowable(width="100%", thickness=1))
    for job in (resume.get("experience") or []):
        story.append(Paragraph(f"<b>{_s(job.get('title',''))} | {_s(job.get('company',''))}</b> - {_s(job.get('dates',''))}", BODY_STYLE))
        for bullet in (job.get("bullets") or []):
            story.append(Paragraph(f"&#8226; {_s(bullet)}", BULLET_STYLE))
        if job.get("techStack"):
            story.append(Paragraph(f"<b>Tech Stack:</b> {_s(job.get('techStack',''))}", BULLET_STYLE))

    story.append(Paragraph("Projects", HEADING_STYLE))
    story.append(HRFlowable(width="100%", thickness=1))
    for proj in (resume.get("projects") or []):
        title = proj.get("name") or proj.get("title", "")
        story.append(Paragraph(f"<b>{_s(title)}</b> - {_s(proj.get('dates',''))}", BODY_STYLE))
        for bullet in (proj.get("bullets") or []):
            story.append(Paragraph(f"&#8226; {_s(bullet)}", BULLET_STYLE))
        if proj.get("techStack"):
            story.append(Paragraph(f"<b>Tech Stack:</b> {_s(proj.get('techStack',''))}", BULLET_STYLE))

    edu = resume.get("education") or {}
    story.append(Paragraph("Education", HEADING_STYLE))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Paragraph(f"<b>{_s(edu.get('school',''))}</b> - {_s(edu.get('dates',''))}", BODY_STYLE))
    story.append(Paragraph(f"{_s(edu.get('degree',''))} | {_s(edu.get('gpa',''))}", BODY_STYLE))

    doc.build(story)
