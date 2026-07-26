"""
Sends the actual notification email via Brevo once a job has been
confirmed as a match.
"""

import os
import requests

BREVO_API_KEY = os.environ["BREVO_API_KEY"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]  # the address you verified in Brevo
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]  # the inbox that should receive alerts


def send_job_alert(title: str, company: str, location: str, url: str, reason: str) -> None:
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
        ),
    }
    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
