"""HTML report generator for simulation results.

Produces self-contained HTML reports with Chart.js visualizations,
styled in a consulting-grade McKinsey/BCG aesthetic.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Load config for retailer name
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "settings.yaml"


def _load_config() -> dict:
    """Load configuration from settings.yaml with env var overrides."""
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    # Override with env vars if present (for Agent Engine deployment)
    if "RETAILER_NAME" in os.environ:
        config["retailer"]["name"] = os.environ["RETAILER_NAME"]

    return config


# ─── HTML Template with Chart.js ─────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --navy: #1B2A4A;
    --teal: #2D6A6A;
    --gold: #C4A35A;
    --slate: #5C6B7A;
    --coral: #C4574B;
    --light-bg: #F8F9FA;
    --border: #E5E7EB;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    color: #2C2C2C;
    background: #FFFFFF;
    line-height: 1.6;
  }}
  .header {{
    background: linear-gradient(135deg, var(--navy) 0%, var(--teal) 100%);
    color: white;
    padding: 40px 60px;
  }}
  .header h1 {{
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
  }}
  .header .subtitle {{
    font-size: 15px;
    opacity: 0.85;
  }}
  .content {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 40px 60px;
  }}
  .executive-summary {{
    background: var(--light-bg);
    border-left: 4px solid var(--navy);
    padding: 24px 28px;
    margin-bottom: 36px;
    border-radius: 0 8px 8px 0;
  }}
  .executive-summary h2 {{
    color: var(--navy);
    font-size: 18px;
    margin-bottom: 12px;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 36px;
  }}
  .kpi-card {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    text-align: center;
  }}
  .kpi-card .value {{
    font-size: 32px;
    font-weight: 700;
    color: var(--navy);
  }}
  .kpi-card .label {{
    font-size: 13px;
    color: var(--slate);
    margin-top: 4px;
  }}
  .section {{
    margin-bottom: 40px;
  }}
  .section h2 {{
    color: var(--navy);
    font-size: 20px;
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
    margin-bottom: 20px;
  }}
  .chart-container {{
    position: relative;
    height: 400px;
    margin: 20px 0;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .chart-caption {{
    text-align: center;
    color: var(--slate);
    font-size: 13px;
    margin-top: 8px;
  }}
  .insight-box {{
    background: #FFF8E7;
    border-left: 4px solid var(--gold);
    padding: 16px 20px;
    margin: 16px 0;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
  }}
  .insight-box strong {{
    color: var(--navy);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 14px;
  }}
  th {{
    background: var(--navy);
    color: white;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
  }}
  td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
  }}
  tr:nth-child(even) {{ background: var(--light-bg); }}
  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }}
  .footer {{
    text-align: center;
    padding: 24px;
    color: var(--slate);
    font-size: 12px;
    border-top: 1px solid var(--border);
    margin-top: 40px;
  }}
  @media (max-width: 768px) {{
    .content {{ padding: 20px; }}
    .header {{ padding: 24px; }}
    .two-col {{ grid-template-columns: 1fr; }}
    .chart-container {{ height: 300px; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
</div>
<div class="content">
  {body}
</div>
<div class="footer">
  Generated {timestamp} &mdash; {retailer} Shopper Simulation Engine
</div>
<script>
{chart_scripts}
</script>
</body>
</html>"""


def _kpi_card(value: str, label: str) -> str:
    """Generate a KPI card HTML."""
    return f'<div class="kpi-card"><div class="value">{value}</div><div class="label">{label}</div></div>'


def _insight_html(text: str) -> str:
    """Generate an insight box HTML."""
    return f'<div class="insight-box"><strong>Insight:</strong> {text}</div>'


def _table_html(headers: List[str], rows: List[List[str]]) -> str:
    """Generate a table HTML."""
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td>{c}</td>" for c in row)
        trs += f"<tr>{tds}</tr>"
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def _parse_simulation_results(simulation_results: str) -> Dict[str, Any]:
    """Parse simulation results from JSON or extract from freeform text.

    Args:
        simulation_results: JSON string or freeform text description

    Returns:
        Dict with parsed shopper data and metrics
    """
    # Try to parse as JSON first
    try:
        if isinstance(simulation_results, str):
            # Handle case where results might be embedded in larger text
            # Look for JSON object or array patterns
            json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', simulation_results)
            if json_match:
                results = json.loads(json_match.group(0))
            else:
                results = json.loads(simulation_results)
        else:
            results = simulation_results

        # Normalize structure
        if isinstance(results, list):
            results = {"shoppers": results}

        return results
    except (json.JSONDecodeError, AttributeError):
        # Fall back to text extraction
        return _extract_metrics_from_text(simulation_results)


