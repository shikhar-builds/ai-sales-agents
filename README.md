# AI Sales Agents — Shikhar Srivastava

AI-powered sales toolkit for Senior KAMs. Built on Claude API. One command every morning. No manual steps.

> **Stack:** Python · Claude API (`claude-sonnet-4-6`) · Gmail IMAP · Obsidian · FPDF

**Status: B3 active — email intelligence engine complete**

---

## What this is

A suite of modular Python agents that automate client intelligence, meeting preparation, and competitive research for enterprise account management. Every agent calls Claude directly — no LangChain, no wrappers. XML tags in every prompt. Env vars for every credential.

---

## Modules

### `morning_briefing.py` — Flagship

One command runs the full morning pipeline:

```bash
python3 morning_briefing.py
```

1. Loads CRM data from three CSVs (clients, revenue, last contact)
2. Reads today's daily note and client notes from Obsidian vault
3. Identifies top clients, open pipeline, and overdue follow-ups
4. Calls Claude for an AI executive summary
5. Exports a styled PDF digest and emails it automatically
6. **Meeting prep** — if you have a client meeting, prompts for a name, then:
   - Fetches email intelligence from Gmail (IMAP, three-signal matching, flexible lookback)
   - Sends email context + CRM data to Claude together
   - Returns enriched talking points grounded in both sources
   - Exports a prep PDF and emails it

---

### `email_intel.py` — Email Intelligence Engine

On-demand email intelligence for any named client.

```bash
python3 email_intel.py
# prompts: Client name → lookback window → runs automatically
```

- Connects to Gmail via IMAP (no OAuth — App Password)
- Fetches emails from Inbox + Sent + All Mail across a chosen window: 7 / 14 / 30 / 90 days
- **Three-signal matching:** sender email address · email signature · subject line keywords
- Groups matched emails into threads, strips Re:/Fwd: noise
- Sends threads to Claude and extracts structured intelligence:
  - Decisions made
  - Open actions (with owner)
  - Pain points (with severity)
  - Relationship risks (LOW / MEDIUM / HIGH)
  - Upsell signals
  - Relationship temperature
- Output: full terminal display + `.md` file ready for PDF/PPT conversion

---

### `competitive_intel.py` — Competitor Analysis

Paste competitor data or a URL → structured 6-section intel report → PDF.

Sections: Company Snapshot · Positioning & Messaging · Strengths · Weaknesses & Gaps · Counter-Moves for Worldline KAMs · Watch List (next 90 days)

---

### `meeting_prep.py` — Standalone Meeting Prep

Type a client name → CRM-based prep sheet + Claude talking points → PDF.

*(Note: `morning_briefing.py` now runs an enriched version of this with email intel included. Use this module for standalone prep outside the morning flow.)*

---

### `digest_agent.py` — Daily Client Digest

Reads the three CSVs and outputs a client briefing to terminal. Lightweight — no Claude call, no PDF.

---

### Supporting modules

| Module | Purpose |
|---|---|
| `export_pdf.py` | Exports digest, prep, and intel reports to styled PDF via FPDF |
| `send_email.py` | Sends PDFs via Gmail SMTP |
| `obsidian_brain.py` | Query your Obsidian vault with natural language via Claude |

---

## Architecture principles

- **Direct Claude API calls** — no LangChain, no wrappers, plain HTTP via `requests`
- **XML tags in all prompts** — structured input and output for reliable parsing
- **One file, one job** — each module is independently runnable
- **Env vars for all credentials** — nothing hardcoded

---

## Setup

```bash
# Add to ~/.zshrc
export ANTHROPIC_API_KEY="your_key"
export GMAIL_APP_PASSWORD="your_app_password"

source ~/.zshrc

# Install dependencies
pip3 install fpdf2 requests

# Run
python3 morning_briefing.py
python3 email_intel.py
python3 competitive_intel.py
```

**Gmail:** enable IMAP in Gmail settings → generate an App Password at myaccount.google.com/apppasswords

**Obsidian:** set `VAULT_PATH` in `morning_briefing.py` to your vault directory

---

## Data sources

| File | Contents |
|---|---|
| `clients.csv` | Pipeline value, deal stage, growth targets |
| `revenue.csv` | Revenue figures and growth % |
| `last_contact.csv` | Last contact dates per client |

---

## Impact

- ~7 hours/month saved on manual client prep
- 100% of portfolio reviewed daily vs reactive ad-hoc checks
- Meeting prep time: 45 mins → 5 mins per client, now enriched with email context
- Email intelligence: 30 days of client email history analysed in under 60 seconds

---

## About

Built by **Shikhar Srivastava** — Senior Key Account Manager at Worldline, managing a £7.29M gross revenue portfolio across 20 key clients. Building AI agents to automate how enterprise revenue teams operate.

- LinkedIn: linkedin.com/in/shikhar-srivastava-b292841a

---

## Week 1 learning scripts

`hello.py` · `input_test.py` · `guess_number.py` · `top_clients.py` · `dicts.py`
