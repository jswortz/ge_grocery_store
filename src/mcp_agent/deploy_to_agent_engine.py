"""Deploy the MCP BigQuery agent to Vertex AI Agent Engine.

The MCP agent uses genai-toolbox for BigQuery access locally. Since the
toolbox binary cannot be packaged with Agent Engine, this deployment script
creates a self-contained version of the agent with an inline BigQuery
FunctionTool (pattern-matched SQL) that has no cross-module dependencies.

Usage:
    cd src && python -m mcp_agent.deploy_to_agent_engine
"""

import logging
import os

import vertexai
from vertexai import agent_engines

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "wortz-project-352116")
LOCATION = os.environ.get("AE_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://wortz-project-352116-ge-workshop")

# Hardcoded config for Agent Engine deployment (avoids filesystem config loading)
_DEPLOY_CONFIG = {
    "retailer": {"name": os.environ.get("RETAILER_NAME", "ValueFresh Market")},
    "bigquery": {"project": os.environ.get("BQ_PROJECT", "wortz-project-352116"), "dataset": os.environ.get("BQ_DATASET", "ge_grocery_demo")},
    "models": {"adk": "gemini-3.5-flash"},
}


# ── Self-contained BigQuery tool (no cross-module imports) ────────────────

def _generate_sql(question: str, dataset: str) -> str:
    """Generate SQL from natural language using pattern matching."""
    q = question.lower()

    if "top" in q and "product" in q:
        return f"""
            SELECT p.product_name, p.category, p.brand,
                   SUM(t.total_amount) AS total_revenue,
                   SUM(t.quantity) AS total_units
            FROM `{dataset}.fact_transactions` t
            JOIN `{dataset}.dim_product` p ON t.product_id = p.product_id
            GROUP BY p.product_name, p.category, p.brand
            ORDER BY total_revenue DESC
            LIMIT 10
        """
    if "store" in q and ("sale" in q or "revenue" in q):
        return f"""
            SELECT s.store_name, s.city,
                   SUM(t.total_amount) AS total_revenue,
                   COUNT(*) AS transaction_count,
                   ROUND(AVG(t.total_amount), 2) AS avg_transaction
            FROM `{dataset}.fact_transactions` t
            JOIN `{dataset}.dim_store` s ON t.store_id = s.store_id
            GROUP BY s.store_name, s.city
            ORDER BY total_revenue DESC
        """
    if "loyalty" in q or "tier" in q:
        return f"""
            SELECT c.loyalty_tier,
                   COUNT(DISTINCT c.customer_id) AS customer_count,
                   ROUND(AVG(c.points_balance), 0) AS avg_points,
                   SUM(t.total_amount) AS total_spend
            FROM `{dataset}.dim_customer` c
            LEFT JOIN `{dataset}.fact_transactions` t ON c.customer_id = t.customer_id
            GROUP BY c.loyalty_tier
            ORDER BY total_spend DESC
        """
    if "payment" in q:
        return f"""
            SELECT payment_method,
                   COUNT(*) AS transaction_count,
                   SUM(total_amount) AS total_revenue,
                   ROUND(AVG(total_amount), 2) AS avg_amount
            FROM `{dataset}.fact_transactions`
            GROUP BY payment_method
            ORDER BY transaction_count DESC
        """
    if "category" in q or "categories" in q:
        return f"""
            SELECT p.category,
                   COUNT(*) AS transaction_count,
                   SUM(t.total_amount) AS total_revenue,
                   SUM(t.quantity) AS total_units
            FROM `{dataset}.fact_transactions` t
            JOIN `{dataset}.dim_product` p ON t.product_id = p.product_id
            GROUP BY p.category
            ORDER BY total_revenue DESC
        """
    if "employee" in q or "associate" in q:
        return f"""
            SELECT e.first_name, e.last_name, e.role, s.store_name,
                   COUNT(t.transaction_id) AS transactions_processed,
                   SUM(t.total_amount) AS total_revenue
            FROM `{dataset}.dim_employee` e
            JOIN `{dataset}.dim_store` s ON e.store_id = s.store_id
            LEFT JOIN `{dataset}.fact_transactions` t ON e.employee_id = t.employee_id
            GROUP BY e.first_name, e.last_name, e.role, s.store_name
            ORDER BY total_revenue DESC
            LIMIT 15
        """
    # Default: summary overview
    return f"""
        SELECT
          (SELECT COUNT(*) FROM `{dataset}.fact_transactions`) AS total_transactions,
          (SELECT ROUND(SUM(total_amount), 2) FROM `{dataset}.fact_transactions`) AS total_revenue,
          (SELECT COUNT(DISTINCT product_id) FROM `{dataset}.dim_product`) AS product_count,
          (SELECT COUNT(*) FROM `{dataset}.dim_store`) AS store_count,
          (SELECT COUNT(*) FROM `{dataset}.dim_employee`) AS employee_count,
          (SELECT COUNT(*) FROM `{dataset}.dim_customer`) AS customer_count
    """


