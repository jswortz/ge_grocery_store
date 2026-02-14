"""Deploy the MCP BigQuery agent to Vertex AI Agent Engine.

The MCP agent uses genai-toolbox for BigQuery access. Since the toolbox
binary cannot be packaged with Agent Engine, this deployment script
creates a version of the agent that uses the BigQuery MCP tools available
directly through the google-adk BigQuery prebuilt tools instead.

Usage:
    python -m src.mcp_agent.deploy_to_agent_engine

Note: The MCP agent in Agent Engine will use the same BigQuery tools
(execute_sql, list_table_ids, etc.) but routed through Agent Engine's
built-in MCP support rather than a local genai-toolbox subprocess.
"""

import os
import sys

import vertexai
from vertexai import agent_engines

# Add parent dirs to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_agent.agent import _load_config, _get_agent_instruction


PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://wortz-project-352116-ge-workshop"


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

    print("=" * 80)
    print("DEPLOYING MCP BIGQUERY AGENT TO AGENT ENGINE")
    print("=" * 80)

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    config = _load_config()
    adk_model = config["models"]["adk"]

    # Create the agent with the same instruction but without the MCP toolset
    # (Agent Engine provides BigQuery tools via its own MCP integration)
    agent = LlmAgent(
        name="mcp_grocery_analyst",
        model=adk_model,
        instruction=_get_agent_instruction(config),
        description=(
            "AI analytics assistant for grocery retail that uses BigQuery "
            "tools to answer natural language questions about sales, "
            "products, stores, customers, and employees."
        ),
    )

    display_name = "MCP Grocery Analyst"

    app = agent_engines.AdkApp(
        agent=agent,
        app_name="mcp_grocery_analyst_app",
        enable_tracing=True,
    )

    existing = find_agent_by_display_name(display_name)

    if existing:
        print(f"Found existing deployment: {existing}")
        print("Updating...")
        agent_engines.update(
            agent_engine=app,
            resource_name=existing,
            requirements=os.path.join(
                os.path.dirname(__file__), "requirements.txt"
            ),
            extra_packages=[os.path.dirname(__file__)],
        )
        print(f"Updated: {existing}")
        return existing
    else:
        print("Creating new deployment...")
        remote_app = agent_engines.create(
            agent_engine=app,
            display_name=display_name,
            requirements=os.path.join(
                os.path.dirname(__file__), "requirements.txt"
            ),
            extra_packages=[os.path.dirname(__file__)],
        )
        print(f"Deployed: {remote_app.resource_name}")
        return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy_mcp_agent()
    print(f"\nMCP Agent deployed: {resource_name}")
