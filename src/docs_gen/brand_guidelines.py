"""Mock Brand Guidelines PDF Generator.

Creates a sample brand guideline document that defines color palettes,
typography, tone of voice, and logo usage for the demo retailer.
Used by the ADK agent for grounding image generation and marketing content.
"""

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
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "brand_guidelines"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _color_swatch(hex_color, name):
    """Create a simple color swatch paragraph."""
    return f'<font color="{hex_color}"><b>&#9608;&#9608;&#9608;&#9608;</b></font>  {name} ({hex_color})'


def generate_brand_guidelines(output_path: str = None):
    config = load_config()
    retailer = config["retailer"]["name"]
    tagline = config["retailer"].get("tagline", "")

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / "brand_guidelines.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="BrandTitle", fontSize=28, leading=34,
        alignment=TA_CENTER, spaceAfter=8,
        textColor=colors.HexColor("#2e7d32"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="BrandSub", fontSize=13, leading=17,
        alignment=TA_CENTER, spaceAfter=6,
        textColor=colors.HexColor("#555555"),
    ))
    styles.add(ParagraphStyle(
        name="SH", fontSize=16, leading=20,
        spaceBefore=18, spaceAfter=10,
        textColor=colors.HexColor("#2e7d32"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SSH", fontSize=12, leading=15,
        spaceBefore=10, spaceAfter=6,
        textColor=colors.HexColor("#333333"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="BT", fontSize=10, leading=14, spaceAfter=8,
    ))

    story = []

    # Cover
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph(f"{retailer}", styles["BrandTitle"]))
    story.append(Paragraph("Brand Guidelines", styles["BrandTitle"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f'"{tagline}"', styles["BrandSub"]))
    story.append(Paragraph("Version 1.0 | Confidential", styles["BrandSub"]))
    story.append(PageBreak())

    # Brand Overview
    story.append(Paragraph("1. Brand Overview", styles["SH"]))
    story.append(Paragraph(
        f"{retailer} is committed to providing fresh, high-quality groceries at fair prices "
        "in a welcoming, community-oriented environment. Our brand reflects warmth, "
        "reliability, and a genuine connection to the neighborhoods we serve.",
        styles["BT"],
    ))
    story.append(Paragraph("1.1 Brand Values", styles["SSH"]))
    values = [
        "<b>Freshness</b> — We prioritize quality produce, meats, and bakery items sourced responsibly.",
        "<b>Community</b> — We are neighbors first. Our stores reflect local tastes and values.",
        "<b>Value</b> — Fair pricing without sacrificing quality. Loyalty rewards that matter.",
        "<b>Innovation</b> — Embracing technology to make shopping easier and more personal.",
    ]
    for v in values:
        story.append(Paragraph(f"&bull; {v}", styles["BT"]))

    # Color Palette
    story.append(Paragraph("2. Color Palette", styles["SH"]))
    story.append(Paragraph("2.1 Primary Colors", styles["SSH"]))
    primary_colors = [
        ("#2e7d32", "Market Green", "Primary brand color. Used for headers, logos, and key UI elements."),
        ("#ffffff", "Clean White", "Background color. Ensures readability and clean presentation."),
        ("#1a237e", "Trust Navy", "Secondary accent for text-heavy sections and corporate materials."),
    ]
    for hex_c, name, usage in primary_colors:
        story.append(Paragraph(_color_swatch(hex_c, name), styles["BT"]))
        story.append(Paragraph(f"  Usage: {usage}", styles["BT"]))

    story.append(Paragraph("2.2 Accent Colors", styles["SSH"]))
    accent_colors = [
        ("#c62828", "Deal Red", "Promotional pricing and sale tags only."),
        ("#f9a825", "Fresh Gold", "Highlights, badges, and loyalty program elements."),
        ("#0277bd", "Info Blue", "Informational callouts and links."),
        ("#f5f5f5", "Light Gray", "Table backgrounds, card surfaces, subtle dividers."),
    ]
    for hex_c, name, usage in accent_colors:
        story.append(Paragraph(_color_swatch(hex_c, name), styles["BT"]))
        story.append(Paragraph(f"  Usage: {usage}", styles["BT"]))

    # Typography
    story.append(PageBreak())
    story.append(Paragraph("3. Typography", styles["SH"]))
    story.append(Paragraph("3.1 Font Families", styles["SSH"]))
    fonts = [
        ["Usage", "Font", "Weight", "Size Range"],
        ["Headlines / H1", "Helvetica (or Google Sans)", "Bold", "24-32pt"],
        ["Subheadings / H2", "Helvetica (or Google Sans)", "Bold", "16-20pt"],
        ["Body Text", "Helvetica (or Roboto)", "Regular", "10-12pt"],
        ["Captions / Fine Print", "Helvetica (or Roboto)", "Regular", "8-9pt"],
        ["Prices / CTAs", "Helvetica (or Google Sans)", "Bold", "18-28pt"],
    ]
    font_table = Table(fonts, colWidths=[1.8 * inch, 2 * inch, 1 * inch, 1.2 * inch])
    font_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e7d32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f5f0")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(font_table)

    # Tone of Voice
    story.append(Paragraph("4. Tone of Voice", styles["SH"]))
    story.append(Paragraph("4.1 Writing Principles", styles["SSH"]))
    tone = [
        "<b>Warm &amp; Friendly</b> — Write like a helpful neighbor, not a corporation. Use conversational language.",
        "<b>Clear &amp; Direct</b> — Short sentences. Active voice. No jargon.",
        "<b>Positive &amp; Encouraging</b> — Focus on benefits. 'Save $1.50!' not 'Regular price $4.99.'",
        "<b>Inclusive</b> — Represent diverse communities. Avoid assumptions about family structure or diet.",
    ]
    for t in tone:
        story.append(Paragraph(f"&bull; {t}", styles["BT"]))

    story.append(Paragraph("4.2 Do's and Don'ts", styles["SSH"]))
    dos_donts = [
        ["Do", "Don't"],
        ["'Grab fresh bananas for just $0.39/lb!'", "'Product #101 is available at reduced cost.'"],
        ["'Your loyalty points just got you a free coffee.'", "'Customers with Gold status receive...'"],
        ["'Made with care, right here in Austin.'", "'Produced at our manufacturing facility.'"],
        ["'Questions? Ask any associate!'", "'Contact customer service for inquiries.'"],
    ]
    dd_table = Table(dos_donts, colWidths=[3 * inch, 3 * inch])
    dd_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#2e7d32")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#c62828")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(dd_table)

    # Logo Usage
    story.append(PageBreak())
    story.append(Paragraph("5. Logo Usage Guidelines", styles["SH"]))
    story.append(Paragraph(
        "The logo should always appear with sufficient clear space (minimum 0.5 inches on all sides). "
        "Never stretch, rotate, or apply effects to the logo. Use the primary Market Green on white "
        "backgrounds; use the reversed (white) logo on dark backgrounds.",
        styles["BT"],
    ))
    story.append(Paragraph("5.1 Minimum Sizes", styles["SSH"]))
    story.append(Paragraph("&bull; Print: 1.5 inches wide minimum", styles["BT"]))
    story.append(Paragraph("&bull; Digital: 120px wide minimum", styles["BT"]))
    story.append(Paragraph("&bull; Favicon: 32x32px", styles["BT"]))

    # Photography
    story.append(Paragraph("6. Photography &amp; Imagery", styles["SH"]))
    story.append(Paragraph(
        "Product photography should be bright, naturally lit, and show food in appetizing "
        "contexts — on cutting boards, in bowls, or being prepared. Avoid sterile product-on-white "
        "shots. People in marketing imagery should reflect the diversity of our communities.",
        styles["BT"],
    ))
    story.append(Paragraph("6.1 Product Image Requirements", styles["SSH"]))
    img_reqs = [
        "High resolution: minimum 2000x2000px for catalog, 800x800px for web.",
        "Consistent lighting: natural daylight preferred, no harsh shadows.",
        "Background: lifestyle context or clean neutral (light wood, marble, linen).",
        "Brand elements: subtle inclusion of brand colors in props or setting.",
    ]
    for req in img_reqs:
        story.append(Paragraph(f"&bull; {req}", styles["BT"]))

    doc.build(story)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_brand_guidelines()
