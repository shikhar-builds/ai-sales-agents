"""
email_intel.py
--------------
Email Intelligence Engine for Senior KAMs.
Connects to Gmail via IMAP, pulls emails for a named client (last 30 days),
sends threads to Claude API, extracts structured intelligence.

Output: terminal + .md file (PDF/PPT-ready)

Auth: Gmail App Password via GMAIL_APP_PASSWORD env var
      Claude API key via ANTHROPIC_API_KEY env var

Three-signal client matching:
  1. Sender email address (primary)
  2. Email signature / sign-off in body (secondary)
  3. Subject line keywords (tertiary)
"""

import os
import sys
import imaplib
import email
import json
import re
import requests
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

# ── Config ────────────────────────────────────────────────────────────────────

BASE          = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"
GMAIL_ADDRESS = "shikhar.srivastava1601@gmail.com"
IMAP_HOST     = "imap.gmail.com"
IMAP_PORT     = 993
LOOKBACK_DAYS = 30
MAX_EMAILS    = 50       # cap to avoid token blowout
MAX_BODY_CHARS= 3000     # per email body — keeps prompt lean
CLAUDE_MODEL  = "claude-sonnet-4-6"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ── Env ───────────────────────────────────────────────────────────────────────

def get_env(key):
    val = os.environ.get(key)
    if not val:
        print(f"\n  ❌ Missing env var: {key}")
        print(f"     Add to ~/.zshrc:  export {key}='your_value_here'")
        print(f"     Then run:         source ~/.zshrc\n")
        sys.exit(1)
    return val

# ── Gmail IMAP connection ─────────────────────────────────────────────────────

def connect_gmail(app_password):
    """Connect to Gmail via IMAP SSL."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GMAIL_ADDRESS, app_password)
        print("  ✅ Gmail connected")
        return mail
    except imaplib.IMAP4.error as e:
        print(f"\n  ❌ Gmail login failed: {e}")
        print("     Check GMAIL_APP_PASSWORD is correct and IMAP is enabled in Gmail settings.")
        sys.exit(1)

# ── Email fetching ────────────────────────────────────────────────────────────

def decode_str(s):
    """Decode encoded email header strings."""
    if s is None:
        return ""
    parts = decode_header(s)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def get_body(msg):
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp  = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            pass
    return body.strip()


def fetch_recent_emails(mail, days=LOOKBACK_DAYS):
    """Fetch all emails from inbox + sent in last N days."""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    emails = []

    for folder in ['"[Gmail]/All Mail"', "INBOX", '"[Gmail]/Sent Mail"']:
        try:
            result, _ = mail.select(folder, readonly=True)
            if result != "OK":
                continue

            result, data = mail.search(None, f'(SINCE "{since_date}")')
            if result != "OK" or not data[0]:
                continue

            ids = data[0].split()
            # Take most recent MAX_EMAILS across all folders
            ids = ids[-MAX_EMAILS:]

            for eid in ids:
                result, msg_data = mail.fetch(eid, "(RFC822)")
                if result != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                sender      = decode_str(msg.get("From", ""))
                recipient   = decode_str(msg.get("To", ""))
                subject     = decode_str(msg.get("Subject", ""))
                date_header = msg.get("Date", "")
                body        = get_body(msg)

                # Parse date safely
                try:
                    msg_date = parsedate_to_datetime(date_header)
                    # Make both timezone-aware for comparison
                    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                    if msg_date.tzinfo is None:
                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                    if msg_date < cutoff:
                        continue
                    date_str = msg_date.strftime("%d %b %Y %H:%M")
                except Exception:
                    date_str = date_header

                emails.append({
                    "id":        eid.decode(),
                    "sender":    sender,
                    "recipient": recipient,
                    "subject":   subject,
                    "date":      date_str,
                    "body":      body[:MAX_BODY_CHARS],
                })

        except Exception as e:
            print(f"  ⚠️  Could not read folder {folder}: {e}")
            continue

    # Deduplicate by subject + sender
    seen = set()
    unique = []
    for e in emails:
        key = (e["sender"], e["subject"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique

# ── Three-signal client matching ──────────────────────────────────────────────

def build_keywords(client_name):
    """
    Build keyword variants from client name.
    'Standard Chartered' → ['standard chartered', 'standard', 'chartered', 'sc']
    """
    name_lower = client_name.lower().strip()
    words      = name_lower.split()
    keywords   = [name_lower] + words

    # Common abbreviations for two-word names
    if len(words) == 2:
        keywords.append("".join(w[0] for w in words))  # initials e.g. 'sc'

    return list(set(keywords))


def signal_1_sender(sender, keywords):
    """Primary: sender email or display name contains client keyword."""
    sender_lower = sender.lower()
    # Extract domain from email address
    _, addr = parseaddr(sender)
    domain = addr.split("@")[-1].lower() if "@" in addr else ""
    for kw in keywords:
        if len(kw) > 2 and (kw in sender_lower or kw in domain):
            return True
    return False


def signal_2_signature(body, keywords):
    """
    Secondary: signature/sign-off in last 20 lines of body.
    Looks for client name in the closing section.
    """
    lines = body.strip().split("\n")
    closing = "\n".join(lines[-20:]).lower()
    for kw in keywords:
        if len(kw) > 3 and kw in closing:
            return True
    return False


def signal_3_subject(subject, keywords):
    """Tertiary: subject line contains client name keyword."""
    subject_lower = subject.lower()
    for kw in keywords:
        if len(kw) > 3 and kw in subject_lower:
            return True
    return False


def match_emails(emails, client_name):
    """Apply three-signal matching. Return matched emails with signal flags."""
    keywords = build_keywords(client_name)
    matched  = []

    for e in emails:
        s1 = signal_1_sender(e["sender"], keywords)
        s2 = signal_2_signature(e["body"], keywords)
        s3 = signal_3_subject(e["subject"], keywords)

        if s1 or s2 or s3:
            matched.append({
                **e,
                "signals": {
                    "sender_match":    s1,
                    "signature_match": s2,
                    "subject_match":   s3,
                }
            })

    return matched

# ── Thread grouping ───────────────────────────────────────────────────────────

def group_into_threads(emails):
    """Group emails by subject (normalised — strip Re:/Fwd:)."""
    def normalise(subject):
        return re.sub(r"^(re|fwd|fw):\s*", "", subject.strip().lower(), flags=re.IGNORECASE)

    threads = {}
    for e in emails:
        key = normalise(e["subject"])
        if key not in threads:
            threads[key] = []
        threads[key].append(e)

    # Sort each thread by date
    for key in threads:
        threads[key].sort(key=lambda x: x["date"])

    return threads

# ── Claude API call ───────────────────────────────────────────────────────────

def call_claude(prompt, api_key):
    """Direct HTTP call to Claude API. No LangChain. No wrappers."""
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model":      CLAUDE_MODEL,
        "max_tokens": 1500,
        "messages":   [{"role": "user", "content": prompt}],
    }
    try:
        response = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"].strip()
    except requests.exceptions.RequestException as e:
        print(f"\n  ❌ Claude API call failed: {e}")
        return None

# ── Prompt builder ────────────────────────────────────────────────────────────

def build_extraction_prompt(client_name, threads):
    """Build Claude prompt with XML tags. Non-negotiable."""

    thread_blocks = ""
    for subject, emails in threads.items():
        thread_blocks += f"\n<thread subject='{subject}'>\n"
        for e in emails:
            thread_blocks += f"""<email>
  <date>{e['date']}</date>
  <sender>{e['sender']}</sender>
  <recipient>{e['recipient']}</recipient>
  <body>{e['body']}</body>
