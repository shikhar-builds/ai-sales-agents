"""
client_intel.py
---------------
Client Intelligence Engine for Senior KAMs.
Extends email_intel.py with:
  1. Client picker from clients.csv
  2. Optional subject keyword filter
  3. AI-drafted reply to most recent email

Auth: Gmail App Password via GMAIL_APP_PASSWORD env var
      Claude API key via ANTHROPIC_API_KEY env var

Three-signal client matching:
  1. Sender email address (primary)
  2. Email signature / sign-off in body (secondary)
  3. Subject line keywords (tertiary)
"""

import os
import sys
import csv
import imaplib
import smtplib
import email
import re
import requests
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

# ── Config ────────────────────────────────────────────────────────────────────

BASE          = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"
CLIENTS_CSV   = BASE + "clients.csv"
GMAIL_ADDRESS = "shikhar.srivastava1601@gmail.com"
IMAP_HOST     = "imap.gmail.com"
IMAP_PORT     = 993
MAX_EMAILS    = 50
MAX_BODY_CHARS= 3000
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

# ── Client picker ─────────────────────────────────────────────────────────────

def load_clients():
    """Load clients from CSV. Returns list of dicts."""
    if not os.path.exists(CLIENTS_CSV):
        print(f"\n  ❌ clients.csv not found at: {CLIENTS_CSV}")
        sys.exit(1)
    with open(CLIENTS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        clients = [row for row in reader]
    if not clients:
        print("  ❌ clients.csv is empty.")
        sys.exit(1)
    return clients


def prompt_client(clients):
    """Show numbered client list. User picks by number. Returns selected client dict."""
    width = 65
    print(f"\n  {'#':<4} {'Client':<22} {'Stage':<16} {'Pipeline':>12}  {'Growth':>7}")
    print("  " + "-" * (width - 2))
    for i, c in enumerate(clients, 1):
        pipeline = f"${int(c['pipeline_value']):,}"
        print(f"  {i:<4} {c['client_name']:<22} {c['deal_stage']:<16} {pipeline:>12}  {c['growth_target']:>6}%")
    print()

    while True:
        raw = input("  Pick a client [1–{}]: ".format(len(clients))).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(clients):
            return clients[int(raw) - 1]
        print(f"  ⚠️  Enter a number between 1 and {len(clients)}.")


def prompt_lookback():
    """Ask user to choose email lookback window. Returns number of days."""
    print("\n  📅  Email lookback window:")
    print("       1) 7 days")
    print("       2) 14 days")
    print("       3) 30 days (default)")
    print("       4) 90 days")
    choice = input("       Choose [1-4] or Enter for 30 days: ").strip()
    return {"1": 7, "2": 14, "3": 30, "4": 90}.get(choice, 30)


def prompt_keyword_filter():
    """Optional subject keyword filter. Returns string or None."""
    raw = input("\n  🔍  Subject keyword filter (Enter to skip): ").strip()
    return raw if raw else None

# ── Gmail IMAP ────────────────────────────────────────────────────────────────

def connect_gmail(app_password):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GMAIL_ADDRESS, app_password)
        print("  ✅ Gmail connected")
        return mail
    except imaplib.IMAP4.error as e:
        print(f"\n  ❌ Gmail login failed: {e}")
        print("     Check GMAIL_APP_PASSWORD and that IMAP is enabled in Gmail settings.")
        sys.exit(1)

# ── Email fetching ────────────────────────────────────────────────────────────

def decode_str(s):
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


