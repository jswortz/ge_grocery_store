"""A2A-enabled grocery retail agent.

Wraps the existing ADK sop_agent agent with the A2A (Agent-to-Agent)
protocol so it can be discovered and invoked by other agents. Designed for
deployment to Cloud Run.

Architecture:
    External Agent -> A2A Protocol -> Cloud Run -> ADK Agent -> GCP Services

The agent exposes an AgentCard at /.well-known/agent.json describing its
capabilities, and handles A2A task requests at the /a2a endpoint.

Usage:
    # Local development
    python -m src.a2a_agent.server

    # Deploy to Cloud Run
    gcloud run deploy grocery-a2a-agent \
      --source=. \
      --region=us-central1 \
      --project=wortz-project-352116 \
      --allow-unauthenticated
"""

import os
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_config() -> dict:
    """Load config from settings.yaml, with env var overrides."""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

    if os.environ.get("RETAILER_NAME"):
        config.setdefault("retailer", {})["name"] = os.environ["RETAILER_NAME"]
    if os.environ.get("PROJECT_ID"):
        config.setdefault("project", {})["id"] = os.environ["PROJECT_ID"]
    if os.environ.get("ENGINE_ID"):
        config.setdefault("project", {})["engine_id"] = os.environ["ENGINE_ID"]
    if os.environ.get("BQ_PROJECT"):
        config.setdefault("bigquery", {})["project"] = os.environ["BQ_PROJECT"]
    if os.environ.get("BQ_DATASET"):
        config.setdefault("bigquery", {})["dataset"] = os.environ["BQ_DATASET"]
    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]

    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-3-pro-preview")
    config["models"].setdefault("adk_fast", "gemini-3-flash-preview")

    return config


def create_agent():
    """Create the ADK agent for A2A serving.

    Returns the same sop_agent agent used in src/agent/agent.py
    but configured for A2A serving via Cloud Run.
    """
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.genai.types import ThinkingConfig

    config = _load_config()
    retailer = config["retailer"]["name"]
    adk_model = config["models"]["adk"]          # Pro for root orchestrator
    adk_fast = config["models"]["adk_fast"]      # Flash for sub-agents

    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    # Import tools from the main agent module
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from agent.tools.bq_tool import create_bq_tool
    from agent.tools.image_gen_tool import create_image_gen_tool
    from agent.tools.a2a_tool import create_a2a_tool

    root_tools = []

    # Add DiscoveryEngineSearchTool if available
    try:
        from google.adk.tools.discovery_engine_search_tool import DiscoveryEngineSearchTool
        from google.cloud import discoveryengine_v1beta as discoveryengine

        project_id = config["project"]["id"]
        engine_id = config["project"]["engine_id"]
        search_engine_id = (
            f"projects/{project_id}/locations/global/collections/"
            f"default_collection/engines/{engine_id}"
        )
        ds_base = (
            f"projects/{project_id}/locations/global/collections/"
            f"default_collection/dataStores"
        )
        root_tools.append(DiscoveryEngineSearchTool(
            search_engine_id=search_engine_id,
            data_store_specs=[
                discoveryengine.SearchRequest.DataStoreSpec(
                    data_store=f"{ds_base}/sop-store"
                ),
                discoveryengine.SearchRequest.DataStoreSpec(
                    data_store=f"{ds_base}/brand-guidelines-store"
                ),
            ],
        ))
    except Exception as e:
        print(f"Warning: Could not create search tool: {e}")

    # Add PreloadMemoryTool if available
    try:
        from google.adk.tools.preload_memory_tool import PreloadMemoryTool
        root_tools.append(PreloadMemoryTool())
    except ImportError:
        pass

    # Add simulator delegation tool (Agent Engine cross-agent call)
    try:
        root_tools.append(create_a2a_tool())
    except Exception as e:
        print(f"Warning: Could not create simulator tool: {e}")

    # Sub-agents (Flash for fast delegation)
    analytics_agent = LlmAgent(
        name="analytics_agent",
        model=adk_fast,
        planner=planner,
        instruction=(
            f"You are the data analytics specialist for {retailer}. "
            "Use the query_grocery_data tool to answer questions about sales, "
            "products, stores, customers, and employees."
        ),
        description="Answers data questions by querying BigQuery.",
        tools=[create_bq_tool()],
    )

    image_agent = LlmAgent(
        name="image_agent",
        model=adk_fast,
        planner=planner,
        instruction=(
            f"You are the product imagery specialist for {retailer}. "
            "Use the generate_product_image tool to create product photos. "
            "IMPORTANT: When the tool returns successfully, always include the "
            "markdown image from the 'message' field in your response exactly "
            "as returned (e.g., ![Product Name](/api/images/...)) so the user "
            "can see the generated image inline."
        ),
        description="Generates product images following brand guidelines.",
        tools=[create_image_gen_tool()],
    )

    agent = LlmAgent(
        name="sop_agent",
        model=adk_model,
        planner=planner,
        instruction=f"""You are an AI assistant for {retailer}, a grocery retail company.
You help associates, managers, and stakeholders with:
1. Standard Operating Procedures - Retrieve and explain SOPs
2. Brand-Compliant Marketing Content - Generate brand-aligned materials
3. Product Information & Analytics - Answer data questions using BigQuery
4. Product Image Generation - Create product imagery
5. Shopper Simulation - When users ask to simulate shopper behavior, test
   merchandising strategies, or evaluate endcap placements, use the
   delegate_to_simulator tool. Available stores: Downtown Market, Westside
   Market, Lakefront Market.

Guidelines:
- Always ground responses in data from tools.
- Be concise and actionable.""",
        description=(
            "AI assistant for grocery retail operations. Searches SOPs and "
            "brand guidelines, and delegates to sub-agents for analytics, "
            "image generation, and shopper simulation."
        ),
        tools=root_tools,
        sub_agents=[analytics_agent, image_agent],
    )

    return agent


# For ADK CLI: `adk deploy agent_engine` expects `root_agent` at module level
try:
    root_agent = create_agent()
except Exception as e:
    root_agent = None
    print(f"Warning: Could not create root_agent: {e}")


def get_agent_card() -> dict:
    """Return the A2A AgentCard describing this agent's capabilities."""
    config = _load_config()
    retailer = config["retailer"]["name"]

    return {
        "name": "grocery-retail-assistant",
        "description": (
            f"AI assistant for {retailer} grocery retail operations. "
            "Handles SOP lookup, brand guidelines, sales analytics, "
            "and product image generation."
        ),
        "url": os.environ.get(
            "A2A_AGENT_URL",
            "http://localhost:8080"
        ),
        "version": "1.0.0",
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
        },
        "skills": [
            {
                "id": "sop-lookup",
                "name": "SOP Lookup",
                "description": "Search and retrieve Standard Operating Procedures for store associates",
            },
            {
                "id": "brand-guidelines",
                "name": "Brand Guidelines",
                "description": "Search brand guidelines for colors, typography, tone of voice",
            },
            {
                "id": "sales-analytics",
                "name": "Sales Analytics",
                "description": "Query BigQuery for sales, products, stores, and customer analytics",
            },
            {
                "id": "image-generation",
                "name": "Product Image Generation",
                "description": "Generate brand-compliant product imagery using Gemini Image",
            },
            {
                "id": "shopper-simulation",
                "name": "Shopper Simulation",
                "description": "Simulate shopper behavior and test endcap merchandising strategies via Agent Engine",
            },
        ],
    }