def query_grocery_data(question: str) -> dict:
    """Query the grocery retail BigQuery star schema.

    Translates a natural language question into a SQL query against the
    star schema and returns the results.

    Args:
        question: Natural language question about grocery data

    Returns:
        Dict with 'status', 'question', 'sql' (if generated), and 'results'.
    """
    project_id = os.environ.get("BQ_PROJECT", _DEPLOY_CONFIG["bigquery"]["project"])
    dataset_name = os.environ.get("BQ_DATASET", _DEPLOY_CONFIG["bigquery"]["dataset"])
    full_dataset = f"{project_id}.{dataset_name}"

    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=project_id)
        sql = _generate_sql(question, full_dataset)

        if sql:
            query_job = client.query(sql)
            rows = list(query_job.result())
            results = []
            for row in rows[:20]:
                clean_row = {}
                for k, v in row.items():
                    if hasattr(v, "as_integer_ratio"):
                        clean_row[k] = float(v)
                    elif hasattr(v, "isoformat"):
                        clean_row[k] = v.isoformat()
                    else:
                        clean_row[k] = v
                results.append(clean_row)
            return {
                "status": "success",
                "question": question,
                "sql": sql,
                "results": results,
                "row_count": len(results),
            }
        else:
            return {
                "status": "unsupported",
                "question": question,
                "message": "Could not generate SQL for this question.",
            }
    except Exception as e:
        logger.error("BigQuery query failed: %s", e)
        return {"status": "error", "question": question, "message": str(e)}


# ── Deploy logic ──────────────────────────────────────────────────────────

def find_agent_by_display_name(display_name: str) -> str:
    """Find reasoning engine by display name."""
    agent_filter_query = f'display_name="{display_name}"'
    agent_list = agent_engines.list(filter=agent_filter_query)
    for deployed_agent in agent_list:
        return deployed_agent.resource_name
    return ""


