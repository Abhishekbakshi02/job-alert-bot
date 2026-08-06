"""
Renders resume content (a dict shaped like resume_data.json) into a PDF
using ALWAYS the same template - only the content differs per job.
Pure-Python (reportlab) - no LibreOffice/system dependency needed.

Layout mirrors the original hand-designed resume: centered header, thin
underlined section dividers, a single consistent bullet style with
proper hanging indent, and tab-aligned title/date rows.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, HRFlowable, Spacer,
)
from reportlab.lib.styles import ParagraphStyle

DARK = HexColor("#1a1a1a")
LINE = HexColor("#3d3d3d")
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

NAME_STYLE = ParagraphStyle(
    "name", fontName=FONT_BOLD, fontSize=18, alignment=TA_CENTER,
    textColor=DARK, spaceAfter=3,
)
CONTACT_STYLE = ParagraphStyle(
    "contact", fontName=FONT, fontSize=9.3, alignment=TA_CENTER,
    textColor=DARK, spaceAfter=8,
)
HEADING_STYLE = ParagraphStyle(
    "heading", fontName=FONT_BOLD, fontSize=11.5, textColor=DARK,
    spaceBefore=7, spaceAfter=2,
)
BODY_STYLE = ParagraphStyle(
    "body", fontName=FONT, fontSize=9.3, leading=12.5, textColor=DARK, spaceAfter=3,
)
# Single consistent bullet style for BOTH experience and project bullets.
# leftIndent = where wrapped lines land; bulletIndent = where the "•" sits.
# The gap between them is what gives a proper hanging indent.
BULLET_STYLE = ParagraphStyle(
    "bullet", fontName=FONT, fontSize=9.3, leading=12.5, textColor=DARK,
    leftIndent=16, bulletIndent=4, spaceAfter=1.5,
)
TECHSTACK_STYLE = ParagraphStyle(
    "techstack", fontName=FONT, fontSize=8.8, leading=11.5, textColor=DARK,
    leftIndent=16, spaceAfter=5,
)
ENTRY_TITLE_STYLE = ParagraphStyle(
    "entrytitle", fontName=FONT_BOLD, fontSize=10, textColor=DARK,
)
ENTRY_DATE_STYLE = ParagraphStyle(
    "entrydate", fontName=FONT, fontSize=9.5, textColor=DARK, alignment=2,
)


def _section_heading(text):
    return [
        Paragraph(text, HEADING_STYLE),
        HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=5),
    ]


def _entry_row(left_text, right_text):
    table = Table(
        [[Paragraph(left_text, ENTRY_TITLE_STYLE), Paragraph(right_text, ENTRY_DATE_STYLE)]],
        colWidths=[5.5 * inch, 1.75 * inch],
    )
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _bullet(text):
    return Paragraph(text, BULLET_STYLE, bulletText="\u2022")


def _tech_stack(label, value):
    return Paragraph(f"<b>{label}</b> {value}", TECHSTACK_STYLE)


def build_resume_pdf(data: dict, output_path: str) -> None:
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.4 * inch, bottomMargin=0.4 * inch,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
    )
    story = []

    story.append(Paragraph(data["name"], NAME_STYLE))
    contact = f"{data['email']}   |   {data['linkedin']}   |   {data['phone']}   |   {data['location']}"
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
            story.append(_bullet(bullet))
        story.append(_tech_stack("Tech Stack Used:", job["techStack"]))

    story += _section_heading("Projects")
    for proj in data["projects"]:
        story.append(_entry_row(proj["name"], proj["dates"]))
        for bullet in proj["bullets"]:
            story.append(_bullet(bullet))
        story.append(_tech_stack("Tech Stack:", proj["techStack"]))

    story += _section_heading("Education")
    edu = data["education"]
    story.append(_entry_row(edu["school"], edu["dates"]))
    story.append(Paragraph(f'{edu["degree"]}<br/>{edu["gpa"]}', BODY_STYLE))

    doc.build(story)
