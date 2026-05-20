"""Voice BIDI Agent — passthrough for operations and supply chain insights.

A lightweight orchestrator agent designed for bidirectional voice streaming
via Agent Engine BIDI. It delegates to an operations sub-agent that provides
supply chain, inventory, staffing, and store operations intelligence by
querying BigQuery.

Usage:
    # Local development (from project root)
    adk web src/voice_bidi_agent

    # Programmatic
    from src.voice_bidi_agent.agent import root_agent
"""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_config():
    """Load config from settings.yaml, with env var overrides."""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

    if os.environ.get("RETAILER_NAME"):
        config.setdefault("retailer", {})["name"] = os.environ["RETAILER_NAME"]
    if os.environ.get("BQ_PROJECT"):
        config.setdefault("bigquery", {})["project"] = os.environ["BQ_PROJECT"]
    if os.environ.get("BQ_DATASET"):
        config.setdefault("bigquery", {})["dataset"] = os.environ["BQ_DATASET"]
    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]

    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-3.5-flash")
    config["models"].setdefault("adk_fast", "gemini-3.5-flash")
    config["models"].setdefault("live", "gemini-2.0-flash-live-001")

    return config


def _query_operations_data(query_type: str, limit: int = 10) -> dict:
    """Query BigQuery for operations and supply chain data.

    Args:
        query_type: Type of operations query — one of:
            staffing_levels, store_hours_traffic, inventory_turnover,
            department_performance, employee_schedule, supply_chain_summary,
            shrinkage_report, labor_cost_analysis
        limit: Max rows to return (default 10).

    Returns:
        Dict with status, query, and results.
    """
    config = _load_config()
    project = config["bigquery"]["project"]
    dataset = config["bigquery"]["dataset"]
    fq = f"{project}.{dataset}"

    sql_patterns = {
        "staffing_levels": f"""
            SELECT s.store_name, e.role,
                   COUNT(*) AS headcount,
                   MIN(e.hire_date) AS earliest_hire,
                   MAX(e.hire_date) AS latest_hire
            FROM `{fq}.dim_employee` e
            JOIN `{fq}.dim_store` s ON e.store_id = s.store_id
            GROUP BY s.store_name, e.role
            ORDER BY s.store_name, headcount DESC
        """,
        "store_hours_traffic": f"""
            SELECT s.store_name, s.city,
                   EXTRACT(HOUR FROM t.transaction_ts) AS hour_of_day,
                   COUNT(*) AS transaction_count,
                   SUM(t.total_amount) AS hourly_revenue
            FROM `{fq}.fact_transactions` t
            JOIN `{fq}.dim_store` s ON t.store_id = s.store_id
            GROUP BY s.store_name, s.city, hour_of_day
            ORDER BY s.store_name, hour_of_day
        """,
        "inventory_turnover": f"""
            SELECT p.category, p.product_name,
                   SUM(t.quantity) AS total_units_sold,
                   COUNT(DISTINCT DATE(t.transaction_ts)) AS active_days,
                   ROUND(SUM(t.quantity) / COUNT(DISTINCT DATE(t.transaction_ts)), 2) AS daily_velocity
            FROM `{fq}.fact_transactions` t
            JOIN `{fq}.dim_product` p ON t.product_id = p.product_id
            GROUP BY p.category, p.product_name
            ORDER BY daily_velocity DESC
            LIMIT {limit}
        """,
        "department_performance": f"""
            SELECT p.category AS department,
                   COUNT(*) AS transactions,
                   SUM(t.total_amount) AS revenue,
                   SUM(t.quantity) AS units_sold,
                   ROUND(AVG(t.total_amount), 2) AS avg_basket,
                   ROUND(SUM(t.total_amount - (t.quantity * p.unit_cost)), 2) AS gross_margin
            FROM `{fq}.fact_transactions` t
            JOIN `{fq}.dim_product` p ON t.product_id = p.product_id
            GROUP BY department
            ORDER BY revenue DESC
        """,
        "employee_schedule": f"""
            SELECT e.first_name, e.last_name, e.role,
                   s.store_name,
                   COUNT(t.transaction_id) AS transactions_processed,
                   MIN(t.transaction_ts) AS first_transaction,
                   MAX(t.transaction_ts) AS last_transaction,
                   ROUND(SUM(t.total_amount), 2) AS total_revenue
            FROM `{fq}.dim_employee` e
            JOIN `{fq}.dim_store` s ON e.store_id = s.store_id
            LEFT JOIN `{fq}.fact_transactions` t ON e.employee_id = t.employee_id
            GROUP BY e.first_name, e.last_name, e.role, s.store_name
            ORDER BY total_revenue DESC
            LIMIT {limit}
        """,
        "supply_chain_summary": f"""
            SELECT p.category,
                   COUNT(DISTINCT p.product_id) AS sku_count,
                   COUNT(DISTINCT p.brand) AS brand_count,
                   ROUND(AVG(p.unit_price), 2) AS avg_price,
                   ROUND(AVG(p.unit_cost), 2) AS avg_cost,
                   ROUND(AVG((p.unit_price - p.unit_cost) / p.unit_price * 100), 1) AS avg_margin_pct
            FROM `{fq}.dim_product` p
            GROUP BY p.category
            ORDER BY sku_count DESC
        """,
        "shrinkage_report": f"""
            SELECT s.store_name, p.category,
                   SUM(t.quantity) AS units_sold,
                   ROUND(SUM(t.total_amount), 2) AS revenue,
                   ROUND(SUM(t.quantity * p.unit_cost), 2) AS cogs,
                   ROUND(SUM(t.total_amount) - SUM(t.quantity * p.unit_cost), 2) AS gross_profit,
                   ROUND((SUM(t.total_amount) - SUM(t.quantity * p.unit_cost))
                         / SUM(t.total_amount) * 100, 1) AS margin_pct
            FROM `{fq}.fact_transactions` t
            JOIN `{fq}.dim_product` p ON t.product_id = p.product_id
            JOIN `{fq}.dim_store` s ON t.store_id = s.store_id
            GROUP BY s.store_name, p.category
            ORDER BY s.store_name, revenue DESC
        """,
        "labor_cost_analysis": f"""
            SELECT s.store_name, e.role,
                   COUNT(DISTINCT e.employee_id) AS staff_count,
                   COUNT(t.transaction_id) AS total_transactions,
                   ROUND(COUNT(t.transaction_id) * 1.0
                         / NULLIF(COUNT(DISTINCT e.employee_id), 0), 1) AS txn_per_employee,
                   ROUND(SUM(t.total_amount)
                         / NULLIF(COUNT(DISTINCT e.employee_id), 0), 2) AS revenue_per_employee
            FROM `{fq}.dim_employee` e
            JOIN `{fq}.dim_store` s ON e.store_id = s.store_id
            LEFT JOIN `{fq}.fact_transactions` t ON e.employee_id = t.employee_id
            GROUP BY s.store_name, e.role
            ORDER BY s.store_name, revenue_per_employee DESC
        """,
    }

    sql = sql_patterns.get(query_type)
    if not sql:
        return {
            "status": "error",
            "message": f"Unknown query_type: {query_type}. "
                       f"Available: {list(sql_patterns.keys())}",
        }

    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=project)
        rows = list(client.query(sql).result())
        results = []
        for row in rows[:20]:
            clean = {}
            for k, v in row.items():
                if hasattr(v, "as_integer_ratio"):
                    clean[k] = float(v)
                elif hasattr(v, "isoformat"):
                    clean[k] = v.isoformat()
                else:
                    clean[k] = v
            results.append(clean)
        return {
            "status": "success",
            "query_type": query_type,
            "query": sql.strip(),
            "results": results,
            "row_count": len(results),
        }
    except Exception as e:
        return {"status": "error", "query_type": query_type, "message": str(e)}


