"""Frontline SOP Document Generator.

Generates Standard Operating Procedure PDFs for grocery retail frontline
associates: closing procedures, opening checklists, and safety protocols.
"""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sops"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _header_style():
    return ParagraphStyle(
        name="SOPHeader", fontSize=18, leading=22,
        alignment=TA_CENTER, spaceAfter=6,
        textColor=colors.HexColor("#1a237e"), fontName="Helvetica-Bold",
    )


def _section_style():
    return ParagraphStyle(
        name="SOPSection", fontSize=13, leading=16,
        spaceBefore=14, spaceAfter=8,
        textColor=colors.HexColor("#1a237e"), fontName="Helvetica-Bold",
    )


def _step_style():
    return ParagraphStyle(
        name="SOPStep", fontSize=10, leading=14,
        leftIndent=20, spaceAfter=4,
    )


def _note_style():
    return ParagraphStyle(
        name="SOPNote", fontSize=9, leading=12,
        leftIndent=40, spaceAfter=6,
        textColor=colors.HexColor("#555555"), fontName="Helvetica-Oblique",
    )


def generate_closing_sop(output_path: str = None):
    """Generate the store closing procedures SOP."""
    config = load_config()
    retailer = config["retailer"]["name"]

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / "closing_procedures.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=60, leftMargin=60, topMargin=60, bottomMargin=60,
    )

    hdr = _header_style()
    sec = _section_style()
    step = _step_style()
    note = _note_style()

    story = []

    # Title
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"{retailer} — Standard Operating Procedures", hdr))
    story.append(Paragraph("Store Closing Procedures", hdr))
    story.append(Spacer(1, 0.2 * inch))
    meta_data = [
        ["Document ID", "SOP-CLOSE-001"],
        ["Effective Date", date.today().strftime("%Y-%m-%d")],
        ["Department", "Store Operations"],
        ["Audience", "All Frontline Associates"],
        ["Review Cycle", "Quarterly"],
    ]
    meta_table = Table(meta_data, colWidths=[1.5 * inch, 3 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eaf6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3 * inch))

    # Section 1: Pre-Closing (1 hour before)
    story.append(Paragraph("1. Pre-Closing Procedures (60 Minutes Before Close)", sec))
    pre_close = [
        "1.1 Announce last call for customers over PA system.",
        "1.2 Begin consolidating perishable displays — return unsold items to coolers.",
        "1.3 Verify all self-checkout stations are operational; clear any error states.",
        "1.4 Department managers complete end-of-day inventory counts for high-value items.",
        "1.5 Stock clerks begin front-facing remaining shelf inventory.",
    ]
    for s in pre_close:
        story.append(Paragraph(s, step))
    story.append(Paragraph(
        "Note: Do not block customer access to aisles during front-facing.",
        note,
    ))

    # Section 2: Customer Exit
    story.append(Paragraph("2. Customer Exit & Door Procedures", sec))
    exit_steps = [
        "2.1 At closing time, make final PA announcement: store is now closed.",
        "2.2 Station one associate at each entrance to politely direct remaining customers to checkout.",
        "2.3 Lock all entrance doors; switch automatic doors to exit-only mode.",
        "2.4 Complete a full walkthrough of all aisles to confirm no customers remain.",
        "2.5 Check restrooms, break rooms, and storage areas.",
    ]
    for s in exit_steps:
        story.append(Paragraph(s, step))

    # Section 3: Register Close-Out
    story.append(Paragraph("3. Register Close-Out", sec))
    register_steps = [
        "3.1 Each cashier runs end-of-shift report on their assigned register.",
        "3.2 Count cash drawer — record actual vs. expected in the daily reconciliation log.",
        "3.3 Report any discrepancies exceeding $5.00 to the closing manager immediately.",
        "3.4 Secure cash in the safe according to dual-control procedures.",
        "3.5 Close all POS terminals and power down card readers.",
    ]
    for s in register_steps:
        story.append(Paragraph(s, step))
    story.append(Paragraph(
        "Note: Never leave cash unattended during the close-out process.",
        note,
    ))

    # Section 4: Cleaning
    story.append(Paragraph("4. Cleaning & Sanitation", sec))
    cleaning = [
        "4.1 Sweep and mop all floor areas (produce, deli, bakery, main aisles).",
        "4.2 Clean and sanitize all food preparation surfaces (deli, bakery, meat).",
        "4.3 Empty all trash receptacles; replace liners.",
        "4.4 Clean restrooms: restock supplies, mop floors, sanitize fixtures.",
        "4.5 Wipe down checkout belts and self-checkout screens.",
    ]
    for s in cleaning:
        story.append(Paragraph(s, step))

    # Section 5: Security
    story.append(PageBreak())
    story.append(Paragraph("5. Security & Building Close", sec))
    security = [
        "5.1 Set refrigeration and HVAC to overnight mode via building management system.",
        "5.2 Turn off non-essential lighting (sales floor); leave security lighting active.",
        "5.3 Verify all emergency exits are properly secured with crash bars functional.",
        "5.4 Arm the security system using the closing manager's access code.",
        "5.5 Complete the closing checklist in the store operations log (paper or digital).",
        "5.6 All associates exit through the designated employee entrance.",
        "5.7 Closing manager performs final lock check on all exterior doors.",
    ]
    for s in security:
        story.append(Paragraph(s, step))
    story.append(Paragraph(
        "Note: The closing manager is the last person to leave the building.",
        note,
    ))

    # Section 6: Emergency Procedures
    story.append(Paragraph("6. Emergency Procedures During Close", sec))
    emergency = [
        "6.1 If a medical emergency occurs, call 911 first, then notify the store manager.",
        "6.2 If a security incident occurs, do not confront — contact security dispatch.",
        "6.3 If fire alarm activates, evacuate all associates through nearest emergency exit.",
        "6.4 Report any maintenance issues (broken equipment, leaks) in the facilities log.",
    ]
    for s in emergency:
        story.append(Paragraph(s, step))

    # Sign-off
    story.append(Spacer(1, 0.5 * inch))
    signoff_data = [
        ["Closing Manager Signature:", "___________________________"],
        ["Date:", "___________________________"],
        ["Store Location:", "___________________________"],
    ]
    signoff_table = Table(signoff_data, colWidths=[2.5 * inch, 3 * inch])
    signoff_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(signoff_table)

    doc.build(story)
    print(f"Generated: {output_path}")
    return output_path


