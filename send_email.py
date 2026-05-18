"""
send_email.py
-------------
Sends the daily client digest PDF via Gmail SMTP.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

GMAIL_ADDRESS  = "shikhar.srivastava1601@gmail.com"      # ← your Gmail address
APP_PASSWORD   = "xxxx xxxx xxxx xxxx"       # ← set your Gmail App Password here
SEND_TO        = "shikhar.srivastava1601@gmail.com"      # ← who receives it (yourself for now)


# ── Sender ────────────────────────────────────────────────────────────────────

def send_digest_email(pdf_path, summary=""):
    """Attach PDF and send via Gmail SMTP."""

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return

    today_str = datetime.today().strftime("%A, %d %B %Y")

    # Build email
    msg = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = SEND_TO
    msg["Subject"] = f"Daily Client Digest — {today_str}"

  # Body
    summary_block = f"AI Executive Summary:\n{summary}\n\n" if summary else ""

    body = f"""Hi,

{summary_block}Please find attached your Daily Client Digest for {today_str}.

This report includes:
  • Top 3 clients by revenue
  • Open pipeline opportunities
  • Follow-ups needed (7+ days since last contact)

Generated automatically by digest_agent.py

"""
    msg.attach(MIMEText(body, "plain"))

    # Attach PDF
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(pdf_path)}"
        )
        msg.attach(part)

    # Send
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, SEND_TO, msg.as_string())
        print(f"✅ Email sent to {SEND_TO}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def send_prep_email(pdf_path, client_name, summary=""):
    """Send meeting prep PDF as a separate email."""

    if not os.path.exists(pdf_path):
        print(f"❌ Prep PDF not found: {pdf_path}")
        return

    today_str = datetime.today().strftime("%A, %d %B %Y")

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = SEND_TO
    msg["Subject"] = f"Meeting Prep — {client_name} — {today_str}"

    summary_block = f"Talking Points:\n{summary}\n\n" if summary else ""

    body = f"""Hi,

{summary_block}Please find attached your Meeting Prep sheet for {client_name}.

Generated automatically by morning_briefing.py

"""
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(pdf_path)}"
        )
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, SEND_TO, msg.as_string())
        print(f"✅ Prep email sent to {SEND_TO}")
    except Exception as e:
        print(f"❌ Prep email failed: {e}")