</email>
"""
        thread_blocks += "</thread>\n"

    prompt = f"""You are an AI assistant for a Senior Key Account Manager at a B2B payments company.

Your job is to extract structured intelligence from email threads with a named client.
Be precise. Extract only what is explicitly stated. Do not infer or invent.

<client_name>{client_name}</client_name>

<email_threads>
{thread_blocks}
</email_threads>

Extract and return the following in this exact XML structure:

<intelligence>

<decisions_made>
List every decision that has been confirmed or agreed in these threads.
Format: one decision per line, with date if available.
If none: write "None identified."
</decisions_made>

<open_actions>
List every open action item — things promised but not yet confirmed as done.
Include who owns each action (KAM or client).
Format: [Owner] Action — by [date if stated]
If none: write "None identified."
</open_actions>

<pain_points>
List every complaint, frustration, or problem the client has raised.
Include severity signals (e.g. CTO involved, formal review risk, conversion impact).
Format: one pain point per line with severity indicator.
If none: write "None identified."
</pain_points>

<relationship_risks>
Identify any signals that the relationship is at risk.
Consider: competitor mentions, escalations, procurement reviews, tone shifts, decision-maker changes.
Rate each risk: LOW / MEDIUM / HIGH.
If none: write "None identified."
</relationship_risks>

<upsell_signals>
Identify any signals of genuine upsell or expansion opportunity.
Include: products discussed, interest level, timing signals, stakeholders involved.
If none: write "None identified."
</upsell_signals>

<relationship_temperature>
One paragraph summary of the overall relationship health.
Cover: communication tone, engagement level, trust indicators, structural risks.
</relationship_temperature>

</intelligence>

Be concise. Use plain English. No markdown formatting inside the XML tags."""

    return prompt.strip()

# ── Parse Claude output ───────────────────────────────────────────────────────

def parse_intelligence(raw_output):
    """Extract sections from Claude's XML response."""
    sections = [
        "decisions_made",
        "open_actions",
        "pain_points",
        "relationship_risks",
        "upsell_signals",
        "relationship_temperature",
    ]
    result = {}
    for section in sections:
        pattern = rf"<{section}>(.*?)</{section}>"
        match = re.search(pattern, raw_output, re.DOTALL)
        result[section] = match.group(1).strip() if match else "Could not parse."
    return result

# ── Terminal display ──────────────────────────────────────────────────────────

