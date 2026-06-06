"""
morning_briefing.py
-------------------
One command morning routine for Senior KAMs.
Runs the daily digest + optional meeting prep in sequence.
Claude API called directly — no manual copy-paste required.
"""

import os
import csv
import requests
from datetime import datetime, date

from export_pdf import export_digest_to_pdf, export_prep_pdf
from send_email import send_digest_email, send_prep_email

# ── Config ────────────────────────────────────────────────────────────────────

BASE           = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"
FOLLOW_UP_DAYS = 7
VAULT_PATH     = "/Users/shikhar/Documents/Projects/AI_Brain/AI Brain/"
CLAUDE_MODEL   = "claude-sonnet-4-6"
ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"

# ── Claude API ────────────────────────────────────────────────────────────────

def call_claude(prompt):
    """Direct HTTP call to Claude API. No wrappers. No LangChain."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ❌ Missing ANTHROPIC_API_KEY in environment.")
        print("     Add to ~/.zshrc: export ANTHROPIC_API_KEY='your_key'")
        print("     Then run: source ~/.zshrc")
        return None

    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model":      CLAUDE_MODEL,
        "max_tokens": 1000,
        "messages":   [{"role": "user", "content": prompt}],
    }
    try:
        print(f"  🤖  Calling Claude ({CLAUDE_MODEL})...")
        response = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        result = data["content"][0]["text"].strip()
        print("  ✅  Claude response received")
        return result
    except requests.exceptions.RequestException as e:
        print(f"  ❌  Claude API call failed: {e}")
        return None

# ── Obsidian ──────────────────────────────────────────────────────────────────

def read_obsidian_context():
    """Read today's daily note and client notes from Obsidian vault."""
    context = {"daily_note": None, "client_notes": []}

    today      = date.today().strftime("%Y-%m-%d")
    daily_path = os.path.join(VAULT_PATH, "Daily Notes", f"{today}.md")
    if os.path.exists(daily_path):
        with open(daily_path, "r", encoding="utf-8") as f:
            context["daily_note"] = f.read().strip()
        print("  ✅  Obsidian daily note loaded")
    else:
        print("  ⚠️   No Obsidian daily note found for today")

    clients_path = os.path.join(VAULT_PATH, "Clients")
    if os.path.exists(clients_path):
        for filename in os.listdir(clients_path):
            if filename.endswith(".md"):
                filepath = os.path.join(clients_path, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    context["client_notes"].append({
                        "title":   filename.replace(".md", ""),
                        "content": content[:1500],
                    })
        print(f"  ✅  {len(context['client_notes'])} Obsidian client notes loaded")

    return context

# ── Loaders ───────────────────────────────────────────────────────────────────

def load_csv(filepath):
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        return [row for row in reader]

# ── Merge ─────────────────────────────────────────────────────────────────────

def merge_data(clients, revenues, contacts):
    revenue_map = {r["client_name"].strip(): r for r in revenues}
    contact_map = {c["client_name"].strip(): c for c in contacts}
    merged = []
    for client in clients:
        name = client["client_name"].strip()
        rev  = revenue_map.get(name, {})
        con  = contact_map.get(name, {})
        merged.append({
            "name":           name,
            "account_id":     client.get("account_id", "N/A"),
            "pipeline_value": float(client.get("pipeline_value", 0)),
            "deal_stage":     client.get("deal_stage", "Unknown"),
            "growth_target":  float(client.get("growth_target", 0)),
            "revenue":        float(rev.get("revenue", 0)),
            "growth_pct":     float(rev.get("growth_pct", 0)),
            "last_contact":   con.get("last_contact", "Unknown"),
        })
    return merged

# ── Analysis ──────────────────────────────────────────────────────────────────

def top_by_revenue(clients, n=3):
    return sorted(clients, key=lambda c: c["revenue"], reverse=True)[:n]

def open_pipeline(clients):
    return [c for c in clients if c["deal_stage"] != "Closed Won"]

def needs_followup(clients, days=FOLLOW_UP_DAYS):
    today   = date.today()
    overdue = []
    for c in clients:
        try:
            last = datetime.strptime(c["last_contact"], "%Y-%m-%d").date()
            if (today - last).days >= days:
                overdue.append({**c, "days_since": (today - last).days})
        except ValueError:
            pass
    return sorted(overdue, key=lambda c: c["days_since"], reverse=True)

# ── Display ───────────────────────────────────────────────────────────────────

def print_digest(top, pipeline, followups, today_str):
    width = 60
    print("\n" + "=" * width)
    print(f"  📋  DAILY CLIENT DIGEST — {today_str}")
    print("=" * width)
    print("  📈  TOP 3 CLIENTS BY REVENUE")
    print("  " + "-" * (width - 2))
    for i, c in enumerate(top, 1):
        icon = "🔴" if c["growth_pct"] < 0 else "🟢"
        print(f"  #{i} {c['name']:<22} £ {c['revenue']:>15,.0f}  {icon} {c['growth_pct']:.1f}% growth")
    print("\n  🔄  OPEN PIPELINE OPPORTUNITIES")
    print("  " + "-" * (width - 2))
    for c in pipeline:
        print(f"  {c['name']:<24} £ {c['pipeline_value']:>9,.0f}  [{c['deal_stage']}]")
    print("\n  📞  FOLLOW UPS NEEDED (no contact in 7+ days)")
    print("  " + "-" * (width - 2))
    for c in followups:
        print(f"  {c['name']:<24} Last contact: {c['last_contact']}  ({c['days_since']} days ago)")
    print("=" * width)

# ── Prompt builder ────────────────────────────────────────────────────────────

def build_briefing_prompt(top, pipeline, followups, today_str, obsidian):
    """Build enriched Claude prompt with XML tags. Non-negotiable."""

    client_context = ""
    for note in obsidian["client_notes"]:
        client_context += f"\n<client name='{note['title']}'>\n{note['content']}\n</client>\n"

    daily_context = obsidian["daily_note"] or "No daily note available."

    top_lines      = "\n".join([f"- {c['name']}: £{c['revenue']:,.0f} ({c['growth_pct']:+.1f}% growth)" for c in top])
    pipeline_lines = "\n".join([f"- {c['name']}: £{c['pipeline_value']:,.0f} [{c['deal_stage']}]" for c in pipeline])
    followup_lines = "\n".join([f"- {c['name']}: {c['days_since']} days since last contact" for c in followups])

    prompt = f"""You are a senior sales strategist briefing a Key Account Manager at a B2B payments company.

<context>
  <date>{today_str}</date>
  <role>Senior Key Account Manager — £7.29M portfolio, 20 clients</role>
</context>

<crm_data>
  <top_clients_by_revenue>
{top_lines}
  </top_clients_by_revenue>

  <open_pipeline>
{pipeline_lines}
  </open_pipeline>

  <followups_needed>
{followup_lines}
  </followups_needed>
</crm_data>

<obsidian_client_notes>
{client_context}
</obsidian_client_notes>

<daily_note>
{daily_context}
</daily_note>

<task>
Write a sharp morning briefing with exactly this structure:

<summary>
Three sentences maximum. Identify the single most urgent action today. Highlight the biggest pipeline opportunity. Flag the relationship most at risk.
</summary>

<actions>
3 bullet point actions for today. Specific, named, time-bound where possible. Use both CRM data and personal notes.
</actions>

Be direct. No fluff. Write as if speaking in a Monday morning standup.
</task>"""

    return prompt.strip()

# ── Parse Claude output ───────────────────────────────────────────────────────

def parse_briefing(raw_output):
    """Extract summary and actions from Claude's XML response."""
    import re

    summary_match = re.search(r"<summary>(.*?)</summary>", raw_output, re.DOTALL)
    actions_match = re.search(r"<actions>(.*?)</actions>",  raw_output, re.DOTALL)

    summary = summary_match.group(1).strip() if summary_match else raw_output.strip()
    actions = actions_match.group(1).strip() if actions_match else ""

    # Combine for PDF/email — plain text
    if actions:
        full = f"{summary}\n\nToday's Actions:\n{actions}"
    else:
        full = summary

    return full

# ── Meeting Prep ──────────────────────────────────────────────────────────────

def find_client(name, merged):
    name_lower = name.strip().lower()
    today      = date.today()
    for c in merged:
        if c["name"].lower() == name_lower:
            try:
                days_since = (today - datetime.strptime(c["last_contact"], "%Y-%m-%d").date()).days
            except ValueError:
                days_since = None
            return {**c, "days_since": days_since}
    return None

def build_talking_points_prompt(c):
    """Build talking points prompt with XML tags."""
    prompt = f"""You are a senior sales strategist. I have a meeting with {c['name']}.

<client_profile>
  <name>{c['name']}</name>
  <revenue>£{c['revenue']:,.0f}</revenue>
  <growth>{c['growth_pct']:+.1f}%</growth>
  <pipeline>£{c['pipeline_value']:,.0f} in {c['deal_stage']} stage</pipeline>
  <last_contact>{c['last_contact']} ({c['days_since']} days ago)</last_contact>
  <growth_target>{c['growth_target']:.0f}%</growth_target>
</client_profile>

<task>
Give me exactly 3 sharp talking points for this meeting.

<talking_points>
Format each as a numbered point. Be specific to their data. No generic advice.
</talking_points>

Be direct. No fluff.
</task>"""
    return prompt.strip()

def print_prep(c, talking_points_text=""):
    width = 60
    print("\n" + "=" * width)
    print(f"  📋  MEETING PREP — {c['name']}")
    print("=" * width)
    print(f"  💰  Revenue:        £{c['revenue']:,.0f}  ({c['growth_pct']:+.1f}% growth)")
    print(f"  🎯  Pipeline:       £{c['pipeline_value']:,.0f}  [{c['deal_stage']}]")
    print(f"  📞  Last Contact:   {c['last_contact']}  ({c['days_since']} days ago)")
    print(f"  📈  Growth Target:  {c['growth_target']:.0f}%")
    if talking_points_text:
        print("\n  🤖  TALKING POINTS (Claude)")
        print("  " + "-" * (width - 2))
        for line in talking_points_text.split("\n"):
            print(f"  {line}")
    print("=" * width)

# ── Run ───────────────────────────────────────────────────────────────────────

print("\n🌅  MORNING BRIEFING")
print("=" * 60)

# 0. Load Obsidian context
print("\n  Loading Obsidian context...")
obsidian = read_obsidian_context()

# 1. Load and merge CRM data
print("\n  Loading CRM data...")
clients  = load_csv(BASE + "clients.csv")
revenues = load_csv(BASE + "revenue.csv")
contacts = load_csv(BASE + "last_contact.csv")
print("  Merging sources...")
merged = merge_data(clients, revenues, contacts)

today_str = datetime.today().strftime("%A, %d %B %Y")
top       = top_by_revenue(merged)
pipeline  = open_pipeline(merged)
followups = needs_followup(merged)

# 2. Print digest to terminal
print_digest(top, pipeline, followups, today_str)

# 3. Build PDF data
top_pdf       = [{"name": c["name"], "revenue": c["revenue"], "growth": c["growth_pct"]} for c in top]
pipeline_pdf  = [{"client": c["name"], "value": c["pipeline_value"], "stage": c["deal_stage"]} for c in pipeline]
followups_pdf = [{"client": c["name"], "last_contact": c["last_contact"], "days_ago": c["days_since"]} for c in followups]

# 4. Call Claude API directly — no copy-paste
print("\n  🧠  Building enriched briefing from CRM + Obsidian...")
prompt   = build_briefing_prompt(top, pipeline, followups, today_str, obsidian)
raw      = call_claude(prompt)

if raw:
    summary = parse_briefing(raw)
    print("\n  📋  AI MORNING SUMMARY")
    print("  " + "-" * 58)
    for line in summary.split("\n"):
        print(f"  {line}")
    print("  " + "-" * 58)
else:
    summary = "No AI summary available today."
    print(f"\n  ⚠️   {summary}")

# 5. Export digest PDF and send email
pdf_file = export_digest_to_pdf(top_pdf, pipeline_pdf, followups_pdf, summary=summary)
send_digest_email(pdf_file, summary=summary)

# 6. Meeting prep — optional
print("\n📅  Do you have a client meeting today?")
answer = input("   Enter client name (or press Enter to skip): ").strip()

if answer:
    client = find_client(answer, merged)
    if client:
        print(f"\n  🤖  Generating talking points for {client['name']}...")
        tp_prompt       = build_talking_points_prompt(client)
        tp_raw          = call_claude(tp_prompt)
        talking_points  = tp_raw if tp_raw else "Could not generate talking points."

        print_prep(client, talking_points)

        # Parse into list for PDF
        import re
        points = [p.strip() for p in re.split(r"\n\d+\.", talking_points) if p.strip()]
        if not points:
            points = [talking_points]

        prep_pdf = export_prep_pdf(client, points)
        send_prep_email(prep_pdf, client["name"], summary=talking_points)
    else:
        print(f"\n  ❌  '{answer}' not found. Available clients:")
        for c in merged:
            print(f"     • {c['name']}")
else:
    print("\n  No meeting prep needed. Have a great day! 🚀")

print("\n✅  Morning briefing complete.\n")
