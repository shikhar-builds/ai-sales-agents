import csv
import pandas as pd
from datetime import datetime, date
from export_pdf import export_digest_to_pdf

"""
digest_agent.py
---------------
Daily Client Digest Agent for Senior KAMs
Reads from 3 sources and outputs a prioritised daily briefing.

Sources:
    - clients.csv     → pipeline, deal stage, growth targets
    - revenue.csv     → revenue and growth %
    - last_contact.csv → last contact date
"""

# ── Config ────────────────────────────────────────────────────────────────────

CLIENTS_FILE      = "clients.csv"
REVENUE_FILE      = "revenue.csv"
LAST_CONTACT_FILE = "last_contact.csv"
FOLLOW_UP_DAYS    = 7  # flag clients not contacted in this many days

# ── Loaders ───────────────────────────────────────────────────────────────────

def load_csv(filepath):
    """Generic CSV loader — returns list of dicts with normalised keys."""
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        return [row for row in reader]


# ── Merge ─────────────────────────────────────────────────────────────────────

def merge_data(clients, revenues, contacts):
    """Merge all three sources by client_name."""
    # Build lookup dicts for fast access
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
    """Return top N clients by revenue."""
    return sorted(clients, key=lambda c: c["revenue"], reverse=True)[:n]


def open_pipeline(clients):
    """Return clients with active pipeline (excluding Closed Won)."""
    return [c for c in clients if c["deal_stage"] != "Closed Won"]


def needs_followup(clients, days=FOLLOW_UP_DAYS):
    """Return clients not contacted in the last N days."""
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
        growth_icon = "🔴" if c["growth_pct"] < 0 else "🟢"
        print(f"  #{i} {c['name']:<22} £ {c['revenue']:>15,.0f}  {growth_icon} {c['growth_pct']:.1f}% growth")

    print("\n  🔄  OPEN PIPELINE OPPORTUNITIES")
    print("  " + "-" * (width - 2))
    for c in pipeline:
        print(f"  {c['name']:<24} £ {c['pipeline_value']:>9,.0f}  [{c['deal_stage']}]")

    print("\n  📞  FOLLOW UPS NEEDED (no contact in 7+ days)")
    print("  " + "-" * (width - 2))
    for c in followups:
        print(f"  {c['name']:<24} Last contact: {c['last_contact']}  ({c['days_since']} days ago)")

    print("=" * width)


# ── Run ───────────────────────────────────────────────────────────────────────

base = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"

print("Loading data...")
clients  = load_csv(base + "clients.csv")
revenues = load_csv(base + "revenue.csv")
contacts = load_csv(base + "last_contact.csv")

print("Merging sources...")
merged = merge_data(clients, revenues, contacts)

today_str = datetime.today().strftime("%A, %d %B %Y")
top       = top_by_revenue(merged)
pipeline  = open_pipeline(merged)
followups = needs_followup(merged)

# Print to terminal
print_digest(top, pipeline, followups, today_str)

# Build PDF-ready data
top_clients_pdf = [
    {"name": c["name"], "revenue": c["revenue"], "growth": c["growth_pct"]}
    for c in top
]
pipeline_pdf = [
    {"client": c["name"], "value": c["pipeline_value"], "stage": c["deal_stage"]}
    for c in pipeline
]
followups_pdf = [
    {"client": c["name"], "last_contact": c["last_contact"], "days_ago": c["days_since"]}
    for c in followups
]

# Export to PDF
summary = (
    "Call NatWest today - 42 days without contact with £1.5M in Proposal stage "
    "is a deal at serious risk of going cold. Your biggest pipeline opportunity is "
    "Standard Chartered at £7M in Proposal - get a review meeting in the diary this "
    "week. The relationship most at risk beyond NatWest is Barclays at 37 days silent, "
    "with only £2M in Prospecting stage."
)
export_digest_to_pdf(top_clients_pdf, pipeline_pdf, followups_pdf, summary=summary)  

from send_email import send_digest_email
send_digest_email(f"digest_{datetime.today().strftime('%Y%m%d')}.pdf", summary=summary)

# AI Executive Summary — paste Claude's output here each morning
summary = (
    "Call NatWest today — 42 days without contact with £1.5M in Proposal stage "
    "is a deal at serious risk of going cold. Your biggest pipeline opportunity is "
    "Standard Chartered at £7M in Proposal — get a review meeting in the diary this "
    "week. The relationship most at risk beyond NatWest is Barclays at 37 days silent, "
    "with only £2M in Prospecting stage."
)

export_digest_to_pdf(top_clients_pdf, pipeline_pdf, followups_pdf, summary=summary)
send_digest_email(f"digest_{datetime.today().strftime('%Y%m%d')}.pdf", summary=summary)