def fetch_recent_emails(mail, days):
    """Fetch emails from inbox + sent in last N days."""
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

            ids = data[0].split()[-MAX_EMAILS:]

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
                message_id  = msg.get("Message-ID", "").strip()
                body        = get_body(msg)

                try:
                    msg_date = parsedate_to_datetime(date_header)
                    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                    if msg_date.tzinfo is None:
                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                    if msg_date < cutoff:
                        continue
                    date_str = msg_date.strftime("%d %b %Y %H:%M")
                    sort_key = msg_date
                except Exception:
                    date_str = date_header
                    sort_key = datetime.min.replace(tzinfo=timezone.utc)

                emails.append({
                    "id":         eid.decode(),
                    "sender":     sender,
                    "recipient":  recipient,
                    "subject":    subject,
                    "date":       date_str,
                    "sort_key":   sort_key,
                    "message_id": message_id,
                    "body":       body[:MAX_BODY_CHARS],
                })

        except Exception as e:
            print(f"  ⚠️  Could not read folder {folder}: {e}")

    # Deduplicate by sender + subject — keep the most recent occurrence of each pair
    # (the same email can appear in both INBOX and All Mail; folders are fetched oldest-first,
    # so a naïve first-seen approach would drop newer duplicates in the same thread)
    best = {}
    for e in emails:
        key = (e["sender"], e["subject"])
        if key not in best or e["sort_key"] > best[key]["sort_key"]:
            best[key] = e

    return list(best.values())

# ── Three-signal client matching ──────────────────────────────────────────────

def build_keywords(client_name):
    name_lower = client_name.lower().strip()
    words      = name_lower.split()
    keywords   = [name_lower] + words
    if len(words) == 2:
        keywords.append("".join(w[0] for w in words))
    return list(set(keywords))


def signal_1_sender(sender, keywords):
    sender_lower = sender.lower()
    _, addr = parseaddr(sender)
    domain = addr.split("@")[-1].lower() if "@" in addr else ""
    for kw in keywords:
        if len(kw) > 2 and (kw in sender_lower or kw in domain):
            return True
    return False


def signal_2_signature(body, keywords):
    lines = body.strip().split("\n")
    closing = "\n".join(lines[-20:]).lower()
    for kw in keywords:
        if len(kw) > 3 and kw in closing:
            return True
    return False


def signal_3_subject(subject, keywords):
    subject_lower = subject.lower()
    for kw in keywords:
        if len(kw) > 3 and kw in subject_lower:
            return True
    return False


def match_emails(emails, client_name, keyword_filter=None):
    """Three-signal match. Optional keyword_filter applied to subject."""
    keywords = build_keywords(client_name)
    matched  = []

    for e in emails:
        # Apply subject keyword filter first if set
        if keyword_filter and keyword_filter.lower() not in e["subject"].lower():
            continue

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
    def normalise(subject):
        return re.sub(r"^(re|fwd|fw):\s*", "", subject.strip().lower(), flags=re.IGNORECASE)

    threads = {}
    for e in emails:
        key = normalise(e["subject"])
        if key not in threads:
            threads[key] = []
        threads[key].append(e)

    for key in threads:
        threads[key].sort(key=lambda x: x["sort_key"])

    return threads


def find_most_recent_email(matched):
    """Return the single most recent email from matched list."""
    if not matched:
        return None
    return max(matched, key=lambda e: e.get("sort_key", datetime.min.replace(tzinfo=timezone.utc)))

# ── Claude API ────────────────────────────────────────────────────────────────

def call_claude(prompt, api_key, max_tokens=1500):
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model":      CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}],
    }
    try:
        response = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["content"][0]["text"].strip()
    except requests.exceptions.RequestException as e:
        print(f"\n  ❌ Claude API call failed: {e}")
        return None

# ── Prompts ───────────────────────────────────────────────────────────────────

def build_extraction_prompt(client_name, threads):
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

    return f"""You are an AI assistant for a Senior Key Account Manager at a B2B payments company.

Your job is to extract structured intelligence from email threads with a named client.
Be precise. Extract only what is explicitly stated. Do not infer or invent.

<client_name>{client_name}</client_name>

<email_threads>
{thread_blocks}
</email_threads>

Extract and return the following in this exact XML structure:

<intelligence>

<issue_summary>
Maximum 6 lines. Cover: what the core issue or situation is, where it currently stands,
the single biggest risk to the relationship or deal, and the most urgent next action needed.
Plain English. One point per line. No bullet symbols.
</issue_summary>

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


def build_reply_prompt(client, most_recent_email):
    return f"""You are a Senior Key Account Manager at a B2B payments company named Shikhar.

Draft a professional reply to the email below. Use the client context provided.

