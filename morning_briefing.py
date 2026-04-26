"""
morning_briefing.py
-------------------
One command morning routine for Senior KAMs.
Runs the daily digest + optional meeting prep in sequence.
"""

import os
import csv
from datetime import datetime, date

from export_pdf import export_digest_to_pdf, export_prep_pdf
from send_email import send_digest_email, send_prep_email

# ── Config ────────────────────────────────────────────────────────────────────

BASE = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"
FOLLOW_UP_DAYS = 7

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
    today = date.today()
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

# ── Meeting Prep ──────────────────────────────────────────────────────────────

def find_client(name, merged):
    name_lower = name.strip().lower()
    today = date.today()
    for c in merged:
        if c["name"].lower() == name_lower:
            try:
                days_since = (today - datetime.strptime(c["last_contact"], "%Y-%m-%d").date()).days
            except ValueError:
                days_since = None
            return {**c, "days_since": days_since}
    return None

def print_prep(c):
    width = 60
    print("\n" + "=" * width)
    print(f"  📋  MEETING PREP — {c['name']}")
    print("=" * width)
    print(f"  💰  Revenue:        £{c['revenue']:,.0f}  ({c['growth_pct']:+.1f}% growth)")
    print(f"  🎯  Pipeline:       £{c['pipeline_value']:,.0f}  [{c['deal_stage']}]")
    print(f"  📞  Last Contact:   {c['last_contact']}  ({c['days_since']} days ago)")
    print(f"  📈  Growth Target:  {c['growth_target']:.0f}%")
    print("=" * width)
    print(f"""
  🤖  PASTE THIS INTO CLAUDE.AI FOR TALKING POINTS:
  {"-" * 56}
  You are a senior sales strategist. I have a meeting with {c['name']}.
  Here is their profile:
  - Revenue: £{c['revenue']:,.0f} ({c['growth_pct']:+.1f}% growth)
  - Pipeline: £{c['pipeline_value']:,.0f} in {c['deal_stage']} stage
  - Last contacted: {c['last_contact']} ({c['days_since']} days ago)
  - Growth target: {c['growth_target']:.0f}%

  Give me 3 sharp talking points for this meeting.
  Be direct. No fluff.
""")

# ── Run ───────────────────────────────────────────────────────────────────────

print("\n🌅  MORNING BRIEFING")
print("=" * 60)

# 1. Load and merge data
print("\nLoading data...")
clients  = load_csv(BASE + "clients.csv")
revenues = load_csv(BASE + "revenue.csv")
contacts = load_csv(BASE + "last_contact.csv")
print("Merging sources...")
merged = merge_data(clients, revenues, contacts)

today_str = datetime.today().strftime("%A, %d %B %Y")
top       = top_by_revenue(merged)
pipeline  = open_pipeline(merged)
followups = needs_followup(merged)

# 2. Print digest to terminal
print_digest(top, pipeline, followups, today_str)

# 3. Build PDF data
top_pdf      = [{"name": c["name"], "revenue": c["revenue"], "growth": c["growth_pct"]} for c in top]
pipeline_pdf = [{"client": c["name"], "value": c["pipeline_value"], "stage": c["deal_stage"]} for c in pipeline]
followups_pdf= [{"client": c["name"], "last_contact": c["last_contact"], "days_ago": c["days_since"]} for c in followups]

# 4. AI summary — paste today's Claude output here each morning
summary = (
    "Call NatWest today - 42 days without contact with £1.5M in Proposal stage "
    "is a deal at serious risk of going cold. Your biggest pipeline opportunity is "
    "Standard Chartered at £7M in Proposal - get a review meeting in the diary this "
    "week. The relationship most at risk beyond NatWest is Barclays at 37 days silent, "
    "with only £2M in Prospecting stage."
)

# 5. Export digest PDF and send email
pdf_file = export_digest_to_pdf(top_pdf, pipeline_pdf, followups_pdf, summary=summary)
send_digest_email(pdf_file, summary=summary)

# 6. Meeting prep — optional
print("\n📅  Do you have a client meeting today?")
answer = input("   Enter client name (or press Enter to skip): ").strip()

if answer:
    client = find_client(answer, merged)
    if client:
        print_prep(client)
        print("\n  Paste the prompt above into Claude.ai, then come back.")
        # Write talking points to a temp file, user pastes there
        temp_file = BASE + "talking_points.txt"
        print(f"\n  📝  Open this file and paste Claude's talking points into it:")
        print(f"      {temp_file}")
        print(f"      Save the file, then come back here and press Enter.")
        
        # Create empty file for user to paste into
        with open(temp_file, "w") as f:
            f.write("")
        
        os.system(f"open '{temp_file}'")  # opens in default text editor on Mac
        input("\n  Press Enter when you've saved the talking points... ")
        
        with open(temp_file, "r") as f:
            content = f.read().strip()
        
    if content:
            points = [p.strip() for p in content.split("\n") if p.strip()]
            prep_pdf = export_prep_pdf(client, points)
            os.remove(temp_file)
            send_prep_email(prep_pdf, client["name"], summary=content)    
    else:
        print(f"\n  ❌ '{answer}' not found. Available clients:")
        for c in merged:
            print(f"     • {c['name']}")
else:
    print("\n  No meeting prep needed. Have a great day! 🚀")

print("\n✅  Morning briefing complete.\n")