def generate_opening_sop(output_path: str = None):
    """Generate the store opening procedures SOP."""
    config = load_config()
    retailer = config["retailer"]["name"]

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / "opening_procedures.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=60, leftMargin=60, topMargin=60, bottomMargin=60,
    )

    hdr = _header_style()
    sec = _section_style()
    step = _step_style()
    note = _note_style()

    story = []
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"{retailer} — Standard Operating Procedures", hdr))
    story.append(Paragraph("Store Opening Procedures", hdr))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("1. Building Access & Safety Check", sec))
    steps = [
        "1.1 Opening manager arrives 60 minutes before store opens.",
        "1.2 Disarm security system using assigned access code.",
        "1.3 Perform exterior walkthrough: check for damage, obstructions, or safety hazards.",
        "1.4 Turn on main lighting and adjust HVAC to daytime settings.",
        "1.5 Check refrigeration temperatures — log any out-of-range readings.",
    ]
    for s in steps:
        story.append(Paragraph(s, step))

    story.append(Paragraph("2. Department Readiness", sec))
    steps = [
        "2.1 Produce: inspect and rotate displays, pull any items past sell-by date.",
        "2.2 Deli/Bakery: begin heating equipment, verify food safety temp logs.",
        "2.3 Meat/Seafood: verify case temperatures, stock fresh items from walk-in.",
        "2.4 Grocery: spot-check shelf gaps from overnight stocking.",
        "2.5 Front End: power on all POS terminals, verify card reader connectivity.",
    ]
    for s in steps:
        story.append(Paragraph(s, step))

    story.append(Paragraph("3. Associate Check-In", sec))
    steps = [
        "3.1 Verify all scheduled associates have arrived; contact no-shows.",
        "3.2 Brief team on daily priorities, promotions, and any alerts.",
        "3.3 Assign cash drawers to cashiers (dual-count verification).",
        "3.4 Confirm break schedule for the shift.",
    ]
    for s in steps:
        story.append(Paragraph(s, step))

    story.append(Paragraph("4. Store Opening", sec))
    steps = [
        "4.1 Unlock customer entrance doors 5 minutes before posted opening time.",
        "4.2 Switch automatic doors to full-access mode.",
        "4.3 Make PA welcome announcement.",
        "4.4 Opening manager logs opening time and any exceptions in the operations log.",
    ]
    for s in steps:
        story.append(Paragraph(s, step))

    doc.build(story)
    print(f"Generated: {output_path}")
    return output_path


def generate_all_sops():
    """Generate all SOP documents."""
    paths = []
    paths.append(generate_closing_sop())
    paths.append(generate_opening_sop())
    return paths


if __name__ == "__main__":
    generate_all_sops()
