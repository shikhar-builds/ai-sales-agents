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
APP_PASSWORD   = "rdnu exum swzo ojkr"       # ← your 16-char app password
SEND_TO        = "shikhar.srivastava1601@gmail.com"      # ← who receives it (yourself for now)


# ── Sender ────────────────────────────────────────────────────────────────────

def send_digest_email(pdf_path):
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
    body = f"""Hi,

Please find attached your Daily Client Digest for {today_str}.

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