<client_context>
  <client_name>{client['client_name']}</client_name>
  <deal_stage>{client['deal_stage']}</deal_stage>
  <growth_target>{client['growth_target']}% growth target</growth_target>
  <pipeline_value>${int(client['pipeline_value']):,}</pipeline_value>
</client_context>

<email_to_reply_to>
  <date>{most_recent_email['date']}</date>
  <sender>{most_recent_email['sender']}</sender>
  <subject>{most_recent_email['subject']}</subject>
  <body>{most_recent_email['body']}</body>
</email_to_reply_to>

Write a reply that is:
- Professional and concise (3–5 short paragraphs max)
- Appropriate for the deal stage ({client['deal_stage']})
- Acknowledges any open items or questions in the email
- Advances the relationship toward the {client['growth_target']}% growth target where natural
- Senior KAM voice — direct, confident, not salesy

Sign off with exactly:

Best,
Shikhar
Senior Key Account Manager | Worldline

Return only the email body — no subject line, no metadata, no explanation."""

# ── Parse Claude output ───────────────────────────────────────────────────────

def parse_intelligence(raw_output):
    sections = [
        "issue_summary",
        "decisions_made",
        "open_actions",
        "pain_points",
        "relationship_risks",
        "upsell_signals",
        "relationship_temperature",
    ]
    result = {}
    for section in sections:
        pattern = rf"<{section}>(.*?)<\s*/{section}\s*>"
        match = re.search(pattern, raw_output, re.DOTALL | re.IGNORECASE)
        result[section] = match.group(1).strip() if match else "Could not parse."
    return result

# ── Terminal display ──────────────────────────────────────────────────────────

def print_client_header(client, days, keyword_filter):
    width = 65
    print("\n" + "=" * width)
    print(f"  🧠  CLIENT INTELLIGENCE — {client['client_name'].upper()}")
    print(f"  📊  Stage: {client['deal_stage']}  |  Pipeline: ${int(client['pipeline_value']):,}  |  Target: {client['growth_target']}%")
    if keyword_filter:
        print(f"  🔍  Subject filter: \"{keyword_filter}\"")
    print("=" * width)


def print_issue_summary(intel, email_count, days):
    width = 65
    print(f"\n  📬  {email_count} emails · last {days} days")
    print("\n  ISSUE SUMMARY")
    print("  " + "-" * (width - 2))
    for line in intel["issue_summary"].split("\n"):
        if line.strip():
            print(f"  {line.strip()}")
    print("  " + "-" * (width - 2))


def strip_quoted_reply(body):
    """Return only the top message — strip quoted chains and 'On <date>... wrote:' blocks."""
    lines = body.split("\n")
    cut = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(">"):
            cut = i
            break
        if re.match(r"^On .{10,}, .+ wrote:$", stripped):
            cut = i
            break
    return "\n".join(lines[:cut]).rstrip()


def print_most_recent_email(most_recent):
    width = 65
    print(f"\n  MOST RECENT EMAIL")
    print("  " + "-" * (width - 2))
    print(f"  From:    {most_recent['sender']}")
    print(f"  Subject: {most_recent['subject']}")
    print(f"  Date:    {most_recent['date']}")
    print("  " + "-" * (width - 2))
    print()
    for line in strip_quoted_reply(most_recent["body"]).split("\n"):
        print(f"  {line}")
    print()


def print_draft_reply(draft, most_recent):
    width = 65
    print("\n" + "=" * width)
    print("  ✉️   DRAFT REPLY")
    print(f"  Re: {most_recent['subject']}")
    print(f"  To: {most_recent['sender']}")
    print("  " + "-" * (width - 2))
    print()
    for line in draft.split("\n"):
        print(f"  {line}")
    print("\n" + "=" * width)

# ── Markdown export ───────────────────────────────────────────────────────────

def export_markdown(client, intel, draft, most_recent, thread_count, email_count, days, keyword_filter):
    today = datetime.today().strftime("%Y%m%d")
    safe_name = client['client_name'].replace(' ', '_')
    filename = BASE + f"client_intel_{safe_name}_{today}.md"

    labels = {
        "decisions_made":          "Decisions Made",
        "open_actions":            "Open Actions",
        "pain_points":             "Pain Points",
        "relationship_risks":      "Relationship Risks",
        "upsell_signals":          "Upsell Signals",
        "relationship_temperature":"Relationship Temperature",
    }

    lines = [
        f"# Client Intelligence — {client['client_name']}",
        f"**Generated:** {datetime.today().strftime('%A, %d %B %Y %H:%M')}",
        f"**Account ID:** {client['account_id']}  |  "
        f"**Stage:** {client['deal_stage']}  |  "
        f"**Pipeline:** ${int(client['pipeline_value']):,}  |  "
        f"**Growth Target:** {client['growth_target']}%",
        f"**Source:** {email_count} emails · {thread_count} threads · last {days} days",
    ]

    if keyword_filter:
        lines.append(f"**Subject filter:** \"{keyword_filter}\"")

    lines += ["", "---", ""]

    for key, label in labels.items():
        lines.append(f"## {label}")
        lines.append("")
        lines.append(intel[key])
        lines.append("")
        lines.append("---")
        lines.append("")

    if draft and most_recent:
        lines += [
            "## Draft Reply",
            "",
            f"**Re:** {most_recent['subject']}",
            f"**To:** {most_recent['sender']}",
            "",
            draft,
            "",
            "---",
            "",
        ]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  📄  Markdown saved: {filename}")
    return filename

# ── Draft refinement + reply gate ────────────────────────────────────────────

def build_refinement_prompt(current_draft, instruction):
    return f"""You are a Senior Key Account Manager at a B2B payments company named Shikhar.

