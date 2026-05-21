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
    config["models"].setdefault("adk", "gemini-3.5-flash")
    config["models"].setdefault("adk_fast", "gemini-3.5-flash")

    return config


def _get_a2ui_prompt(retailer: str) -> str:
    """Generate A2UI-first system prompt for the A2A grocery agent.

    Returns a UI-first prompt that mandates <a2ui-json> blocks as the
    PRIMARY output format with rich interactive components.
    """
    try:
        from a2ui.schema.manager import A2uiSchemaManager
        from a2ui.basic_catalog.provider import BasicCatalog

        schema_manager = A2uiSchemaManager(
            version='0.8',
            catalogs=[BasicCatalog.get_config('0.8')],
        )
        base = schema_manager.generate_system_prompt(
            role_description=f"UI-first grocery retail operations assistant for {retailer}",
            ui_description=(
                "This agent is a VISUAL DASHBOARD that renders all outputs as rich "
                "interactive UI surfaces. Every response MUST lead with an <a2ui-json> "
                "block before any text. Available components: Card (wrapped content), "
                "Row (side-by-side layouts), Column (vertical stacks), List (scrollable "
                "items), Tabs (multi-section organizer), Text (formatted markdown with "
                "bold metrics and emoji KPIs), Image (product photos, charts), "
                "Icon (material icons like shoppingCart, star, check, warning, lock, info), "
                "Divider (visual separator), CheckBox (interactive checklists). "
                "Use Tabs to organize multi-section SOPs. Use CheckBox for procedure steps. "
                "Use Row for KPI metric dashboards. Use Image for product cards. "
                "NEVER output a plain markdown list — use List with Card children instead."
            ),
            include_schema=True,
            include_examples=True,
        )
        examples = """

⚠️ MANDATORY A2UI-FIRST OUTPUT RULES:
- Your primary output is A2UI components, NOT text.
- FIRST output the <a2ui-json> block, THEN at most 1-2 sentences of context.
- NEVER use markdown bullet lists (use List + Card), markdown tables (use Row + Card),
  or long text paragraphs for SOPs (use CheckBox list).
- SOPs → Card header + CheckBox steps. Analytics → Row of KPI Cards. Products → Image + Card.
- Use Icon for badges (lock, check, warning, shoppingCart, star, info).
- Use Divider between sections. Minimum 4 component types per response.
- ALWAYS use at least a VARIETY of component types — Card, Row, List, Icon, Text, Divider.
- Use emoji indicators in Text for visual richness (📈 📉 ✅ ⚠️ 🏆 🔒 📊 🌱 ⭐).

STRICT RULES:
- Wrap A2UI JSON in <a2ui-json> and </a2ui-json> tags.
- Always start with beginRendering, then surfaceUpdate.
- Use flat component arrays with string ID refs in children.explicitList.
- Card uses "child" (singular string ID). Text.text uses {"literalString": "..."}.
- Icon.name uses {"literalString": "check"}.
"""
        return base + examples
    except Exception:
        return ""


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

    a2ui_suffix = _get_a2ui_prompt(retailer)
    base_instruction = f"""You are an AI assistant for {retailer}, a grocery retail company.
You help associates, managers, and stakeholders with:
1. Standard Operating Procedures - Retrieve and explain SOPs
2. Brand-Compliant Marketing Content - Generate brand-aligned materials
3. Product Information & Analytics - Answer data questions using BigQuery
4. Product Image Generation - Create product imagery

Guidelines:
- Always ground responses in data from tools.
- Be concise and actionable."""
    if a2ui_suffix:
        base_instruction += "\n\n" + a2ui_suffix

    agent = LlmAgent(
        name="sop_agent",
        model=adk_model,
        planner=planner,
        instruction=base_instruction,
        description=(
            "AI assistant for grocery retail operations. Searches SOPs and "
            "brand guidelines, and delegates to sub-agents for analytics "
            "and image generation."
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


def get_agent_card():
    """Deprecated — AgentCard is built in server.py with A2UI extension."""
    from .server import _build_agent_card
    return _build_agent_card()
