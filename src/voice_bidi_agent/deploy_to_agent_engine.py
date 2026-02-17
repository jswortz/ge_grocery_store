"""Deploy the Voice BIDI Operations agent to Vertex AI Agent Engine.

Self-contained deployment script for the voice operations agent.

Usage:
    cd src && python -m voice_bidi_agent.deploy_to_agent_engine
"""

import logging
import os

import vertexai
from vertexai import agent_engines

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "wortz-project-352116")
LOCATION = os.environ.get("AE_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://wortz-project-352116-ge-workshop")

_BQ_PROJECT = os.environ.get("BQ_PROJECT", "wortz-project-352116")
_BQ_DATASET = os.environ.get("BQ_DATASET", "ge_grocery_demo")
_RETAILER_NAME = os.environ.get("RETAILER_NAME", "ValueFresh Market")
_ADK_MODEL = os.environ.get("ADK_MODEL", "gemini-3-pro-preview")
_ADK_FAST = os.environ.get("ADK_FAST", "gemini-3-flash-preview")


def find_agent_by_display_name(display_name: str) -> str:
    """Find reasoning engine by display name."""
    agent_filter_query = f'display_name="{display_name}"'
    agent_list = agent_engines.list(filter=agent_filter_query)
    for deployed_agent in agent_list:
        return deployed_agent.resource_name
    return ""


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
    project = os.environ.get("BQ_PROJECT", _BQ_PROJECT)
    dataset = os.environ.get("BQ_DATASET", _BQ_DATASET)
    fq = f"{project}.{dataset}"

    sql_patterns = {
        "staffing_levels": f"""
            SELECT s.store_name, e.role,
                   COUNT(*) AS headcount
            FROM `{fq}.dim_employee` e
            JOIN `{fq}.dim_store` s ON e.store_id = s.store_id
            GROUP BY s.store_name, e.role
            ORDER BY s.store_name, headcount DESC
        """,
        "store_hours_traffic": f"""
            SELECT s.store_name,
                   EXTRACT(HOUR FROM t.transaction_ts) AS hour_of_day,
                   COUNT(*) AS transaction_count,
                   SUM(t.total_amount) AS hourly_revenue
            FROM `{fq}.fact_transactions` t
            JOIN `{fq}.dim_store` s ON t.store_id = s.store_id
            GROUP BY s.store_name, hour_of_day
            ORDER BY s.store_name, hour_of_day
        """,
        "inventory_turnover": f"""
            SELECT p.category, p.product_name,
                   SUM(t.quantity) AS total_units_sold,
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
                   ROUND(SUM(t.total_amount - (t.quantity * p.unit_cost)), 2) AS gross_margin
            FROM `{fq}.fact_transactions` t
            JOIN `{fq}.dim_product` p ON t.product_id = p.product_id
            GROUP BY department
            ORDER BY revenue DESC
        """,
        "employee_schedule": f"""
            SELECT e.first_name, e.last_name, e.role, s.store_name,
                   COUNT(t.transaction_id) AS transactions_processed,
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
                   ROUND(AVG(p.unit_price), 2) AS avg_price,
                   ROUND(AVG(p.unit_cost), 2) AS avg_cost,
                   ROUND(AVG((p.unit_price - p.unit_cost) / p.unit_price * 100), 1) AS avg_margin_pct
            FROM `{fq}.dim_product` p
            GROUP BY p.category
            ORDER BY sku_count DESC
        """,
        "shrinkage_report": f"""
            SELECT s.store_name, p.category,
                   ROUND(SUM(t.total_amount), 2) AS revenue,
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
            "results": results,
            "row_count": len(results),
        }
    except Exception as e:
        return {"status": "error", "query_type": query_type, "message": str(e)}


def deploy():
    """Deploy the voice operations agent to Agent Engine."""
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool

    print("=" * 80)
    print("DEPLOYING VOICE OPERATIONS AGENT TO AGENT ENGINE")
    print("=" * 80)

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    ops_tool = FunctionTool(func=_query_operations_data)

    operations_agent = LlmAgent(
        name="operations_analyst",
        model=_ADK_FAST,
        instruction=f"""You are the operations and supply chain analyst for {_RETAILER_NAME}.
You provide real-time insights on store operations, staffing, inventory,
and supply chain performance using BigQuery data.

Use the _query_operations_data tool with these query types:
- staffing_levels, store_hours_traffic, inventory_turnover,
  department_performance, employee_schedule, supply_chain_summary,
  shrinkage_report, labor_cost_analysis

Be conversational and concise — this is a voice interface.""",
        description="Operations analyst for BigQuery data.",
        tools=[ops_tool],
    )

    agent = LlmAgent(
        name="voice_operations_assistant",
        model=_ADK_MODEL,
        instruction=f"""You are the voice-activated operations assistant for {_RETAILER_NAME}.
You help store managers and operations staff with real-time insights about
store operations, supply chain, and staffing.

Delegate all data queries to your operations_analyst sub-agent.

Keep responses concise for voice — 2-3 sentences for simple questions.""",
        description="Voice passthrough for operations and supply chain insights.",
        sub_agents=[operations_agent],
    )

    display_name = "Voice Operations Agent"

    app = agent_engines.AdkApp(
        agent=agent,
        app_name="voice_operations_app",
        enable_tracing=True,
    )

    env_vars = {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        "GOOGLE_CLOUD_LOCATION": "global",  # Gemini 3 models require global endpoint
    }

    existing = find_agent_by_display_name(display_name)

    if existing:
        print(f"Deleting existing deployment: {existing}")
        agent_engines.delete(existing, force=True)
        print("  Deleted.")

    print("Creating new deployment...")
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        requirements=[
            "google-adk>=1.19.0",
            "google-cloud-bigquery>=3.0.0",
            "google-cloud-aiplatform",
            "pyyaml>=6.0",
        ],
        env_vars=env_vars,
    )
    print(f"Deployed: {remote_app.resource_name}")
    return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy()
    print(f"\nVoice Operations Agent deployed: {resource_name}")
