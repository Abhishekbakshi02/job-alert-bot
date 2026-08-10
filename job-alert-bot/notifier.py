"""
Sends the actual notification email via Brevo once a job has been
confirmed as a match - optionally with a tailored resume attached, and
optionally with AI-answered application questions included in the body.
"""

import os
import base64
import requests

BREVO_API_KEY = os.environ["BREVO_API_KEY"].strip()
SENDER_EMAIL = os.environ["SENDER_EMAIL"].strip()
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"].strip()


def _answers_html(application_answers: list) -> str:
    if not application_answers:
        return ""
    items = "".join(
        f"<p><b>Q: {qa['question']}</b><br>{qa['answer']}</p>"
        for qa in application_answers
    )
    return f"<hr><p><b>This posting included application questions - draft answers:</b></p>{items}"


def send_job_alert(title: str, company: str, location: str, url: str, reason: str,
                    resume_path: str = None, application_answers: list = None) -> None:
    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "Job Alert Bot"},
        "to": [{"email": NOTIFY_EMAIL}],
        "subject": f"Job match: {title} at {company}",
        "htmlContent": (
            f"<p>This job looks suitable for you:</p>"
            f"<p><b>{title}</b> — {company}<br>"
            f"Location: {location}<br>"
            f"Why it matched: {reason}</p>"
            f'<p><a href="{url}">View the listing</a></p>'
            + ("<p>A tailored resume for this role is attached.</p>" if resume_path else "")
            + _answers_html(application_answers or [])
        ),
    }

    if resume_path:
        with open(resume_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        payload["attachment"] = [{"content": encoded, "name": os.path.basename(resume_path)}]

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
