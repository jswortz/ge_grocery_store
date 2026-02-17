"""Main ADK agent definition for the grocery retail assistant.

Uses a multi-agent architecture:
- root_agent: Orchestrator with DiscoveryEngineSearchTool (searches both
  SOP and brand guideline data stores via the engine) and sub-agents for
  function tools
- analytics_agent: FunctionTool for BigQuery queries
- image_agent: FunctionTool for product image generation

We use DiscoveryEngineSearchTool (a FunctionTool subclass) directly instead
of VertexAiSearchTool because VertexAiSearchTool adds a built-in Gemini
retrieval tool that cannot coexist with the transfer_to_agent function tools
injected by sub-agents. DiscoveryEngineSearchTool wraps the Discovery Engine
SearchService REST API as a regular function tool, avoiding this conflict.

Usage:
    # Local development (from project root)
    adk web src/agent

    # Programmatic
    from src.agent.agent import root_agent
"""

import os
from pathlib import Path

import yaml

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
    if os.environ.get("ENGINE_ID"):
        config.setdefault("project", {})["engine_id"] = os.environ["ENGINE_ID"]
    if os.environ.get("BQ_PROJECT"):
        config.setdefault("bigquery", {})["project"] = os.environ["BQ_PROJECT"]
    if os.environ.get("BQ_DATASET"):
        config.setdefault("bigquery", {})["dataset"] = os.environ["BQ_DATASET"]
    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]
    if os.environ.get("IMAGEN_MODEL"):
        config.setdefault("models", {})["imagen"] = os.environ["IMAGEN_MODEL"]

    # Defaults for models if not set
    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-3-pro-preview")
    config["models"].setdefault("adk_fast", "gemini-3-flash-preview")
    config["models"].setdefault("imagen", "gemini-3-pro-image-preview")

    return config


def _build_datastore_id(store_name: str) -> str:
    """Build full data store resource path."""
    config = _load_config()
    project_id = config["project"]["id"]
    return (
        f"projects/{project_id}/locations/global/collections/"
        f"default_collection/dataStores/{store_name}"
    )


async def _save_memory_callback(callback_context):
    """Save session to memory after each agent turn for cross-session recall."""
    memory_service = callback_context._invocation_context.memory_service
    if memory_service is not None:
        await memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )


def create_agent():
    """Create and return the configured root agent with sub-agents.

    Uses DiscoveryEngineSearchTool directly (a FunctionTool subclass) on the
    root agent. This avoids the Gemini built-in search tool limitation that
    prevents mixing retrieval tools with function tools (like transfer_to_agent).
    """
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.adk.tools.discovery_engine_search_tool import DiscoveryEngineSearchTool
    from google.genai.types import ThinkingConfig

    from .prompts.system_prompts import get_main_agent_instruction
    from .tools.bq_tool import create_bq_tool
    from .tools.image_gen_tool import create_image_gen_tool

    config = _load_config()
    retailer = config["retailer"]["name"]
    adk_model = config["models"]["adk"]          # Pro for root orchestrator
    adk_fast = config["models"]["adk_fast"]      # Flash for sub-agents

    # Enable Gemini thinking for multi-step reasoning
    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    # DiscoveryEngineSearchTool wraps the Discovery Engine SearchService API
    # as a regular FunctionTool, so it can coexist with transfer_to_agent tools.
    # We specify data_store_specs to restrict search to only our GCS-backed
    # stores (sop-store, brand-guidelines-store), excluding any workspace
    # data stores (Gmail, Calendar, etc.) which require user OAuth.
    root_tools = []
    try:
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

    # Add PreloadMemoryTool for cross-session memory
    try:
        from google.adk.tools.preload_memory_tool import PreloadMemoryTool
        root_tools.append(PreloadMemoryTool())
    except ImportError:
        print("Warning: PreloadMemoryTool not available")

    # Add Google Search grounding for real-time market data
    try:
        from google.adk.tools import google_search
        root_tools.append(google_search)
    except ImportError:
        print("Warning: GoogleSearchTool not available")

    # Add A2A tool for cross-agent delegation to simulator
    try:
        from .tools.a2a_tool import create_a2a_tool
        root_tools.append(create_a2a_tool())
    except ImportError:
        print("Warning: A2A tool not available")

    # Sub-agents for function tools
    sub_agents = []

    # Analytics sub-agent (Flash for fast SQL generation)
    analytics_agent = LlmAgent(
        name="analytics_agent",
        model=adk_fast,
        planner=planner,
        instruction=(
            f"You are the data analytics specialist for {retailer}. "
            "Use the query_grocery_data tool to answer questions about sales, "
            "products, stores, customers, and employees. Present results clearly "
            "with specific numbers."
        ),
        description=(
            "Answers data questions about sales, products, stores, and customers "
            "by querying the BigQuery star schema."
        ),
        tools=[create_bq_tool()],
    )
    sub_agents.append(analytics_agent)

    # Image generation sub-agent (Flash for coordination, Imagen for actual gen)
    image_agent = LlmAgent(
        name="image_agent",
        model=adk_fast,
        planner=planner,
        instruction=(
            f"You are the product imagery specialist for {retailer}. "
            "Use the generate_product_image tool to create product photos. "
            "Apply brand colors and style guidelines when generating images. "
            "IMPORTANT: When the tool returns successfully, always include the "
            "markdown image from the 'message' field in your response exactly "
            "as returned (e.g., ![Product Name](/api/images/...)) so the user "
            "can see the generated image inline in the chat."
        ),
        description=(
            "Generates product images following brand guidelines "
            "for promotional materials and marketing content."
        ),
        tools=[create_image_gen_tool()],
    )
    sub_agents.append(image_agent)

    # Root orchestrator with search tools + sub-agents for function tools
    agent = LlmAgent(
        name="grocery_assistant",
        model=adk_model,
        planner=planner,
        instruction=get_main_agent_instruction(),
        description=(
            "AI assistant for grocery retail operations. Searches SOPs and "
            "brand guidelines directly, and delegates to sub-agents for "
            "analytics and image generation."
        ),
        tools=root_tools,
        sub_agents=sub_agents,
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