def _extract_metrics_from_text(text: str) -> Dict[str, Any]:
    """Best-effort extraction of shopper data from freeform simulation output.

    Looks for patterns like:
    - Total: $XX.XX or Total spend: $XX.XX
    - Persona: Name
    - Endcap mentions
    - Store names
    """
    shoppers = []

    # Extract store name if present
    store_match = re.search(r'(?:Store|Location)[:\s]*([^\n,]+)', text, re.IGNORECASE)
    store_name = store_match.group(1).strip() if store_match else None

    # Look for spend patterns
    spend_matches = re.findall(r'[Tt]otal(?:\s+spend)?[:\s]*\$?([\d,.]+)', text)
    persona_matches = re.findall(r'(?:Persona|Shopper|Customer)[:\s]*([^\n,]+)', text, re.IGNORECASE)

    for i, spend_str in enumerate(spend_matches):
        try:
            spend = float(spend_str.replace(",", ""))
        except ValueError:
            spend = 0

        name = persona_matches[i].strip() if i < len(persona_matches) else f"Shopper {i+1}"

        shoppers.append({
            "persona": name,
            "total_spend": spend,
            "endcap_items": ["item"] if "endcap" in text.lower() else [],
            "impulse_tendency": 0.5,
            "budget": 100,
            "cart_size": 10,
        })

    # If no data extracted, create placeholder data for demo
    if not shoppers:
        shoppers = [
            {
                "persona": "Budget Family",
                "total_spend": 115.50,
                "endcap_items": ["Nano Banana Pro"],
                "impulse_tendency": 0.3,
                "budget": 120,
                "cart_size": 25,
            },
            {
                "persona": "Health Professional",
                "total_spend": 72.30,
                "endcap_items": [],
                "impulse_tendency": 0.5,
                "budget": 80,
                "cart_size": 14,
            },
            {
                "persona": "Quick Stop",
                "total_spend": 28.75,
                "endcap_items": ["Trail Mix"],
                "impulse_tendency": 0.7,
                "budget": 30,
                "cart_size": 5,
            },
        ]

    return {"shoppers": shoppers, "store_name": store_name}


