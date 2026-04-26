"""
meeting_prep.py
---------------
Meeting Prep Agent for Senior KAMs
Type a client name and get a full structured briefing.
"""

import csv
from datetime import datetime, date

# ── Config ────────────────────────────────────────────────────────────────────

BASE = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"

# ── Loader ────────────────────────────────────────────────────────────────────

def load_csv(filepath):
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        return [row for row in reader]

# ── Lookup ────────────────────────────────────────────────────────────────────

def find_client(name, clients, revenues, contacts):
    name_lower = name.strip().lower()

    client  = next((c for c in clients  if c["client_name"].strip().lower() == name_lower), None)
    revenue = next((r for r in revenues if r["client_name"].strip().lower() == name_lower), None)
    contact = next((c for c in contacts if c["client_name"].strip().lower() == name_lower), None)

    if not client:
        return None

    today = date.today()
    last_contact = contact.get("last_contact", "Unknown") if contact else "Unknown"
    try:
        days_since = (today - datetime.strptime(last_contact, "%Y-%m-%d").date()).days
    except ValueError:
        days_since = None

    return {
        "name":           client["client_name"].strip(),
        "account_id":     client.get("account_id", "N/A"),
        "pipeline_value": float(client.get("pipeline_value", 0)),
        "deal_stage":     client.get("deal_stage", "Unknown"),
        "growth_target":  float(client.get("growth_target", 0)),
        "revenue":        float(revenue.get("revenue", 0)) if revenue else 0,
        "growth_pct":     float(revenue.get("growth_pct", 0)) if revenue else 0,
        "last_contact":   last_contact,
        "days_since":     days_since,
    }

# ── Display ───────────────────────────────────────────────────────────────────

def print_prep(c):
    width = 60
    print("\n" + "=" * width)
    print(f"  📋  MEETING PREP — {c['name']}")
    print("=" * width)
    print(f"  💰  Revenue:        £{c['revenue']:,.0f}  ({c['growth_pct']:+.1f}% growth)")
    print(f"  🎯  Pipeline:       £{c['pipeline_value']:,.0f}  [{c['deal_stage']}]")
    if c["days_since"] is not None:
        print(f"  📞  Last Contact:   {c['last_contact']}  ({c['days_since']} days ago)")
    else:
        print(f"  📞  Last Contact:   {c['last_contact']}")
    print(f"  📈  Growth Target:  {c['growth_target']:.0f}%")
    print("=" * width)
    print()
    print("  🤖  PASTE THIS INTO CLAUDE.AI FOR TALKING POINTS:")
    print("  " + "-" * (width - 2))
    print(f"""
  You are a senior sales strategist. I have a meeting with {c['name']}.
  Here is their profile:
  - Revenue: £{c['revenue']:,.0f} ({c['growth_pct']:+.1f}% growth)
  - Pipeline: £{c['pipeline_value']:,.0f} in {c['deal_stage']} stage
  - Last contacted: {c['last_contact']} ({c['days_since']} days ago)
  - Growth target: {c['growth_target']:.0f}%

  Give me 3 sharp talking points for this meeting.
  Be direct. No fluff.
""")
    print("=" * width)

# ── Run ───────────────────────────────────────────────────────────────────────

clients  = load_csv(BASE + "clients.csv")
revenues = load_csv(BASE + "revenue.csv")
contacts = load_csv(BASE + "last_contact.csv")

print("\n🔍 Meeting Prep Agent")
print("─" * 30)
name = input("  Enter client name: ").strip()

client = find_client(name, clients, revenues, contacts)

if client:
    print_prep(client)
else:
    print(f"\n❌ Client '{name}' not found. Check spelling and try again.")
    print("  Available clients:")
    for c in clients:
        print(f"    • {c['client_name'].strip()}")

from export_pdf import export_prep_pdf

if client:
    print_prep(client)

    talking_points = [
        "Match their growth trajectory - show specifically how your solution sustains or accelerates their 16% rate. Don't sell features; sell 16%.",
        "Unblock £7M sitting in Proposal - 39 days of silence is a risk signal. Open the meeting by asking: 'What's standing between us and closing this?'",
        "Re-establish urgency - a month-plus gap at Proposal stage means a deal going cold. Reset the cadence, confirm stakeholder alignment, and lock a next step with a concrete date.",
    ]

    export_prep_pdf(client, talking_points)