Rewrite the email draft below based on the refinement instruction provided.
Keep the same professional, concise, senior KAM voice.
Sign off with exactly:

Best,
Shikhar
Senior Key Account Manager | Worldline

<refinement_instruction>{instruction}</refinement_instruction>

<current_draft>{current_draft}</current_draft>

Return only the revised email body — no subject line, no metadata, no explanation."""


def reply_gate(draft, most_recent, api_key, app_password):
    """Loop: show [y/n/r] gate. r → refine and loop. y/n → act and return."""
    while True:
        answer = input("\n  [y] Send  [n] Save to Drafts  [r] Refine: ").strip().lower()

        if answer == "y":
            send_reply(draft, most_recent, app_password)
            return draft

        if answer == "n":
            save_to_drafts(draft, most_recent, app_password)
            return draft

        if answer == "r":
            instruction = input("  How should I refine this? ").strip()
            if not instruction:
                print("  ⚠️  No instruction given — try again.")
                continue
            print(f"  🤖  Refining via Claude ({CLAUDE_MODEL})...")
            refined = call_claude(build_refinement_prompt(draft, instruction), api_key, max_tokens=800)
            if refined:
                draft = refined
                print("  ✅ Refined draft ready")
                print_draft_reply(draft, most_recent)
            else:
                print("  ❌ Refinement failed — keeping current draft.")
        else:
            print("  ⚠️  Enter y, n, or r.")


# ── SMTP sender + IMAP Drafts ─────────────────────────────────────────────────

def _build_reply_msg(draft, most_recent):
    """Build MIMEMultipart reply addressed to the sender of most_recent."""
    _, to_addr = parseaddr(most_recent["sender"])
    subject = most_recent["subject"]
    if not re.match(r"^re:", subject.strip(), re.IGNORECASE):
        subject = "Re: " + subject

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_addr
    msg["Subject"] = subject
    mid = most_recent.get("message_id", "")
    if mid:
        msg["In-Reply-To"] = mid
        msg["References"]  = mid
    msg.attach(MIMEText(draft, "plain"))
    return msg, to_addr


def send_reply(draft, most_recent, app_password):
    """Send draft via Gmail SMTP SSL to the exact sender of most_recent."""
    msg, to_addr = _build_reply_msg(draft, most_recent)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, app_password)
            server.sendmail(GMAIL_ADDRESS, to_addr, msg.as_string())
        print(f"\n  ✅ Reply sent to {to_addr}")
    except Exception as e:
        print(f"\n  ❌ Send failed: {e}")


def save_to_drafts(draft, most_recent, app_password):
    """Append draft to [Gmail]/Drafts via IMAP so it appears ready to send."""
    msg, to_addr = _build_reply_msg(draft, most_recent)
    raw = msg.as_bytes()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GMAIL_ADDRESS, app_password)
        mail.append('"[Gmail]/Drafts"', "\\Draft", imaplib.Time2Internaldate(datetime.now(timezone.utc)), raw)
        mail.logout()
        print(f"\n  📝  Draft saved to Gmail Drafts (To: {to_addr})")
    except Exception as e:
        print(f"\n  ❌ Could not save to Drafts: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    width = 65
    print("\n" + "=" * width)
    print("  🧠  CLIENT INTELLIGENCE ENGINE")
    print("=" * width)

    # 1. Load and pick client
    clients = load_clients()
    print(f"\n  {len(clients)} clients loaded from clients.csv")
    client = prompt_client(clients)
    print(f"\n  ✅ Selected: {client['client_name']} ({client['deal_stage']})")

    # 2. Lookback + keyword filter
    days           = prompt_lookback()
    keyword_filter = prompt_keyword_filter()

    print_client_header(client, days, keyword_filter)

    # 3. Load credentials
    app_password = get_env("GMAIL_APP_PASSWORD")
    api_key      = get_env("ANTHROPIC_API_KEY")

    # 4. Connect and fetch
    print("\n  Connecting to Gmail...")
    mail = connect_gmail(app_password)

    print("  Fetching recent emails...")
    all_emails = fetch_recent_emails(mail, days=days)
    print(f"  ✅ {len(all_emails)} emails fetched")
    mail.logout()

    # 5. Three-signal matching + keyword filter
    print(f"\n  Running three-signal match for '{client['client_name']}'...")
    matched = match_emails(all_emails, client["client_name"], keyword_filter)

    if not matched:
        msg = f"\n  ⚠️  No emails matched for '{client['client_name']}' in the last {days} days."
        if keyword_filter:
            msg += f"\n  (subject filter: \"{keyword_filter}\")"
        print(msg)
        print("  Signals checked: sender email · email signature · subject line\n")
        sys.exit(0)

    print(f"  ✅ {len(matched)} emails matched")
    s1 = sum(1 for e in matched if e["signals"]["sender_match"])
    s2 = sum(1 for e in matched if e["signals"]["signature_match"])
    s3 = sum(1 for e in matched if e["signals"]["subject_match"])
    print(f"     Signal 1 (sender):     {s1} emails")
    print(f"     Signal 2 (signature):  {s2} emails")
    print(f"     Signal 3 (subject):    {s3} emails")

    # 6. Group into threads
    threads = group_into_threads(matched)
    print(f"\n  📂  {len(threads)} thread(s) identified:")
    for subject in threads:
        print(f"     • {subject}  ({len(threads[subject])} emails)")

    # 7. Intelligence extraction
    print(f"\n  🤖  Extracting intelligence via Claude ({CLAUDE_MODEL})...")
    intel_prompt = build_extraction_prompt(client["client_name"], threads)
    raw_intel    = call_claude(intel_prompt, api_key, max_tokens=1500)

    if not raw_intel:
        print("  ❌ No response from Claude. Check API key and connectivity.")
        sys.exit(1)

    print("  ✅ Intelligence extracted")
    intel = parse_intelligence(raw_intel)
    print_issue_summary(intel, len(matched), days)

    # 8. Draft reply to most recent email
    most_recent = find_most_recent_email(matched)
    draft = None

    if most_recent:
        print_most_recent_email(most_recent)
        print(f"  🤖  Drafting reply via Claude ({CLAUDE_MODEL})...")
        reply_prompt = build_reply_prompt(client, most_recent)
        draft = call_claude(reply_prompt, api_key, max_tokens=800)
        if draft:
            print("  ✅ Draft ready")
            print_draft_reply(draft, most_recent)
            draft = reply_gate(draft, most_recent, api_key, app_password)
        else:
            print("  ⚠️  Draft generation failed — skipping.")

    # 9. Save markdown
    md_file = export_markdown(
        client, intel, draft, most_recent,
        len(threads), len(matched), days, keyword_filter
    )

    print(f"\n  ✅ Done. Review: {md_file}")
    print("=" * width + "\n")


if __name__ == "__main__":
    main()
