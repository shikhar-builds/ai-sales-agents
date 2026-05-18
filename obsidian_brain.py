"""
obsidian_brain.py
-----------------
Reads your Obsidian vault and generates a Claude.ai prompt
that queries your own notes — clients, startup, daily brain.
"""

import os
from datetime import datetime, date

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH = "/Users/shikhar/Documents/Projects/AI_Brain/AI Brain/"
BASE       = "/Users/shikhar/Documents/Projects/StartupProjects/Code/Python/"

# ── Vault Reader ──────────────────────────────────────────────────────────────

def read_folder(folder_name, max_files=5):
    """Read all markdown files in a vault folder."""
    folder_path = os.path.join(VAULT_PATH, folder_name)
    notes = []

    if not os.path.exists(folder_path):
        print(f"  ⚠️  Folder not found: {folder_path}")
        return notes

    files = sorted([
        f for f in os.listdir(folder_path)
        if f.endswith(".md")
    ], reverse=True)[:max_files]

    for filename in files:
        filepath = os.path.join(folder_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            notes.append({
                "title": filename.replace(".md", ""),
                "content": content[:2000]  # limit per note
            })

    return notes

def read_todays_note():
    """Read today's daily note if it exists."""
    today = date.today().strftime("%Y-%m-%d")
    filepath = os.path.join(VAULT_PATH, "Daily Notes", f"{today}.md")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_brain_prompt(query, client_notes, startup_notes, daily_note):
    """Build a Claude.ai prompt from vault contents."""

    # Format client notes
    clients_block = ""
    for note in client_notes:
        clients_block += f"\n### {note['title']}\n{note['content']}\n"

    # Format startup notes
    startup_block = ""
    for note in startup_notes:
        startup_block += f"\n### {note['title']}\n{note['content']}\n"

    # Format daily note
    daily_block = daily_note if daily_note else "No daily note found for today."

    prompt = f"""You are Shikhar's personal AI chief of staff. You have access to his private knowledge base containing client notes, startup research, and daily priorities.

Today's date: {datetime.today().strftime("%A, %d %B %Y")}

--- CLIENT NOTES ---
{clients_block}

--- STARTUP NOTES ---
{startup_block if startup_block else "No startup notes yet."}

--- TODAY'S DAILY NOTE ---
{daily_block}

--- QUERY ---
{query}

Answer directly and specifically using only the information in the notes above. If the answer isn't in the notes, say so clearly. Be concise and actionable.
"""
    return prompt.strip()

# ── Display ───────────────────────────────────────────────────────────────────

def display_prompt(query, prompt):
    """Save prompt to file and open it."""
    safe_query = query[:30].replace(" ", "_").replace("?", "")
    temp_file = BASE + f"brain_prompt_{safe_query}.txt"

    with open(temp_file, "w") as f:
        f.write(prompt)

    os.system(f"open '{temp_file}'")
    print(f"\n  ✅ Prompt saved and opened: {temp_file}")
    print(f"  📋 Copy everything and paste into Claude.ai\n")
    return temp_file

# ── Run ───────────────────────────────────────────────────────────────────────

width = 60
print("\n" + "=" * width)
print("  🧠  OBSIDIAN AI BRAIN")
print("=" * width)

# Read vault
print("\n  Reading your vault...")
client_notes  = read_folder("Clients", max_files=10)
startup_notes = read_folder("Startup", max_files=5)
daily_note    = read_todays_note()

print(f"  ✅ {len(client_notes)} client notes loaded")
print(f"  ✅ {len(startup_notes)} startup notes loaded")
print(f"  ✅ Daily note: {'found' if daily_note else 'not found'}")

# Query
print("\n  What do you want to know from your brain?")
print("  Examples:")
print("    - Which clients am I most at risk of losing?")
print("    - What did I commit to Standard Chartered?")
print("    - What are my priorities today?")
print("    - Who are my most important contacts this week?")

query = input("\n  Your question: ").strip()

if not query:
    print("  ❌ No query entered. Exiting.")
    exit()

# Build and display prompt
print("\n  Building prompt from your vault...")
prompt = build_brain_prompt(query, client_notes, startup_notes, daily_note)
display_prompt(query, prompt)

print("  Paste the prompt into Claude.ai, get the answer, come back.\n")
print("=" * width)