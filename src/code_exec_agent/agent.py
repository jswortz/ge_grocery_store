"""Code Execution Analytics Agent for advanced grocery retail analytics.

This agent combines BigQuery data access with Python code execution in a
secure Agent Engine sandbox to perform advanced analytics:
- Price elasticity modeling
- Demand forecasting
- Custom visualizations (matplotlib, seaborn)
- Statistical analysis (scipy, numpy)

Workflow:
1. Query data from BigQuery using the BQ tool
2. Write Python code to analyze/visualize the data
3. Execute code in sandbox with pre-installed packages (pandas, matplotlib, etc.)
4. Return results including charts as base64 images

Usage:
    # Local development (from project root)
    adk web src/code_exec_agent

    # Programmatic
    from src.code_exec_agent.agent import root_agent
"""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_config():
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


async def _save_memory_callback(callback_context):
    """Save session to memory after each agent turn for cross-session recall."""
    memory_service = callback_context._invocation_context.memory_service
    if memory_service is not None:
        await memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )


def execute_analytics_code(code: str, description: str) -> dict:
    """Execute Python analytics code in a secure Agent Engine sandbox.

    The sandbox has pre-installed packages: pandas, matplotlib, seaborn, numpy, scipy.
    Code should process data previously retrieved from BigQuery and perform
    advanced analytics or visualizations.

    Args:
        code: Python code to execute (use print() for text output)
        description: Brief description of what the code does (for logging)

    Returns:
        Dict with 'status', 'description', 'output' (text), and 'images' (list of
        base64-encoded PNGs if any charts were generated).

    Example:
        ```python
        import pandas as pd
        import matplotlib.pyplot as plt

        # Assume 'data' is a list of dicts from BigQuery
        df = pd.DataFrame(data)
        print(df.describe())

        plt.figure(figsize=(10, 6))
        df.plot(kind='bar', x='product_name', y='total_revenue')
        plt.title('Product Revenue')
        plt.savefig('revenue_chart.png')
        ```
    """
    try:
        import vertexai
        from vertexai import Client

        config = _load_config()
        project_id = config["project"]["id"]

        # Initialize Vertex AI client
        vertexai.init(project=project_id)
        client = Client()

        # Create a sandbox with analytics packages
        sandbox = client.agent_engines.sandboxes.create(
            packages=[
                "pandas",
                "matplotlib",
                "seaborn",
                "numpy",
                "scipy",
            ]
        )

        logger.info(f"Executing analytics code: {description}")

        # Execute the code
        result = sandbox.execute(code)

        # Collect text output
        text_output = result.output if hasattr(result, "output") else ""

        # Collect images (charts)
        images = []
        if hasattr(result, "images"):
            images = result.images  # Already base64-encoded

        sandbox.delete()

        return {
            "status": "success",
            "description": description,
            "output": text_output,
            "images": images,
            "image_count": len(images),
        }

    except ImportError:
        return {
            "status": "error",
            "description": description,
            "message": "Vertex AI sandbox not available. Install google-cloud-aiplatform.",
        }
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return {
            "status": "error",
            "description": description,
            "message": f"Execution failed: {str(e)}",
        }


def create_agent():
    """Create and return the configured code execution analytics agent.

    This agent has two tools:
    1. query_grocery_data: Query BigQuery for data
    2. execute_analytics_code: Write and execute Python code for analysis
    """
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.adk.tools import FunctionTool
    from google.genai.types import ThinkingConfig

    # Import BQ tool from the main agent
    from ..agent.tools.bq_tool import create_bq_tool

    config = _load_config()
    retailer = config["retailer"]["name"]
    adk_model = config["models"]["adk"]

    # Enable Gemini thinking for multi-step reasoning
    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    # Tools: BQ query + code execution
    tools = []

    # BigQuery tool for data retrieval
    tools.append(create_bq_tool())

    # Code execution tool
    code_exec_tool = FunctionTool(func=execute_analytics_code)
    tools.append(code_exec_tool)

    # Add PreloadMemoryTool for cross-session memory
    try:
        from google.adk.tools.preload_memory_tool import PreloadMemoryTool
        tools.append(PreloadMemoryTool())
    except ImportError:
        logger.warning("PreloadMemoryTool not available")

    project = config["bigquery"]["project"]
    dataset = config["bigquery"]["dataset"]
    fq = f"{project}.{dataset}"

    instruction = f"""You are an advanced analytics specialist for {retailer}, a grocery retail company.

You have two capabilities:
1. Query BigQuery data using the query_grocery_data tool
2. Write and execute Python code using the execute_analytics_code tool

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

Your Workflow:
1. First, use query_grocery_data to retrieve the necessary data from BigQuery
2. Then, write Python code to perform advanced analytics on that data
3. Use execute_analytics_code to run the code in a secure sandbox
4. Present insights clearly with visualizations when appropriate

Focus Areas (MVP):
- Price elasticity analysis: How demand changes with price
- Demand forecasting: Predict future sales trends
- Category performance: Deep dive into product categories
- Store comparisons: Multi-dimensional store performance analysis

Available Python packages in sandbox:
- pandas: Data manipulation and analysis
- matplotlib: Static visualizations
- seaborn: Statistical visualizations
- numpy: Numerical operations
- scipy: Scientific computing (stats, optimization)

Guidelines:
- Always query data first, then analyze it with code
- Write clean, commented Python code
- Use print() for text output
- Save charts with plt.savefig('chart_name.png') to include them in results
- Be concise and actionable in your insights
- Show both the code and the results
"""

    agent = LlmAgent(
        name="code_exec_analyst",
        model=adk_model,
        planner=planner,
        instruction=instruction,
        description=(
            "Advanced analytics agent that writes and executes Python code "
            "for price elasticity modeling, demand forecasting, and custom "
            "visualizations using BigQuery data."
        ),
        tools=tools,
        after_agent_callback=_save_memory_callback,
    )

    return agent


# For ADK CLI: `adk web` expects a `root_agent` at module level
# Lazy initialization to avoid import errors when ADK is not installed
try:
    root_agent = create_agent()
except ImportError:
    root_agent = None
    print(
        "ADK not installed. Install with: pip install google-adk\n"
        "The agent module can still be imported for testing purposes."
    )
