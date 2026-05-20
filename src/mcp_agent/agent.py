"""MCP-based ADK agent for grocery retail analytics.

Uses the MCP Toolbox for Databases (googleapis/genai-toolbox) with the
prebuilt BigQuery configuration to provide natural language querying of
the grocery retail star schema. This replaces the manual SQL pattern
matching in src/agent/tools/bq_tool.py with a proper MCP integration
that lets the LLM generate arbitrary SQL through the toolbox.

Architecture:
    ADK Agent  --(MCP stdio)-->  genai-toolbox  --(BigQuery API)-->  BQ

The genai-toolbox binary runs as a subprocess and exposes BigQuery tools
via the Model Context Protocol (MCP) over stdio. The ADK agent connects
to it using McpToolset with StdioServerParameters.

Prebuilt BigQuery tools available via the toolbox:
    - execute_sql: Run arbitrary SQL queries
    - list_table_ids: List tables in a dataset
    - get_table_info: Get table schema/metadata
    - get_dataset_info: Get dataset metadata
    - list_dataset_ids: List datasets in a project
    - search_catalog: Search for tables, views, models
    - ask_data_insights: AI-powered data analysis
    - forecast: Time series forecasting
    - analyze_contribution: Metric contribution analysis

Usage:
    # First, download the toolbox binary:
    # export VERSION=0.27.0
    # curl -L -o toolbox \\
    #   https://storage.googleapis.com/genai-toolbox/v$VERSION/linux/amd64/toolbox
    # chmod +x toolbox

    # Then run the agent:
    # adk web src/mcp_agent

    # Or programmatically:
    from src.mcp_agent.agent import root_agent
"""

import os
import shutil
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"

# Default toolbox binary name — can be overridden via TOOLBOX_PATH env var
_TOOLBOX_BINARY = "toolbox"


def _load_config() -> dict:
    """Load config from settings.yaml, with env var overrides for deployment."""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

    # Allow env var overrides for Agent Engine deployment
    if os.environ.get("RETAILER_NAME"):
        config.setdefault("retailer", {})["name"] = os.environ["RETAILER_NAME"]
    if os.environ.get("PROJECT_ID"):
        config.setdefault("project", {})["id"] = os.environ["PROJECT_ID"]
    if os.environ.get("BQ_PROJECT"):
        config.setdefault("bigquery", {})["project"] = os.environ["BQ_PROJECT"]
    if os.environ.get("BQ_DATASET"):
        config.setdefault("bigquery", {})["dataset"] = os.environ["BQ_DATASET"]
    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]

    # Defaults for models if not set
    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-3.5-flash")

    return config


