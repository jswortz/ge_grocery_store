"""Quarterly Strategy Report PDF Generator.

Generates a professional Q4 strategy document covering customer experience
enhancement, operational efficiency, and technology-driven initiatives.
All retailer references are loaded from config.
"""

import os
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CoverTitle",
        fontSize=28,
        leading=34,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#4a4a6a"),
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=16,
        leading=20,
        spaceBefore=18,
        spaceAfter=10,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SubHeader",
        fontSize=12,
        leading=15,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#2d2d4e"),
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    ))
    return styles


def generate_strategy_report(output_path: str = None):
    config = load_config()
    retailer = config["retailer"]["name"]

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / "quarterly_strategy_report.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = build_styles()
    story = []

    # Cover page
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph(f"{retailer}", styles["CoverTitle"]))
    story.append(Paragraph("Q4 Quarterly Strategy Report", styles["CoverTitle"]))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Customer Experience, Operational Efficiency &amp; Technology Innovation", styles["CoverSubtitle"]))
    story.append(Paragraph(f"Prepared: {date.today().strftime('%B %Y')}", styles["CoverSubtitle"]))
    story.append(Paragraph("CONFIDENTIAL — For Internal Distribution Only", styles["CoverSubtitle"]))
    story.append(PageBreak())

    # Executive Summary
    story.append(Paragraph("1. Executive Summary", styles["SectionHeader"]))
    story.append(Paragraph(
        f"This report outlines {retailer}'s strategic priorities for Q4, focusing on three "
        "interconnected pillars: enhancing the customer experience through personalization and "
        "digital engagement, improving operational efficiency across our store network, and "
        "leveraging emerging AI technologies — specifically Google Cloud's Gemini Enterprise "
        "platform — to drive measurable business outcomes.",
        styles["BodyText2"],
    ))
    story.append(Paragraph(
        "Key Q4 targets include a 12% increase in digital engagement, 8% reduction in "
        "inventory shrinkage, and deployment of AI-powered associate tools across all locations.",
        styles["BodyText2"],
    ))

    # Customer Experience
    story.append(Paragraph("2. Customer Experience Enhancement", styles["SectionHeader"]))
    story.append(Paragraph("2.1 Personalization at Scale", styles["SubHeader"]))
    story.append(Paragraph(
        "Loyalty program analytics reveal that Gold-tier members generate 3.2x the average "
        "transaction value. Q4 initiatives will focus on personalized promotions driven by "
        "purchase history analysis, targeted through mobile app notifications and in-store "
        "digital displays. The Gemini Enterprise platform enables natural-language querying "
        "of customer segments directly from our BigQuery data warehouse.",
        styles["BodyText2"],
    ))
    story.append(Paragraph("2.2 Digital-First Engagement", styles["SubHeader"]))
    story.append(Paragraph(
        "Expanding our mobile-first strategy with real-time inventory visibility, "
        "personalized weekly deals, and seamless BOPIS (Buy Online, Pick Up In Store) "
        "experiences. AI-assisted product recommendations will leverage Gemini's "
        "multi-modal capabilities to suggest complementary items based on shopping patterns.",
        styles["BodyText2"],
    ))
    story.append(Paragraph("2.3 In-Store Experience", styles["SubHeader"]))
    story.append(Paragraph(
        "Deploying interactive kiosks powered by conversational AI for recipe suggestions, "
        "product locator, and nutritional information. Associates equipped with AI-powered "
        "handheld devices can answer customer queries with enterprise-grounded responses.",
        styles["BodyText2"],
    ))

    # Operational Efficiency
    story.append(Paragraph("3. Operational Efficiency", styles["SectionHeader"]))
    story.append(Paragraph("3.1 Inventory Optimization", styles["SubHeader"]))
    story.append(Paragraph(
        "Implementing predictive demand forecasting using historical transaction data "
        "combined with external signals (weather, local events, seasonal trends). The "
        "star schema in BigQuery enables rapid analysis across product categories, "
        "store locations, and time dimensions.",
        styles["BodyText2"],
    ))

    # KPI table
    kpi_data = [
        ["KPI", "Current", "Q4 Target", "Initiative"],
        ["Inventory Shrinkage", "2.4%", "2.2%", "AI demand forecasting"],
        ["Checkout Wait Time", "4.2 min", "3.0 min", "Smart scheduling"],
        ["Associate Productivity", "Baseline", "+15%", "AI-powered tools"],
        ["Digital Engagement", "22%", "34%", "Mobile app expansion"],
        ["Customer Satisfaction", "4.1/5", "4.5/5", "Personalization engine"],
    ]
    kpi_table = Table(kpi_data, colWidths=[1.8 * inch, 1.1 * inch, 1.1 * inch, 2 * inch])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(kpi_table)

    story.append(Paragraph("3.2 Workforce Scheduling", styles["SubHeader"]))
    story.append(Paragraph(
        "AI-driven shift optimization that balances labor costs with customer traffic "
        "patterns. Analysis of transaction timestamps reveals peak hours vary significantly "
        "by store location, requiring location-specific scheduling models.",
        styles["BodyText2"],
    ))

    # Technology & AI
    story.append(PageBreak())
    story.append(Paragraph("4. Technology & AI Strategy", styles["SectionHeader"]))
    story.append(Paragraph("4.1 Gemini Enterprise Platform", styles["SubHeader"]))
    story.append(Paragraph(
        "The Gemini Enterprise platform (Discovery Engine) provides our foundation for "
        "enterprise AI capabilities. Key components include: StreamAssist for conversational "
        "agent interactions, Vertex AI Search for grounded document retrieval, and the "
        "Agent Development Kit (ADK) for building specialized tools.",
        styles["BodyText2"],
    ))
    story.append(Paragraph("4.2 Data Architecture", styles["SubHeader"]))
    story.append(Paragraph(
        "Our BigQuery star schema provides the analytics backbone, with transaction-level "
        "granularity across stores, products, employees, and customers. Multi-modal "
        "enrichment of the product catalog (images, descriptions) enables next-generation "
        "AI experiences including visual product search and automated marketing content.",
        styles["BodyText2"],
    ))
    story.append(Paragraph("4.3 AI-Powered Associate Tools", styles["SubHeader"]))
    story.append(Paragraph(
        "Frontline associates will have access to an AI assistant capable of: retrieving "
        "standard operating procedures, generating brand-compliant marketing materials, "
        "and answering data-driven questions about store performance. All responses are "
        "grounded in enterprise data stores to ensure accuracy and compliance.",
        styles["BodyText2"],
    ))

    # Next Steps
    story.append(Paragraph("5. Next Steps & Timeline", styles["SectionHeader"]))
    timeline_data = [
        ["Phase", "Description", "Timeline"],
        ["Phase 1", "BigQuery schema deployment & data ingestion", "Week 1-2"],
        ["Phase 2", "Discovery Engine provisioning & document stores", "Week 2-3"],
        ["Phase 3", "ADK agent development & tool integration", "Week 3-5"],
        ["Phase 4", "Associate pilot program (1 store)", "Week 5-7"],
        ["Phase 5", "Full rollout & performance monitoring", "Week 8-12"],
    ]
    timeline_table = Table(timeline_data, colWidths=[1.2 * inch, 3 * inch, 1.5 * inch])
    timeline_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(timeline_table)

    doc.build(story)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_strategy_report()
