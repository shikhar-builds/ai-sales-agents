"""
top_clients.py
--------------
Reads a CSV file of client accounts and prints the top 3 by revenue.

Expected CSV columns (case-insensitive):
    client_name, account_id, revenue

Usage:
    python top_clients.py                        # uses the built-in sample CSV
    python top_clients.py /Users/shikhar/Documents/Projects/StartupProjects/Data/clients.csv   # uses your own file
"""

import csv
import sys
import os
import tempfile

# ── Sample data (used when no file path is provided) ─────────────────────────

SAMPLE_CSV = """\
client_name,account_id,revenue
Acme Corp,A001,142000
BlueSky Ltd,B002,98500
CloudNine,C003,310000
DeltaTech,D004,75200
Echo Systems,E005,215000
Falcon Group,F006,310000
GreenLeaf,G007,48900
HorizonAI,H008,189000
IronClad,I009,95000
Jasper Co,J010,402000
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_clients(filepath: str) -> list[dict]:
    """Read the CSV and return a list of row dicts with normalised keys."""
    clients = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, quoting=csv.QUOTE_ALL)

        # Normalise header names to lowercase and strip whitespace
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        required = {"client_name", "account_id", "revenue"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")

        for row in reader:
            try:
                clients.append({
                    "client_name": row["client_name"].strip(),
                    "account_id":  row["account_id"].strip(),
                    "revenue":     float(row["revenue"].replace(",", "").strip()),
                })
            except ValueError:
                print(f"  ⚠  Skipping row with invalid revenue: {dict(row)}")

    return clients


def top_n(clients: list[dict], n: int = 3) -> list[dict]:
    """Return the top N clients sorted by revenue (descending)."""
    return sorted(clients, key=lambda c: c["revenue"], reverse=True)[:n]


def print_results(top: list[dict]) -> None:
    """Pretty-print the ranked results."""
    print("\n" + "=" * 50)
    print(f"  🏆  TOP {len(top)} CLIENTS BY REVENUE")
    print("=" * 50)
    for rank, client in enumerate(top, start=1):
        revenue_fmt = f"£{client['revenue']:>12,.2f}"
        print(f"  #{rank}  {client['client_name']:<20} {revenue_fmt}  (ID: {client['account_id']})")
    print("=" * 50 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Determine which file to use
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"Error: file not found → {filepath}")
            sys.exit(1)
        print(f"\nReading: {filepath}")
    else:
        filepath = "/Users/shikhar/Documents/Projects/StartupProjects/Data/clients.csv"
        print(f"\nNo file provided — using default: {filepath}")

    # Load, rank, display
    clients = load_clients(filepath)
    print(f"  {len(clients)} client records loaded.")

    if len(clients) == 0:
        print("  No valid records found.")
        return

    top = top_n(clients, n=3)
    print_results(top)

    # Greet all clients
    def greet_clients(client_names: list[str]) -> None:
        for name in client_names:
            print(f"Hello, {name}! Thank you for being a valued client.")

    names = [c["client_name"] for c in clients]
    greet_clients(names)
    

if __name__ == "__main__":
    main()