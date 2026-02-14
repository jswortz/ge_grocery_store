"""Industry Analyst Consulting Report PDF Generator.

Generates a market analysis and technology recommendation document
focused on AI adoption in grocery retail.
"""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
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
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "templates"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def generate_analyst_report(output_path: str = None):
    config = load_config()
    retailer = config["retailer"]["name"]

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / "industry_analyst_report.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle", fontSize=26, leading=32,
        alignment=TA_CENTER, spaceAfter=12,
        textColor=colors.HexColor("#0d1b2a"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="CoverSub", fontSize=13, leading=17,
        alignment=TA_CENTER, spaceAfter=6, textColor=colors.HexColor("#3a506b"),
    ))
    styles.add(ParagraphStyle(
        name="SH", fontSize=15, leading=19, spaceBefore=16, spaceAfter=10,
        textColor=colors.HexColor("#0d1b2a"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SSH", fontSize=11, leading=14, spaceBefore=10, spaceAfter=5,
        textColor=colors.HexColor("#1b2838"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="BT", fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=8,
    ))

    story = []

    # Cover
    story.append(Spacer(1, 2.5 * inch))
    story.append(Paragraph("Industry Analyst Report", styles["CoverTitle"]))
    story.append(Paragraph("AI-Driven Transformation in Grocery Retail", styles["CoverTitle"]))
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(f"Prepared for {retailer} Leadership", styles["CoverSub"]))
    story.append(Paragraph(f"{date.today().strftime('%B %Y')} | Confidential", styles["CoverSub"]))
    story.append(PageBreak())

    # Market Overview
    story.append(Paragraph("1. Market Overview", styles["SH"]))
    story.append(Paragraph(
        "The U.S. grocery market reached $1.1 trillion in 2024, with digital grocery "
        "sales accounting for 12.4% of total revenue — up from 7.2% pre-pandemic. "
        "Competitive pressure from discount retailers, direct-to-consumer brands, and "
        "quick commerce is accelerating the need for technology-driven differentiation.",
        styles["BT"],
    ))
    story.append(Paragraph(
        "Key industry trends include: hyper-personalization of promotions (driving 18% "
        "higher redemption rates), AI-powered inventory management (reducing shrinkage "
        "by 15-20%), and conversational AI for both customer-facing and associate-facing "
        "applications.",
        styles["BT"],
    ))

    # Competitive Landscape
    story.append(Paragraph("2. Competitive Landscape", styles["SH"]))
    comp_data = [
        ["Capability", "Industry Leaders", "Industry Average", f"{retailer}"],
        ["AI-Powered Recommendations", "Deployed", "Piloting", "Planning"],
        ["Predictive Demand Forecasting", "Deployed", "Piloting", "Piloting"],
        ["Conversational AI (Customer)", "Deployed", "Not Started", "Planning"],
        ["Conversational AI (Associate)", "Piloting", "Not Started", "Planning"],
        ["Multi-Modal Product Search", "Piloting", "Not Started", "Not Started"],
        ["Real-Time Inventory Visibility", "Deployed", "Piloting", "Deployed"],
    ]
    comp_table = Table(comp_data, colWidths=[2 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch])
    comp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1b2a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f7")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(comp_table)

    # Technology Assessment
    story.append(Paragraph("3. Technology Assessment: Gemini Enterprise", styles["SH"]))
    story.append(Paragraph("3.1 Platform Capabilities", styles["SSH"]))
    story.append(Paragraph(
        "Google Cloud's Gemini Enterprise platform (built on the Discovery Engine API) "
        "provides an integrated suite for building enterprise AI applications. Core "
        "capabilities include:",
        styles["BT"],
    ))
    capabilities = [
        "<b>StreamAssist API</b> — Conversational agent endpoint with session management, "
        "multi-turn reasoning, and grounded responses from enterprise data stores.",
        "<b>Vertex AI Search</b> — Enterprise document search with semantic understanding, "
        "supporting unstructured (PDFs, docs) and structured (BigQuery, databases) sources.",
        "<b>Agent Development Kit (ADK)</b> — Python/Java/Go framework for building "
        "multi-tool agents with sequential, parallel, and loop orchestration patterns.",
        "<b>Multi-Modal Models</b> — Gemini 2.0/2.5 Flash models supporting text, image, "
        "audio, and video inputs for product recognition, visual search, and content generation.",
    ]
    for cap in capabilities:
        story.append(Paragraph(f"&bull; {cap}", styles["BT"]))

    story.append(Paragraph("3.2 Data Residency & Regional Availability", styles["SSH"]))
    story.append(Paragraph(
        "<b>Finding:</b> Discovery Engine supports global and select regional endpoints "
        "(us, eu). The StreamAssist API is confirmed operational on the global endpoint. "
        "Regional endpoint availability for streamAssist should be validated for compliance "
        "requirements. BigQuery datasets can be pinned to specific US regions.",
        styles["BT"],
    ))
    story.append(Paragraph(
        "<b>Gap:</b> Fine-grained data residency guarantees for Discovery Engine data stores "
        "are not explicitly documented for all regions. Organizations with strict data "
        "sovereignty requirements should engage Google Cloud support for region-specific SLAs.",
        styles["BT"],
    ))

    # Recommendations
    story.append(PageBreak())
    story.append(Paragraph("4. Recommendations", styles["SH"]))
    story.append(Paragraph("4.1 Immediate Actions (Q4)", styles["SSH"]))
    recs = [
        "Deploy BigQuery star schema with transaction, product, store, and customer dimensions "
        "to enable unified analytics.",
        "Provision Discovery Engine with curated data stores for SOPs, brand guidelines, "
        "and product information.",
        "Build and pilot an ADK-based associate assistant at one store location, integrating "
        "SOP retrieval and brand-compliant content generation.",
        "Establish baseline metrics for associate productivity, customer satisfaction, and "
        "operational efficiency.",
    ]
    for i, rec in enumerate(recs, 1):
        story.append(Paragraph(f"<b>{i}.</b> {rec}", styles["BT"]))

    story.append(Paragraph("4.2 Medium-Term (Q1-Q2 Next Year)", styles["SSH"]))
    recs2 = [
        "Expand AI assistant to customer-facing channels (mobile app, in-store kiosks).",
        "Integrate predictive demand forecasting with automated reorder recommendations.",
        "Deploy multi-modal product search enabling visual and natural language queries.",
        "Scale associate tools across all store locations with performance monitoring.",
    ]
    for i, rec in enumerate(recs2, 1):
        story.append(Paragraph(f"<b>{i}.</b> {rec}", styles["BT"]))

    # ROI Projection
    story.append(Paragraph("5. ROI Projection", styles["SH"]))
    roi_data = [
        ["Investment Area", "Annual Cost", "Projected Annual Benefit", "ROI"],
        ["Gemini Enterprise Platform", "$120K", "$450K (productivity gains)", "275%"],
        ["BigQuery Analytics", "$30K", "$180K (shrinkage reduction)", "500%"],
        ["ADK Agent Development", "$80K", "$320K (labor optimization)", "300%"],
        ["Total", "$230K", "$950K", "313%"],
    ]
    roi_table = Table(roi_data, colWidths=[2 * inch, 1.2 * inch, 2 * inch, 0.8 * inch])
    roi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1b2a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2f7")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8eef5")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(roi_table)

    doc.build(story)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_analyst_report()
