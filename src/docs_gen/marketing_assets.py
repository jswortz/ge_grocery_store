"""Marketing Layout and Promotional Asset Generator.

Generates brand-compliant promotional content PDFs including weekly deals,
product spotlights, and seasonal campaigns.
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
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "templates"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def generate_weekly_deals(output_path: str = None):
    """Generate a weekly promotional deals flyer."""
    config = load_config()
    retailer = config["retailer"]["name"]
    tagline = config["retailer"].get("tagline", "")

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / "weekly_deals.pdf")

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PromoTitle", fontSize=30, leading=36,
        alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor("#c62828"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="PromoSub", fontSize=14, leading=18,
        alignment=TA_CENTER, spaceAfter=8,
        textColor=colors.HexColor("#333333"),
    ))
    styles.add(ParagraphStyle(
        name="DealHeader", fontSize=14, leading=17,
        spaceBefore=12, spaceAfter=6,
        textColor=colors.HexColor("#1b5e20"), fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="DealBody", fontSize=10, leading=14, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="PriceTag", fontSize=20, leading=24,
        textColor=colors.HexColor("#c62828"), fontName="Helvetica-Bold",
    ))

    story = []

    # Header
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"{retailer}", styles["PromoTitle"]))
    story.append(Paragraph("Weekly Deals", styles["PromoTitle"]))
    story.append(Paragraph(tagline, styles["PromoSub"]))
    story.append(Paragraph(f"Valid: {date.today().strftime('%m/%d')} - Next Week", styles["PromoSub"]))
    story.append(Spacer(1, 0.3 * inch))

    # Deals grid
    deals = [
        ("Golden Grain White Bread", "$1.99", "Save $0.50!", "Buy 2, get 1 free on all Golden Grain bakery items."),
        ("Farm Fresh Bananas", "$0.39/lb", "Save $0.20/lb!", "Ripe and ready. Perfect for smoothies and snacking."),
        ("Valley Dairy Whole Milk", "$2.99/gal", "Save $0.80!", "Farm-fresh whole milk, now at our lowest price."),
        ("Prairie Ranch Chicken Breast", "$2.99/lb", "Save $1.00/lb!", "Boneless, skinless. Stock up for the week."),
        ("Nano Banana Pro Bar", "$3.49", "Save $1.50!", "High-protein banana bread bar. New and exclusive."),
        ("Crystal Springs Sparkling Water", "2 for $2.00", "BOGO!", "Naturally carbonated. 12 oz bottles."),
    ]

    for name, price, savings, desc in deals:
        deal_data = [
            [Paragraph(f"<b>{name}</b>", styles["DealBody"]),
             Paragraph(price, styles["PriceTag"])],
            [Paragraph(desc, styles["DealBody"]),
             Paragraph(f"<font color='#1b5e20'><b>{savings}</b></font>", styles["DealBody"])],
        ]
        deal_table = Table(deal_data, colWidths=[4 * inch, 2 * inch])
        deal_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#e0e0e0")),
        ]))
        story.append(deal_table)
        story.append(Spacer(1, 0.1 * inch))

    # Footer
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "Prices valid at all locations. While supplies last. "
        "Rain checks available. Loyalty card required for member pricing.",
        ParagraphStyle(
            name="Footer", fontSize=8, leading=10,
            alignment=TA_CENTER, textColor=colors.HexColor("#888888"),
        ),
    ))

    doc.build(story)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_weekly_deals()
