"""
Renders resume content (a dict shaped like resume_data.json) into a PDF
using ALWAYS the same template - only the content differs per job.
Pure-Python (reportlab) - no LibreOffice/system dependency needed, which
keeps this fast and reliable inside GitHub Actions.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, HRFlowable,
)
from reportlab.lib.styles import ParagraphStyle

DARK = HexColor("#1a1a1a")
LINE = HexColor("#444444")

NAME_STYLE = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=17, alignment=TA_CENTER, textColor=DARK, spaceAfter=2)
CONTACT_STYLE = ParagraphStyle("contact", fontName="Helvetica", fontSize=9, alignment=TA_CENTER, textColor=DARK, spaceAfter=6)
HEADING_STYLE = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=11, textColor=DARK, spaceBefore=5, spaceAfter=1)
BODY_STYLE = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12, textColor=DARK, spaceAfter=2)
BULLET_STYLE = ParagraphStyle("bullet", fontName="Helvetica", fontSize=9, leading=12, textColor=DARK, leftIndent=14, spaceAfter=1)
SUBBULLET_STYLE = ParagraphStyle("subbullet", fontName="Helvetica", fontSize=9, leading=12, textColor=DARK, leftIndent=28, spaceAfter=1)
TECHSTACK_STYLE = ParagraphStyle("techstack", fontName="Helvetica", fontSize=8.5, leading=11, textColor=DARK, leftIndent=14, spaceAfter=4)
ENTRY_TITLE_STYLE = ParagraphStyle("entrytitle", fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK)
ENTRY_DATE_STYLE = ParagraphStyle("entrydate", fontName="Helvetica", fontSize=9.5, textColor=DARK, alignment=2)


def _section_heading(text):
    return [
        Paragraph(text, HEADING_STYLE),
        HRFlowable(width="100%", thickness=0.75, color=LINE, spaceAfter=3),
    ]


def _entry_row(left_text, right_text):
    table = Table(
        [[Paragraph(left_text, ENTRY_TITLE_STYLE), Paragraph(right_text, ENTRY_DATE_STYLE)]],
        colWidths=[5.3 * inch, 1.7 * inch],
    )
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _tech_stack(label, value):
    return Paragraph(f"<b>{label}</b> {value}", TECHSTACK_STYLE)


def build_resume_pdf(data: dict, output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.25 * inch, bottomMargin=0.25 * inch,
        leftMargin=0.45 * inch, rightMargin=0.45 * inch,
    )
    story = []

    story.append(Paragraph(data["name"], NAME_STYLE))
    contact = f"{data['email']}  |  {data['linkedin']}  |  {data['phone']}  |  {data['location']}"
    story.append(Paragraph(contact, CONTACT_STYLE))

    story += _section_heading("Summary")
    story.append(Paragraph(data["summary"], BODY_STYLE))

    story += _section_heading("Technical Skills")
    for skill in data["skills"]:
        story.append(Paragraph(f'<b>{skill["label"]}:</b> {skill["value"]}', BODY_STYLE))

    story += _section_heading("Experience")
    for job in data["experience"]:
        story.append(_entry_row(f"{job['title']} | {job['company']}", job["dates"]))
        for bullet in job["bullets"]:
            story.append(Paragraph(f"&#8226;  {bullet}", BULLET_STYLE))
        story.append(_tech_stack("Tech Stack Used:", job["techStack"]))

    story += _section_heading("Projects")
    for proj in data["projects"]:
        story.append(_entry_row(proj["name"], proj["dates"]))
        for bullet in proj["bullets"]:
            story.append(Paragraph(f"&#9702;  {bullet}", SUBBULLET_STYLE))
        story.append(_tech_stack("Tech Stack:", proj["techStack"]))

    story += _section_heading("Education")
    edu = data["education"]
    story.append(_entry_row(edu["school"], edu["dates"]))
    story.append(Paragraph(f'{edu["degree"]}      {edu["gpa"]}', BODY_STYLE))

    doc.build(story)