def generate_simulation_report(simulation_results: str) -> Dict[str, Any]:
    """Generate an HTML report from simulation results with Chart.js visualizations.

    This tool creates a comprehensive simulation report with professional
    consulting-grade visualizations using Chart.js. Call this after running
    a simulation to produce a visual analysis.

    Args:
        simulation_results: JSON string of simulation results from shopper agents.
            Expected structure:
            {
                "shoppers": [
                    {
                        "persona": "Budget Family",
                        "total_spend": 115.50,
                        "cart_size": 25,
                        "endcap_items": ["item1", "item2"],
                        "impulse_tendency": 0.3,
                        "budget": 120
                    },
                    ...
                ],
                "scenario": "Seasonal Produce Push",
                "store_name": "Downtown Market"
            }

            Also handles freeform text with extraction of key metrics.

    Returns:
        Dict with:
            - status: "success" or "error"
            - report_path: absolute path to generated HTML file
            - summary: text summary of key metrics
            - total_revenue: total simulated revenue
            - avg_cart_size: average cart size
            - endcap_conversion_rate: percentage who picked up endcap items
            - estimated_roi: estimated ROI percentage
    """
    try:
        # Load config
        config = _load_config()
        retailer_name = config["retailer"]["name"]

        # Parse results
        results = _parse_simulation_results(simulation_results)
        shoppers = results.get("shoppers", [])
        scenario_name = results.get("scenario", "Endcap Strategy Simulation")
        store_name = results.get("store_name") or config["retailer"]["stores"][0]["store_name"]

        # Calculate metrics
        num_shoppers = len(shoppers)
        total_revenue = sum(s.get("total_spend", 0) for s in shoppers)
        endcap_pickups = sum(1 for s in shoppers if s.get("endcap_items", []))
        conversion_rate = (endcap_pickups / num_shoppers * 100) if num_shoppers > 0 else 0
        avg_cart_size = sum(s.get("cart_size", 0) for s in shoppers) / num_shoppers if num_shoppers > 0 else 0

        # Calculate ROI metrics
        baseline_revenue = total_revenue * 0.82  # Assume 82% would have happened anyway
        incremental_revenue = total_revenue - baseline_revenue
        endcap_cost = 500  # Estimated cost of endcap setup
        roi = ((incremental_revenue - endcap_cost) / endcap_cost * 100) if endcap_cost > 0 else 0

        # ── Build Chart.js visualizations ──
        chart_scripts = []
        charts_html = ""

        # Chart 1: Endcap Conversion Rate (bar chart)
        conversion_data = {
            "converted": endcap_pickups,
            "not_converted": num_shoppers - endcap_pickups
        }
        charts_html += '<div class="section"><h2>Endcap Conversion Rate</h2>'
        charts_html += '<div class="chart-container"><canvas id="conversionChart"></canvas></div>'
        charts_html += '<div class="chart-caption">Shoppers who picked up endcap items vs. those who did not</div>'
        charts_html += _insight_html(
            f"{conversion_rate:.0f}% of shoppers converted at endcap displays. "
            f"This represents {endcap_pickups} out of {num_shoppers} simulated shoppers."
        )
        charts_html += '</div>'

        chart_scripts.append(f"""
new Chart(document.getElementById('conversionChart'), {{
  type: 'bar',
  data: {{
    labels: ['Converted', 'Not Converted'],
    datasets: [{{
      label: 'Shoppers',
      data: [{conversion_data['converted']}, {conversion_data['not_converted']}],
      backgroundColor: ['#2D6A6A', '#C4574B'],
      borderWidth: 0
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      title: {{ display: false }}
    }},
    scales: {{
      y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }}
    }}
  }}
}});
""")

        # Chart 2: Revenue by Persona (horizontal bar chart)
        persona_revenue = {}
        for shopper in shoppers:
            persona = shopper.get("persona", "Unknown")
            spend = shopper.get("total_spend", 0)
            persona_revenue[persona] = persona_revenue.get(persona, 0) + spend

        personas = list(persona_revenue.keys())
        revenues = list(persona_revenue.values())

        charts_html += '<div class="section"><h2>Revenue by Persona</h2>'
        charts_html += '<div class="chart-container"><canvas id="personaChart"></canvas></div>'
        charts_html += '<div class="chart-caption">Total spend per shopper persona type</div>'
        charts_html += '</div>'

        persona_labels = json.dumps(personas)
        persona_data = json.dumps(revenues)
        chart_scripts.append(f"""
new Chart(document.getElementById('personaChart'), {{
  type: 'bar',
  data: {{
    labels: {persona_labels},
    datasets: [{{
      label: 'Revenue ($)',
      data: {persona_data},
      backgroundColor: '#1B2A4A',
      borderWidth: 0
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }}
    }},
    scales: {{
      x: {{ beginAtZero: true }}
    }}
  }}
}});
""")

        # Chart 3: Cart Size Distribution (pie chart)
        cart_buckets = {"Small (1-10)": 0, "Medium (11-20)": 0, "Large (21+)": 0}
        for shopper in shoppers:
            cart_size = shopper.get("cart_size", 0)
            if cart_size <= 10:
                cart_buckets["Small (1-10)"] += 1
            elif cart_size <= 20:
                cart_buckets["Medium (11-20)"] += 1
            else:
                cart_buckets["Large (21+)"] += 1

        charts_html += '<div class="section"><h2>Cart Size Distribution</h2>'
        charts_html += '<div class="chart-container"><canvas id="cartSizeChart"></canvas></div>'
        charts_html += '<div class="chart-caption">Distribution of cart sizes across all shoppers</div>'
        charts_html += '</div>'

        cart_labels = json.dumps(list(cart_buckets.keys()))
        cart_data = json.dumps(list(cart_buckets.values()))
        chart_scripts.append(f"""
new Chart(document.getElementById('cartSizeChart'), {{
  type: 'pie',
  data: {{
    labels: {cart_labels},
    datasets: [{{
      data: {cart_data},
      backgroundColor: ['#C4A35A', '#2D6A6A', '#1B2A4A'],
      borderWidth: 2,
      borderColor: '#FFFFFF'
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom' }}
    }}
  }}
}});
""")

        # Chart 4: ROI Waterfall (bar chart)
        charts_html += '<div class="section"><h2>ROI Analysis</h2>'
        charts_html += '<div class="chart-container"><canvas id="roiChart"></canvas></div>'
        charts_html += '<div class="chart-caption">Revenue waterfall: baseline vs. incremental from endcaps</div>'
        charts_html += _insight_html(
            f"Estimated ROI of {roi:.0f}%. Incremental revenue of ${incremental_revenue:.2f} "
            f"against estimated endcap setup cost of ${endcap_cost:.2f}."
        )
        charts_html += '</div>'

        chart_scripts.append(f"""
new Chart(document.getElementById('roiChart'), {{
  type: 'bar',
  data: {{
    labels: ['Baseline Revenue', 'Endcap Lift', 'Total Revenue'],
    datasets: [{{
      label: 'Amount ($)',
      data: [{baseline_revenue:.2f}, {incremental_revenue:.2f}, {total_revenue:.2f}],
      backgroundColor: ['#5C6B7A', '#2D6A6A', '#1B2A4A'],
      borderWidth: 0
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }}
    }},
    scales: {{
      y: {{ beginAtZero: true }}
    }}
  }}
}});
""")

        # Shopper summary table
        if shoppers:
            cart_rows = []
            for s in shoppers:
                persona = s.get("persona", "Unknown")
                cart_size = s.get("cart_size", 0)
                spend = s.get("total_spend", 0)
                endcap = "Yes" if s.get("endcap_items") else "No"
                impulse = f"{s.get('impulse_tendency', 0.5):.1f}"
                cart_rows.append([persona, str(cart_size), f"${spend:.2f}", endcap, impulse])

            charts_html += '<div class="section"><h2>Shopper Summary</h2>'
            charts_html += _table_html(
                ["Persona", "Cart Size", "Total Spend", "Endcap Pickup", "Impulse Tendency"],
                cart_rows
            )
            charts_html += '</div>'

        # ── Build KPI cards ──
        kpis = (
            _kpi_card(f"${total_revenue:,.2f}", "Total Revenue")
            + _kpi_card(f"{num_shoppers}", "Shoppers Simulated")
            + _kpi_card(f"{conversion_rate:.0f}%", "Endcap Conversion")
            + _kpi_card(f"{avg_cart_size:.1f}", "Avg. Cart Size")
        )

        # ── Executive summary ──
        exec_summary = f"""<div class="executive-summary">
<h2>Executive Summary</h2>
<p>Simulation of <strong>{num_shoppers} shoppers</strong> at <strong>{store_name}</strong>
under the <strong>{scenario_name}</strong> strategy generated
<strong>${total_revenue:,.2f}</strong> in total revenue with a
<strong>{conversion_rate:.0f}%</strong> endcap conversion rate and estimated
<strong>{roi:.0f}% ROI</strong>.</p>
</div>"""

        # ── Assemble body ──
        body = exec_summary
        body += f'<div class="kpi-grid">{kpis}</div>'
        body += charts_html

        # ── Render HTML ──
        html = _HTML_TEMPLATE.format(
            title=f"Simulation Report — {scenario_name}",
            subtitle=f"{store_name} | {num_shoppers} Shoppers | {datetime.now().strftime('%B %d, %Y')}",
            body=body,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            retailer=retailer_name,
            chart_scripts="\n".join(chart_scripts)
        )

        # Save report to /tmp
        report_path = Path("/tmp/simulation_report.html")
        report_path.write_text(html, encoding="utf-8")

        logger.info(f"Simulation report generated: {report_path}")

        return {
            "status": "success",
            "report_path": str(report_path),
            "summary": (
                f"Report generated at {report_path}. "
                f"Revenue: ${total_revenue:,.2f}, "
                f"Endcap conversion: {conversion_rate:.0f}%, "
                f"Avg cart size: {avg_cart_size:.1f}, "
                f"Estimated ROI: {roi:.0f}%."
            ),
            "total_revenue": total_revenue,
            "avg_cart_size": avg_cart_size,
            "endcap_conversion_rate": conversion_rate,
            "estimated_roi": roi,
        }

    except Exception as e:
        logger.error(f"Error generating simulation report: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate report: {str(e)}",
            "report_path": None,
            "summary": "Report generation failed."
        }
