from fpdf import FPDF
from datetime import datetime

def export_digest_to_pdf(top_clients, pipeline, followups, date_str=None):
    if date_str is None:
        date_str = datetime.today().strftime("%A, %d %B %Y")

    file_date = datetime.today().strftime("%Y%m%d")
    filename = f"digest_{file_date}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── HEADER ──────────────────────────────────────────
    pdf.set_fill_color(30, 158, 117)          # teal
    pdf.rect(0, 0, 210, 28, style="F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(8)
    pdf.cell(0, 12, "Daily Client Digest", align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, date_str, align="C")
    pdf.ln(16)

    # ── SECTION HELPER ───────────────────────────────────
    def section_title(title):
        pdf.set_font("Helvetica", "B", 11)
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
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(8, 7, f"#{i}", ln=False)
        pdf.set_font("Helvetica", "", 10)
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
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(70, 7, opp["client"], ln=False)
        pdf.cell(50, 7, f"£{opp['value']:,.0f}", ln=False)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, f"[{opp['stage']}]", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
    pdf.ln(4)

    # ── FOLLOW-UPS ────────────────────────────────────────
    section_title("Follow-Ups Needed (7+ days since contact)")
    for fu in followups:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(70, 7, fu["client"], ln=False)
        pdf.cell(55, 7, f"Last contact: {fu['last_contact']}", ln=False)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(180, 60, 60)
        pdf.cell(0, 7, f"({fu['days_ago']} days ago)", ln=True)
        pdf.set_text_color(40, 40, 40)
    pdf.ln(6)

    # ── FOOTER ────────────────────────────────────────────
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, f"Generated {datetime.today().strftime('%d %b %Y %H:%M')}  |  Confidential", align="C")

    pdf.output(filename)
    print(f"\n✅ PDF exported: {filename}")
    return filename