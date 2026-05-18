"""
competitive_intel.py
--------------------
Competitive Intelligence Tool for Senior KAMs and Founders.
Input: competitor name + pasted text or URL
Output: structured Claude.ai prompt → consistent intel report → PDF
"""

import os
import sys
import requests
from datetime import datetime
from export_pdf import export_intel_pdf

BASE = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"

# ── URL Fetcher ───────────────────────────────────────────────────────────────

def fetch_url(url):
    """Fetch text content from a URL — works for static sites only."""
    print("\n  ⚠️  Note: JS-rendered sites (Adyen, Stripe, etc.) won't parse well.")
    print("  💡  For those, use option 1 (paste text) instead.\n")
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        if len(text) < 200:
            print("  ⚠️  Page returned very little text — try paste method instead.")
            return None
        return text[:8000]
    except Exception as e:
        print(f"\n  ❌ Could not fetch URL: {e}")
        return None

# ── Input Handler ─────────────────────────────────────────────────────────────

def get_competitor_data():
    """Get competitor name and raw data from user."""
    width = 60
    print("\n" + "=" * width)
    print("  🔍  COMPETITIVE INTELLIGENCE TOOL")
    print("=" * width)

    # Competitor name
    competitor = input("\n  Competitor name: ").strip()
    if not competitor:
        print("  ❌ No competitor entered. Exiting.")
        sys.exit(1)

    # Context
    print("\n  Context:")
    print("  1. Payments / KAM role (Worldline vs competitor)")
    print("  2. Startup (my startup vs competitor)")
    context_choice = input("\n  Choose context (1 or 2): ").strip()
    context = "payments" if context_choice == "1" else "startup"

    # Input method
    print("\n  How do you want to input competitor data?")
    print("  1. Paste text (from website, LinkedIn, news)")
    print("  2. Fetch from URL")
    choice = input("\n  Choose (1 or 2): ").strip()

    raw_data = ""

    if choice == "1":
        # Write to temp file for multi-line paste
        temp_file = BASE + "competitor_input.txt"
        with open(temp_file, "w") as f:
            f.write("")
        print(f"\n  📝 Open this file and paste competitor info:")
        print(f"     {temp_file}")
        print(f"     Save it, then come back and press Enter.")
        os.system(f"open '{temp_file}'")
        input("\n  Press Enter when saved... ")
        with open(temp_file, "r") as f:
            raw_data = f.read().strip()
        os.remove(temp_file)

    elif choice == "2":
        url = input("\n  Enter URL: ").strip()
        print("\n  Fetching...")
        raw_data = fetch_url(url)
        if raw_data:
            print(f"  ✅ Fetched {len(raw_data)} characters")

    if not raw_data:
        print("  ❌ No data provided. Exiting.")
        sys.exit(1)

    return competitor, context, raw_data

# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_prompt(competitor, context, raw_data):
    """Build a structured Claude.ai prompt for consistent intel output."""

    if context == "payments":
        context_block = """You are a senior competitive intelligence analyst specialising in B2B payments and e-commerce. 
I am a Senior Key Account Manager at Worldline, a global payment service provider. 
I need to understand how this competitor positions against Worldline so I can defend my accounts and spot opportunities."""
    else:
        context_block = """You are a senior competitive intelligence analyst specialising in B2B SaaS and tech startups.
I am a founder building an AI-native B2B SaaS product.
I need to understand this competitor's positioning, weaknesses, and gaps so I can differentiate my startup."""

    prompt = f"""
{context_block}

Competitor: {competitor}

Raw data about this competitor:
---
{raw_data}
---

Based on the above, produce a structured competitive intelligence report with exactly these sections:

1. COMPANY SNAPSHOT
   - What they do in one sentence
   - Target customer (size, sector, geography)
   - Business model (pricing, revenue model)
   - Key products or services

2. POSITIONING & MESSAGING
   - How they position themselves in the market
   - Their key value propositions
   - What they emphasise most (speed, price, tech, service)
   - Who they are trying to steal customers from

3. STRENGTHS
   - 3-4 genuine strengths backed by the data
   - What they do better than most competitors

4. WEAKNESSES & GAPS
   - 3-4 specific weaknesses or blind spots
   - Where they are vulnerable
   - What customer complaints or limitations exist

5. COUNTER-MOVES (for {"Worldline KAMs" if context == "payments" else "my startup"})
   - 3 specific talking points to use against this competitor in a sales conversation
   - What to lead with, what to avoid, what questions to ask the client

6. WATCH LIST
   - 2-3 things to monitor about this competitor over the next 90 days
   - Any signals that suggest they are moving into new territory

Be direct. Use bullet points. No fluff. Write as if briefing a senior executive before a competitive deal.
"""
    return prompt.strip()

# ── Display ───────────────────────────────────────────────────────────────────

def display_prompt(competitor, prompt):
    """Display the prompt and save to temp file for easy copy."""
    width = 60
    temp_file = BASE + f"intel_prompt_{competitor.replace(' ', '_')}.txt"

    print("\n" + "=" * width)
    print(f"  🤖  CLAUDE.AI PROMPT — {competitor.upper()}")
    print("=" * width)
    print("\n  Prompt saved to file — opening now.")
    print(f"  📋  Copy everything in the file and paste into Claude.ai\n")

    with open(temp_file, "w") as f:
        f.write(prompt)

    os.system(f"open '{temp_file}'")
    print(f"  File: {temp_file}")
    print("\n" + "=" * width)

    return temp_file

# ── Run ───────────────────────────────────────────────────────────────────────

competitor, context, raw_data = get_competitor_data()
prompt = build_prompt(competitor, context, raw_data)
prompt_file = display_prompt(competitor, prompt)

print(f"""
  Next steps:
  1. Copy the prompt from the file that just opened
  2. Paste it into Claude.ai
  3. Copy Claude's response
  4. Come back here and press Enter to generate the PDF report
""")

input("  Press Enter when you have Claude's output ready... ")

# Get Claude's output
output_file = BASE + f"intel_output_{competitor.replace(' ', '_')}.txt"
with open(output_file, "w") as f:
    f.write("")
print(f"\n  📝 Paste Claude's output into this file:")
print(f"     {output_file}")
os.system(f"open '{output_file}'")
input("\n  Press Enter when saved... ")

with open(output_file, "r") as f:
    intel_output = f.read().strip()

os.remove(output_file)

print(f"\n  ✅ Intel captured for {competitor}")
print(f"  📄 Generating PDF report...")

# Export to PDF
print(f"\n  DEBUG: intel_output length = {len(intel_output)} characters")
print(f"  DEBUG: first 300 chars:\n{intel_output[:300]}")
export_intel_pdf(competitor, context, intel_output)

# Commit reminder
print("\n  💾  Commit when done:")
print(f"     git add competitive_intel.py export_pdf.py")
print(f"     git commit -m 'feat: competitive intel PDF export'")
print("=" * 60)