def create_agent():
    """Create the voice BIDI passthrough agent with operations sub-agent."""
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool

    config = _load_config()
    retailer = config["retailer"]["name"]
    # Use the Live API model for all agents in the voice pipeline.
    # The Live API requires all agents (root + sub-agents) to use a
    # Live API-compatible model since run_live() streams through them.
    live_model = config["models"].get("live", "gemini-2.0-flash-live-001")

    ops_tool = FunctionTool(func=_query_operations_data)

    # Operations sub-agent with BQ access (also uses Live API model)
    operations_agent = LlmAgent(
        name="operations_analyst",
        model=live_model,
        instruction=f"""You are the operations and supply chain analyst for {retailer}.
You provide real-time insights on store operations, staffing, inventory,
and supply chain performance using BigQuery data.

Use the _query_operations_data tool with these query types:
- staffing_levels: Current headcount by store and role
- store_hours_traffic: Transaction volume by hour for each store
- inventory_turnover: Product velocity and daily sales rates
- department_performance: Revenue, margin, and units by department
- employee_schedule: Employee activity and transaction processing
- supply_chain_summary: SKU counts, brand diversity, and margins by category
- shrinkage_report: Store-category level profitability analysis
- labor_cost_analysis: Revenue and transactions per employee by role

When answering:
- Be conversational and concise — this is a voice interface
- Lead with the key insight, then provide supporting data
- Round numbers for easy listening (say "about twelve hundred" not "1,247")
- Offer follow-up suggestions
""",
        description=(
            "Operations analyst providing staffing, inventory, supply chain, "
            "and store performance insights from BigQuery."
        ),
        tools=[ops_tool],
    )

    # Root passthrough agent — uses the Live API model for BIDI streaming
    root = LlmAgent(
        name="voice_operations_assistant",
        model=live_model,
        instruction=f"""You are the voice-activated operations assistant for {retailer}.
You help store managers, regional directors, and operations staff with
real-time insights about store operations, supply chain, and staffing.

You delegate all data queries to your operations_analyst sub-agent.

Your communication style:
- Speak naturally and conversationally — you are a voice interface
- Keep responses concise (2-3 sentences for simple questions)
- Use approximate numbers for easy listening
- Proactively suggest related insights
- Start with a brief greeting when the conversation begins

Topics you cover:
- Staffing levels and labor efficiency
- Store traffic patterns and peak hours
- Inventory velocity and turnover
- Department and category performance
- Supply chain margins and costs
- Employee productivity metrics

If asked about topics outside operations (marketing, brand guidelines,
product images), let the user know you specialize in operations and
suggest they use the main assistant for those topics.
""",
        description=(
            "Voice-activated passthrough agent for operations and supply "
            "chain insights, delegating to an analytics sub-agent."
        ),
        sub_agents=[operations_agent],
    )

    return root


# For ADK CLI: `adk web` expects a `root_agent` at module level
try:
    root_agent = create_agent()
except ImportError:
    root_agent = None
    print(
        "ADK not installed. Install with: pip install google-adk\n"
        "The agent module can still be imported for testing purposes."
    )