def deploy_mcp_agent():
    """Deploy the MCP BigQuery agent to Agent Engine."""
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.adk.tools import FunctionTool
    from google.genai.types import ThinkingConfig

    print("=" * 80)
    print("DEPLOYING MCP BIGQUERY AGENT TO AGENT ENGINE")
    print("=" * 80)

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    config = _DEPLOY_CONFIG
    adk_model = config["models"]["adk"]
    retailer = config["retailer"]["name"]

    project = config["bigquery"]["project"]
    dataset = config["bigquery"]["dataset"]
    fq = f"{project}.{dataset}"

    instruction = f"""You are a data analytics assistant for {retailer}, a grocery retail company.
You answer natural language questions about sales, products, stores, customers,
and employees by querying BigQuery.

BigQuery Dataset: `{fq}`

Tables and Columns:
- `{fq}.fact_transactions`
  transaction_id INT64, transaction_ts TIMESTAMP, store_id INT64,
  employee_id INT64, product_id INT64, quantity INT64,
  unit_price NUMERIC, total_amount NUMERIC, payment_method STRING,
  customer_id INT64

- `{fq}.dim_store`
  store_id INT64, store_name STRING, city STRING, state STRING,
  zip_code STRING, square_feet INT64, open_date DATE

- `{fq}.dim_product`
  product_id INT64, product_name STRING, category STRING,
  subcategory STRING, brand STRING, unit_price NUMERIC,
  unit_cost NUMERIC, image_uri STRING, description STRING

- `{fq}.dim_employee`
  employee_id INT64, first_name STRING, last_name STRING,
  role STRING, store_id INT64, hire_date DATE

- `{fq}.dim_customer`
  customer_id INT64, first_name STRING, last_name STRING,
  email STRING, phone STRING, loyalty_tier STRING,
  home_store_id INT64, signup_date DATE, points_balance INT64

Guidelines:
- Use the query_grocery_data tool to answer questions about the data.
- Present results clearly with specific numbers and context.
- Be concise and actionable in your responses.
- IMPORTANT: Always show the SQL query you executed in a ```sql code block before presenting results. This helps users understand and verify the analysis.
"""
    try:
        from a2ui.schema.manager import A2uiSchemaManager
        from a2ui.basic_catalog.provider import BasicCatalog

        schema_manager = A2uiSchemaManager(
            version='0.8',
            catalogs=[BasicCatalog.get_config('0.8')],
        )
        a2ui_suffix = schema_manager.generate_system_prompt(
            role_description="grocery retail data analytics assistant",
            ui_description=(
                "Rich visual outputs for analytics results: data tables as Card grids, "
                "store comparisons in Row layouts, loyalty tier breakdowns. "
                "Use Card for metric summaries, Row/Column for layouts, "
                "and Text for formatted data with markdown."
            ),
        )
        a2ui_suffix += '''

Here is a compact example of A2UI output for analytics results:

<a2ui-json>
[
  {"beginRendering": {"surfaceId": "analytics", "root": "root"}},
  {"surfaceUpdate": {"surfaceId": "analytics", "components": [
    {"id": "root", "component": {"Row": {"children": {"explicitList": ["card1", "card2"]}}}},
    {"id": "card1", "component": {"Card": {"title": "Downtown Market", "subtitle": "$45,231 Revenue", "children": {"explicitList": ["t1"]}}}},
    {"id": "t1", "component": {"Text": {"text": "**1,234** transactions · Avg basket **$36.69**"}}},
    {"id": "card2", "component": {"Card": {"title": "Westside Market", "subtitle": "$38,102 Revenue", "children": {"explicitList": ["t2"]}}}},
    {"id": "t2", "component": {"Text": {"text": "**987** transactions · Avg basket **$38.60**"}}}
  ]}}
]
</a2ui-json>

Rules:
- Wrap A2UI JSON arrays in <a2ui-json> and </a2ui-json> tags.
- Always start with a beginRendering message, then surfaceUpdate.
- Use flat component arrays with string ID references in children.explicitList.
- For multi-card layouts, use a Row component with cards as children.
- Include natural language text OUTSIDE the <a2ui-json> tags for context.
'''
        instruction += "\n\n" + a2ui_suffix
    except ImportError:
        pass

    bq_tool = FunctionTool(func=query_grocery_data)

    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    agent = LlmAgent(
        name="mcp_grocery_analyst",
        model=adk_model,
        planner=planner,
        instruction=instruction,
        description=(
            "AI analytics assistant for grocery retail that uses BigQuery "
            "tools to answer natural language questions about sales, "
            "products, stores, customers, and employees."
        ),
        tools=[bq_tool],
    )

    display_name = "MCP Grocery Analyst"

    app = agent_engines.AdkApp(
        agent=agent,
        app_name="mcp_grocery_analyst_app",
        enable_tracing=True,
    )

    existing = find_agent_by_display_name(display_name)

    if existing:
        print(f"Deleting existing deployment: {existing}")
        agent_engines.delete(existing, force=True)
        print("  Deleted.")

    env_vars = {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        "GOOGLE_CLOUD_LOCATION": "global",  # Gemini 3 models require global endpoint
    }

    print("Creating new deployment...")
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        requirements=[
            "google-adk>=1.19.0,<2.0.0",
            "google-cloud-bigquery>=3.0.0",
            "google-cloud-aiplatform",
            "pyyaml>=6.0",
            "a2ui-agent-sdk>=0.2.1",
        ],
        env_vars=env_vars,
    )
    print(f"Deployed: {remote_app.resource_name}")
    return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy_mcp_agent()
    print(f"\nMCP Agent deployed: {resource_name}")