def print_intelligence(client_name, intel, thread_count, email_count):
    width = 65
    print("\n" + "=" * width)
    print(f"  🧠  EMAIL INTELLIGENCE — {client_name.upper()}")
    print(f"  📬  {email_count} emails · {thread_count} threads · last {LOOKBACK_DAYS} days")
    print("=" * width)

    labels = {
        "decisions_made":          ("✅", "DECISIONS MADE"),
        "open_actions":            ("📋", "OPEN ACTIONS"),
        "pain_points":             ("⚠️ ", "PAIN POINTS"),
        "relationship_risks":      ("🔴", "RELATIONSHIP RISKS"),
        "upsell_signals":          ("💚", "UPSELL SIGNALS"),
        "relationship_temperature":("🌡️ ", "RELATIONSHIP TEMPERATURE"),
    }

    for key, (icon, label) in labels.items():
        print(f"\n  {icon}  {label}")
        print("  " + "-" * (width - 2))
        for line in intel[key].split("\n"):
            print(f"  {line}")

    print("\n" + "=" * width)

# ── Markdown export ───────────────────────────────────────────────────────────

def export_markdown(client_name, intel, thread_count, email_count):
    """Save intelligence as .md file for PDF/PPT conversion."""
    today = datetime.today().strftime("%Y%m%d")
    filename = BASE + f"email_intel_{client_name.replace(' ', '_')}_{today}.md"

    labels = {
        "decisions_made":          "Decisions Made",
        "open_actions":            "Open Actions",
        "pain_points":             "Pain Points",
        "relationship_risks":      "Relationship Risks",
        "upsell_signals":          "Upsell Signals",
        "relationship_temperature":"Relationship Temperature",
    }

    lines = [
        f"# Email Intelligence — {client_name}",
        f"**Generated:** {datetime.today().strftime('%A, %d %B %Y %H:%M')}",
        f"**Source:** {email_count} emails · {thread_count} threads · last {LOOKBACK_DAYS} days",
        "",
        "---",
        "",
    ]

    for key, label in labels.items():
        lines.append(f"## {label}")
        lines.append("")
        lines.append(intel[key])
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n  📄  Markdown saved: {filename}")
    return filename

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    width = 65
    print("\n" + "=" * width)
    print("  📧  EMAIL INTELLIGENCE ENGINE")
    print("=" * width)

    # 1. Get client name
    if len(sys.argv) > 1:
        client_name = " ".join(sys.argv[1:]).strip()
    else:
        client_name = input("\n  Client name: ").strip()

    if not client_name:
        print("  ❌ No client name provided. Exiting.")
        sys.exit(1)

    print(f"\n  🔍  Searching emails for: {client_name}")
    print(f"  📅  Looking back: {LOOKBACK_DAYS} days\n")

    # 2. Load credentials
    app_password = get_env("GMAIL_APP_PASSWORD")
    api_key      = get_env("ANTHROPIC_API_KEY")

    # 3. Connect and fetch
    print("  Connecting to Gmail...")
    mail = connect_gmail(app_password)

    print("  Fetching recent emails...")
    all_emails = fetch_recent_emails(mail)
    print(f"  ✅ {len(all_emails)} emails fetched")

    mail.logout()

    # 4. Three-signal matching
    print(f"\n  Running three-signal match for '{client_name}'...")
    matched = match_emails(all_emails, client_name)

    if not matched:
        print(f"\n  ⚠️  No emails matched for '{client_name}' in the last {LOOKBACK_DAYS} days.")
        print("  Signals checked: sender email · email signature · subject line")
        print("  Tip: Try a partial name e.g. 'Chartered' instead of 'Standard Chartered'\n")
        sys.exit(0)

    print(f"  ✅ {len(matched)} emails matched")

    # Show signal breakdown
    s1 = sum(1 for e in matched if e["signals"]["sender_match"])
    s2 = sum(1 for e in matched if e["signals"]["signature_match"])
    s3 = sum(1 for e in matched if e["signals"]["subject_match"])
    print(f"     Signal 1 (sender):     {s1} emails")
    print(f"     Signal 2 (signature):  {s2} emails")
    print(f"     Signal 3 (subject):    {s3} emails")

    # 5. Group into threads
    threads = group_into_threads(matched)
    print(f"\n  📂  {len(threads)} thread(s) identified:")
    for subject in threads:
        print(f"     • {subject}  ({len(threads[subject])} emails)")

    # 6. Build prompt and call Claude
    print(f"\n  🤖  Sending to Claude ({CLAUDE_MODEL})...")
    prompt     = build_extraction_prompt(client_name, threads)
    raw_output = call_claude(prompt, api_key)

    if not raw_output:
        print("  ❌ No response from Claude. Check API key and connectivity.")
        sys.exit(1)

    print("  ✅ Intelligence extracted")

    # 7. Parse and display
    intel = parse_intelligence(raw_output)
    print_intelligence(client_name, intel, len(threads), len(matched))

    # 8. Save markdown
    md_file = export_markdown(client_name, intel, len(threads), len(matched))

    print(f"\n  ✅ Done. Next: open {md_file} to review or convert to PDF/PPT.")
    print("=" * width + "\n")


if __name__ == "__main__":
    main()
