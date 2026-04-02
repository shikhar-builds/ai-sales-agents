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

import csv
from datetime import datetime, date

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

def print_digest(clients):
    today = date.today().strftime("%A, %d %B %Y")

    print("\n" + "=" * 60)
    print(f"  📋  DAILY CLIENT DIGEST — {today}")
    print("=" * 60)

    # Section 1 — Top clients by revenue
    print("\n  📈  TOP 3 CLIENTS BY REVENUE")
    print("  " + "-" * 56)
    for i, c in enumerate(top_by_revenue(clients), 1):
        growth_flag = "🟢" if c["growth_pct"] >= c["growth_target"] else "🔴"
        print(f"  #{i} {c['name']:<22} £{c['revenue']:>15,.0f}  {growth_flag} {c['growth_pct']}% growth")

    # Section 2 — Open pipeline
    print("\n  🔄  OPEN PIPELINE OPPORTUNITIES")
    print("  " + "-" * 56)
    pipeline = open_pipeline(clients)
    for c in sorted(pipeline, key=lambda x: x["pipeline_value"], reverse=True):
        print(f"  {c['name']:<24} £{c['pipeline_value']:>10,.0f}  [{c['deal_stage']}]")

    # Section 3 — Follow ups
    print(f"\n  📞  FOLLOW UPS NEEDED (no contact in {FOLLOW_UP_DAYS}+ days)")
    print("  " + "-" * 56)
    overdue = needs_followup(clients)
    if overdue:
        for c in overdue:
            print(f"  {c['name']:<24} Last contact: {c['last_contact']}  ({c['days_since']} days ago)")
    else:
        print("  ✅  All clients contacted recently!")

    print("\n" + "=" * 60 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    clients  = load_csv(CLIENTS_FILE)
    revenues = load_csv(REVENUE_FILE)
    contacts = load_csv(LAST_CONTACT_FILE)

    print("Merging sources...")
    merged = merge_data(clients, revenues, contacts)

    print_digest(merged)


if __name__ == "__main__":
    main()