def _resolve_toolbox_path() -> str:
    """Resolve the path to the genai-toolbox binary.

    Checks in order:
    1. TOOLBOX_PATH environment variable
    2. ./toolbox in the project root
    3. toolbox on the system PATH
    """
    # Check env var first
    env_path = os.environ.get("TOOLBOX_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check project root
    project_root = Path(__file__).resolve().parent.parent.parent
    local_path = project_root / _TOOLBOX_BINARY
    if local_path.is_file():
        return str(local_path)

    # Check system PATH
    system_path = shutil.which(_TOOLBOX_BINARY)
    if system_path:
        return system_path

    return _TOOLBOX_BINARY  # Fall back; will fail at runtime with a clear error


def _get_schema_context(config: dict) -> str:
    """Build schema context string for the agent instruction.

    Provides the LLM with full schema knowledge so it can generate
    accurate SQL queries via the MCP execute_sql tool.
    """
    project = config["bigquery"]["project"]
    dataset = config["bigquery"]["dataset"]
    fq = f"{project}.{dataset}"

    return f"""
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

Key Relationships:
- fact_transactions.store_id -> dim_store.store_id
- fact_transactions.product_id -> dim_product.product_id
- fact_transactions.employee_id -> dim_employee.employee_id
- fact_transactions.customer_id -> dim_customer.customer_id
- dim_employee.store_id -> dim_store.store_id
- dim_customer.home_store_id -> dim_store.store_id
"""


def _get_a2ui_suffix() -> str:
    """Generate A2UI-first schema instructions for analytics output."""
    try:
        from a2ui.schema.manager import A2uiSchemaManager
        from a2ui.basic_catalog.provider import BasicCatalog

        schema_manager = A2uiSchemaManager(
            version='0.8',
            catalogs=[BasicCatalog.get_config('0.8')],
        )
        base = schema_manager.generate_system_prompt(
            role_description="UI-first grocery retail data analytics dashboard",
            ui_description=(
                "This agent is a VISUAL DASHBOARD that renders all analytics as rich "
                "UI surfaces. Every response MUST lead with an <a2ui-json> block. "
                "Use Row of Cards for KPI metrics, List for ranked items, "
                "Icon for visual badges, Divider between sections, and Text with "
                "bold metrics and emoji indicators. NEVER use markdown tables or "
                "plain lists — use Card grids and List components instead."
            ),
            include_schema=True,
            include_examples=True,
        )
        example = '''

⚠️ A2UI-FIRST OUTPUT RULES:
- FIRST output <a2ui-json>, THEN at most 1-2 sentences of context.
- NEVER use markdown tables or bullet lists — use Row + Card or List + Card.
- Use Icon for badges, Divider between sections, minimum 4 component types.

<a2ui-json>
[
  {"beginRendering": {"surfaceId": "analytics", "root": "root"}},
  {"surfaceUpdate": {"surfaceId": "analytics", "components": [
    {"id": "root", "component": {"Column": {"children": {"explicitList": ["hdr", "metrics", "divider", "detail"]}}}},
    {"id": "hdr", "component": {"Row": {"children": {"explicitList": ["hdr-icon", "hdr-txt"]}, "alignment": "center"}}},
    {"id": "hdr-icon", "component": {"Icon": {"name": {"literalString": "star"}}}},
    {"id": "hdr-txt", "component": {"Text": {"text": {"literalString": "**Store Revenue Comparison**"}, "usageHint": "h2"}}},
    {"id": "metrics", "component": {"Row": {"children": {"explicitList": ["card1", "card2"]}}}},
    {"id": "card1", "component": {"Card": {"child": "t1"}}},
    {"id": "t1", "component": {"Text": {"text": {"literalString": "🏪 **Downtown Market**\\n\\n💰 **$45,231** revenue\\n🛒 **1,234** transactions\\n📊 Avg basket **$36.69**"}}}},
    {"id": "card2", "component": {"Card": {"child": "t2"}}},
    {"id": "t2", "component": {"Text": {"text": {"literalString": "🏪 **Westside Market**\\n\\n💰 **$38,102** revenue\\n🛒 **987** transactions\\n📊 Avg basket **$38.60**"}}}},
    {"id": "divider", "component": {"Divider": {"axis": "horizontal"}}},
    {"id": "detail", "component": {"Card": {"child": "detail-t"}}},
    {"id": "detail-t", "component": {"Text": {"text": {"literalString": "📈 Downtown leads by **$7,129** (+18.7%) · Higher transaction volume but lower basket size"}}}}
  ]}}
]
</a2ui-json>

CHART COMPONENTS (render native Chart.js visualizations):
- BarChart: {"id": "chart1", "component": {"BarChart": {"title": "Revenue by Store", "labels": ["Downtown","Westside","Eastgate"], "datasets": [{"label": "Revenue", "data": [45231,38102,29847], "color": "#2e7d32"}]}}}
- LineChart: same props as BarChart, renders as line graph (good for time series)
- PieChart: same props, renders as pie/donut chart (good for category breakdowns)
When results have categories + numeric values, prefer BarChart/LineChart/PieChart over Text-only Cards.

STRICT RULES:
- Wrap A2UI JSON in <a2ui-json> and </a2ui-json> tags.
- Always start with beginRendering, then surfaceUpdate.
- Use flat component arrays with string ID refs in children.explicitList.
- Card uses "child" (singular). Text.text uses {"literalString": "..."}.
- Use Icon, Divider, and at least 4 component types per response.
'''
        result = base + example
        try:
            from src.shared.a2ui_skills import load_a2ui_skills
            skills = load_a2ui_skills()
            if skills:
                result += skills
        except ImportError:
            pass
        return result
    except ImportError:
        return ""


def _get_agent_instruction(config: dict) -> str:
    """Build the agent instruction with retailer name and schema context."""
    retailer = config["retailer"]["name"]
    schema = _get_schema_context(config)

    base = f"""You are a data analytics assistant for {retailer}, a grocery retail company.
You answer natural language questions about sales, products, stores, customers,
and employees by querying BigQuery through the MCP tools available to you.

{schema}

Guidelines:
- Use the execute_sql tool to run BigQuery SQL queries against the dataset above.
- Use list_table_ids or get_table_info to explore the schema if needed.
- Always use fully qualified table names (project.dataset.table).
- Write read-only SELECT queries. Never modify data.
- Limit results to 20 rows unless the user asks for more.
- Present results clearly with specific numbers and context.
- If you are unsure about the schema, use get_table_info to inspect it.
- For complex analytics questions, break them into steps.
- When citing data, reference the specific tables and columns used.
- Be concise and actionable in your responses.
- When results have categories + numeric values, use BarChart or PieChart A2UI components.
- For time series data, use LineChart with date labels.
- Always present KPI summaries as a Row of Cards before any chart.
- IMPORTANT: Always show the SQL query you executed in a ```sql code block before presenting results. This helps users understand and verify the analysis.
"""
    a2ui_suffix = _get_a2ui_suffix()
    if a2ui_suffix:
        base += "\n\n" + a2ui_suffix
    return base


def get_mcp_toolset():
    """Create the MCP toolset for BigQuery via genai-toolbox.

    Uses StdioServerParameters to launch the genai-toolbox binary as a
    subprocess with the --prebuilt bigquery flag, which exposes all
    BigQuery tools (execute_sql, list_table_ids, get_table_info, etc.)
    via MCP over stdio.

    Returns:
        McpToolset configured to connect to the BigQuery toolbox.
    """
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
    from mcp import StdioServerParameters

    config = _load_config()
    project_id = config["bigquery"]["project"]
    toolbox_path = _resolve_toolbox_path()

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=toolbox_path,
                args=[
                    "--prebuilt", "bigquery",
                    "--stdio",
                ],
                env={
                    **os.environ,
                    "BIGQUERY_PROJECT": project_id,
                },
            ),
            timeout=30.0,
        ),
        # Expose all BigQuery tools; can filter if needed:
        # tool_filter=["execute_sql", "list_table_ids", "get_table_info"],
    )


