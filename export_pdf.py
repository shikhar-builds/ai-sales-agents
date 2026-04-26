from fpdf import FPDF
from datetime import datetime

FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD    = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ITALIC  = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"


def export_digest_to_pdf(top_clients, pipeline, followups, date_str=None, summary=""):
    if date_str is None:
        date_str = datetime.today().strftime("%A, %d %B %Y")

    file_date = datetime.today().strftime("%Y%m%d")
    filename = f"digest_{file_date}.pdf"

    pdf = FPDF()
    pdf.add_font("Arial", "",  FONT_REGULAR, uni=True)
    pdf.add_font("Arial", "B", FONT_BOLD,    uni=True)
    pdf.add_font("Arial", "I", FONT_ITALIC,  uni=True)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── HEADER ──────────────────────────────────────────
    pdf.set_fill_color(30, 158, 117)
    pdf.rect(0, 0, 210, 28, style="F")
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(8)
    pdf.cell(0, 12, "Daily Client Digest", align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, date_str, align="C")
    pdf.ln(16)

    # ── EXECUTIVE SUMMARY ────────────────────────────────
    if summary:
        pdf.set_fill_color(225, 245, 238)
        pdf.set_draw_color(30, 158, 117)
        pdf.set_line_width(0.4)
        pdf.rect(20, pdf.get_y(), 170, 24, style="FD")
        pdf.set_xy(24, pdf.get_y() + 3)
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(15, 110, 86)
        pdf.cell(0, 5, "AI EXECUTIVE SUMMARY", ln=True)
        pdf.set_x(24)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(162, 5, summary)
        pdf.ln(4)

    # ── SECTION HELPER ───────────────────────────────────
    def section_title(title):
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(30, 158, 117)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_draw_color(30, 158, 117)
        pdf.set_line_width(0.4)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(3)
        pdf.set_text_color(40, 40, 40)

    # ── TOP CLIENTS ──────────────────────────────────────
    section_title("Top 3 Clients by Revenue")
    for i, client in enumerate(top_clients, 1):
        pdf.set_font("Arial", "B", 10)
        pdf.cell(8, 7, f"#{i}", ln=False)
        pdf.set_font("Arial", "", 10)
        pdf.cell(60, 7, client["name"], ln=False)
        pdf.cell(50, 7, f"£{client['revenue']:,.0f}", ln=False)
        growth_color = (200, 50, 50) if client["growth"] < 0 else (30, 130, 80)
        pdf.set_text_color(*growth_color)
        pdf.cell(0, 7, f"{client['growth']:+.1f}%", ln=True)
        pdf.set_text_color(40, 40, 40)
    pdf.ln(4)

    # ── PIPELINE ─────────────────────────────────────────
    section_title("Open Pipeline Opportunities")
    for opp in pipeline:
        pdf.set_font("Arial", "", 10)
        pdf.cell(70, 7, opp["client"], ln=False)
        pdf.cell(50, 7, f"£{opp['value']:,.0f}", ln=False)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, f"[{opp['stage']}]", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.set_text_color(40, 40, 40)
    pdf.ln(4)

    # ── FOLLOW-UPS ───────────────────────────────────────
    section_title("Follow-Ups Needed (7+ days since contact)")
    for fu in followups:
        pdf.set_font("Arial", "", 10)
        pdf.cell(70, 7, fu["client"], ln=False)
        pdf.cell(55, 7, f"Last contact: {fu['last_contact']}", ln=False)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(180, 60, 60)
        pdf.cell(0, 7, f"({fu['days_ago']} days ago)", ln=True)
        pdf.set_text_color(40, 40, 40)
    pdf.ln(6)

    # ── FOOTER ────────────────────────────────────────────
    pdf.set_y(-20)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, f"Generated {datetime.today().strftime('%d %b %Y %H:%M')}  |  Confidential", align="C")

    pdf.output(filename)
    print(f"\n✅ PDF exported: {filename}")
    return filename


def export_prep_pdf(client, talking_points, date_str=None):
    if date_str is None:
        date_str = datetime.today().strftime("%A, %d %B %Y")

    filename = f"prep_{client['name'].replace(' ', '_')}_{datetime.today().strftime('%Y%m%d')}.pdf"

    pdf = FPDF()
    pdf.add_font("Arial", "",  FONT_REGULAR, uni=True)
    pdf.add_font("Arial", "B", FONT_BOLD,    uni=True)
    pdf.add_font("Arial", "I", FONT_ITALIC,  uni=True)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── HEADER ──────────────────────────────────────────
    pdf.set_fill_color(30, 158, 117)
    pdf.rect(0, 0, 210, 28, style="F")
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(8)
    pdf.cell(0, 12, f"Meeting Prep - {client['name']}", align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, date_str, align="C")
    pdf.ln(16)

    # ── CLIENT SNAPSHOT ──────────────────────────────────
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(30, 158, 117)
    pdf.cell(0, 8, "Client Snapshot", ln=True)
    pdf.set_draw_color(30, 158, 117)
    pdf.set_line_width(0.4)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)
    pdf.set_text_color(40, 40, 40)

    rows = [
        ("Revenue",       f"£{client['revenue']:,.0f}  ({client['growth_pct']:+.1f}% growth)"),
        ("Pipeline",      f"£{client['pipeline_value']:,.0f}  [{client['deal_stage']}]"),
        ("Last Contact",  f"{client['last_contact']}  ({client['days_since']} days ago)"),
        ("Growth Target", f"{client['growth_target']:.0f}%"),
        ("Account ID",    client['account_id']),
    ]
    for label, value in rows:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(50, 7, label + ":", ln=False)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 7, value, ln=True)
    pdf.ln(4)

    # ── TALKING POINTS ───────────────────────────────────
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(30, 158, 117)
    pdf.cell(0, 8, "Talking Points", ln=True)
    pdf.set_draw_color(30, 158, 117)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)
    pdf.set_text_color(40, 40, 40)

    for i, point in enumerate(talking_points, 1):
        pdf.set_font("Arial", "B", 10)
        pdf.cell(8, 7, f"{i}.", ln=False)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(162, 6, point)
        pdf.ln(2)
    pdf.ln(2)

    # ── FOOTER ────────────────────────────────────────────
    pdf.set_y(-20)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, f"Generated {datetime.today().strftime('%d %b %Y %H:%M')}  |  Confidential", align="C")

    pdf.output(filename)
    print(f"\n✅ Prep PDF exported: {filename}")
    return filename