def create_agent():
    """Create and return the MCP-based grocery analytics agent.

    This agent uses McpToolset to connect to the genai-toolbox binary
    running in prebuilt BigQuery mode. The toolbox manages the BigQuery
    connection and exposes SQL execution plus metadata tools via MCP.
    """
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.genai.types import ThinkingConfig

    config = _load_config()
    adk_model = config["models"]["adk"]

    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    mcp_toolset = get_mcp_toolset()

    agent = LlmAgent(
        name="mcp_grocery_analyst",
        model=adk_model,
        planner=planner,
        instruction=_get_agent_instruction(config),
        description=(
            "AI analytics assistant for grocery retail that uses MCP Toolbox "
            "for BigQuery to answer natural language questions about sales, "
            "products, stores, customers, and employees."
        ),
        tools=[mcp_toolset],
    )

    return agent


# For ADK CLI: `adk web` expects a `root_agent` at module level
# Lazy initialization to avoid import errors when ADK/MCP is not installed
try:
    root_agent = create_agent()
except ImportError as e:
    root_agent = None
    print(
        f"MCP agent dependencies not installed: {e}\n"
        "Install with: pip install google-adk mcp\n"
        "Also ensure the genai-toolbox binary is available.\n"
        "The agent module can still be imported for testing purposes."
    )
except Exception as e:
    root_agent = None
    print(
        f"Warning: Could not create MCP agent: {e}\n"
        "The agent module can still be imported for testing purposes."
    )
