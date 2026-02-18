"""World-model shopper simulator ADK agent.

Simulates individual shoppers making store purchases as concurrent sub-agents.
Each shopper agent walks the aisles of a specific store, builds a shopping cart,
and reacts to endcap merchandising placement scenarios.

Architecture:
    simulator_orchestrator (root)
    ├── shopper_agent_1 (sub-agent: walks aisles, builds cart)
    ├── shopper_agent_2 (sub-agent: different persona/store)
    └── ...N concurrent shoppers

Uses gemini-3-flash-preview for all agents with thinking enabled. Leverages ADK user simulation
evaluation to validate shopper behavior across merchandising scenarios.

Usage:
    # Local development
    cd src/simulator_agent && adk web

    # Run scenarios
    python -m src.simulator_agent.run_scenarios
"""

import os
import random
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
CONFIG_PATH = CONFIG_DIR / "settings.yaml"
STRATEGIES_PATH = CONFIG_DIR / "endcap_strategies.yaml"
PERSONAS_PATH = CONFIG_DIR / "shopper_personas.yaml"


def _load_config() -> dict:
    """Load config from settings.yaml."""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]
    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-3-flash-preview")

    return config


def _load_strategies() -> dict:
    """Load endcap strategies from YAML config."""
    if STRATEGIES_PATH.exists():
        with open(STRATEGIES_PATH) as f:
            data = yaml.safe_load(f)
        return data.get("strategies", {})
    return ENDCAP_SCENARIOS_FALLBACK


def _load_personas() -> list[dict]:
    """Load shopper personas from YAML config."""
    if PERSONAS_PATH.exists():
        with open(PERSONAS_PATH) as f:
            data = yaml.safe_load(f)
        return data.get("personas", [])
    return SHOPPER_PERSONAS_FALLBACK


# ─── Store Layout Model ──────────────────────────────────────────────────────

STORE_LAYOUTS = {
    "Downtown Market": {
        "store_id": 1,
        "aisles": [
            {"name": "Produce", "sections": ["Fresh Fruits", "Fresh Vegetables", "Organic", "Salad Bar"]},
            {"name": "Bakery", "sections": ["Bread", "Pastries", "Cakes", "Artisan Loaves"]},
            {"name": "Dairy", "sections": ["Milk", "Cheese", "Yogurt", "Eggs"]},
            {"name": "Meat & Seafood", "sections": ["Beef", "Poultry", "Pork", "Fresh Fish"]},
            {"name": "Frozen", "sections": ["Frozen Meals", "Ice Cream", "Frozen Vegetables", "Pizza"]},
            {"name": "Beverages", "sections": ["Water", "Juice", "Soda", "Coffee & Tea"]},
            {"name": "Snacks", "sections": ["Chips", "Crackers", "Nuts", "Candy"]},
            {"name": "Pantry", "sections": ["Canned Goods", "Pasta", "Rice", "Sauces"]},
        ],
        "endcaps": [],
    },
    "Westside Market": {
        "store_id": 2,
        "aisles": [
            {"name": "Produce", "sections": ["Fruits", "Vegetables", "Herbs", "Ready-Cut"]},
            {"name": "Bakery", "sections": ["Fresh Bread", "Donuts", "Cookies", "Pies"]},
            {"name": "Dairy", "sections": ["Milk & Cream", "Cheese", "Butter", "Eggs"]},
            {"name": "Meat", "sections": ["Fresh Cuts", "Deli Meats", "Sausage", "Ground Meat"]},
            {"name": "Frozen", "sections": ["Entrees", "Desserts", "Vegetables", "Breakfast"]},
            {"name": "Beverages", "sections": ["Soft Drinks", "Water", "Sports Drinks", "Juices"]},
            {"name": "Snacks", "sections": ["Salty Snacks", "Sweet Snacks", "Trail Mix", "Bars"]},
            {"name": "Household", "sections": ["Cleaning", "Paper Products", "Trash Bags", "Laundry"]},
        ],
        "endcaps": [],
    },
    "Lakefront Market": {
        "store_id": 3,
        "aisles": [
            {"name": "Produce", "sections": ["Local Farms", "Tropical Fruits", "Salads", "Mushrooms"]},
            {"name": "Bakery", "sections": ["Sourdough", "Croissants", "Gluten-Free", "Rolls"]},
            {"name": "Dairy", "sections": ["Organic Milk", "Artisan Cheese", "Plant-Based", "Eggs"]},
            {"name": "Seafood", "sections": ["Gulf Shrimp", "Fresh Fillets", "Sushi-Grade", "Crab"]},
            {"name": "Frozen", "sections": ["Organic Frozen", "Ice Cream", "Smoothie Packs", "Meals"]},
            {"name": "Beverages", "sections": ["Kombucha", "Craft Sodas", "Cold Brew", "Coconut Water"]},
            {"name": "Health", "sections": ["Vitamins", "Protein Bars", "Supplements", "Probiotics"]},
            {"name": "International", "sections": ["Asian", "Mexican", "Mediterranean", "Indian"]},
        ],
        "endcaps": [],
    },
}

# ─── Fallback data (used when YAML configs are not available) ────────────────

ENDCAP_SCENARIOS_FALLBACK = {
    "baseline": {
        "name": "Baseline - No Special Endcaps",
        "description": "Standard store layout with no promotional endcaps",
        "endcaps": [],
    },
    "seasonal_produce": {
        "name": "Seasonal Produce Push",
        "description": "Endcaps at Produce aisle exits featuring seasonal fruits at 20% off",
        "endcaps": [
            {"location": "Produce", "position": "exit", "product": "Nano Banana Pro",
             "discount": "20% off", "display_type": "pyramid stack with tasting station"},
            {"location": "Bakery", "position": "entrance", "product": "Fresh Mango Slices",
             "discount": "Buy 2 Get 1 Free", "display_type": "refrigerated endcap with recipe cards"},
        ],
    },
}

SHOPPER_PERSONAS_FALLBACK = [
    {"id": "budget_family", "name": "Budget-Conscious Family Shopper",
     "description": "Parent shopping for a family of 4, focused on value and weekly staples",
     "shopping_behavior": {"budget": 120.00, "impulse_tendency": 0.30},
     "category_preferences": {"produce": 0.8, "dairy": 0.9, "bakery": 0.6, "meat": 0.7},
     "loyalty_tier": "Silver", "distribution_weight": 0.30},
    {"id": "health_enthusiast", "name": "Health-Conscious Professional",
     "description": "Single professional focused on organic, fresh, and healthy options",
     "shopping_behavior": {"budget": 80.00, "impulse_tendency": 0.50},
     "category_preferences": {"produce": 1.0, "dairy": 0.6, "bakery": 0.3},
     "loyalty_tier": "Gold", "distribution_weight": 0.20},
    {"id": "quick_stop", "name": "Quick-Stop Shopper",
     "description": "Person grabbing a few items on the way home, time-constrained",
     "shopping_behavior": {"budget": 30.00, "impulse_tendency": 0.70},
     "category_preferences": {"snacks": 0.8, "beverages": 0.9, "frozen": 0.7},
     "loyalty_tier": "Bronze", "distribution_weight": 0.20},
]


def _build_store_context(store_name: str, scenario_key: str) -> str:
    """Build a textual description of the store layout for the agent."""
    layout = STORE_LAYOUTS.get(store_name, STORE_LAYOUTS["Downtown Market"])
    strategies = _load_strategies()
    scenario = strategies.get(scenario_key, strategies.get("baseline", {"name": "Baseline", "description": "", "endcaps": []}))

    aisle_desc = ""
    for aisle in layout["aisles"]:
        sections = ", ".join(aisle["sections"])
        aisle_desc += f"  - {aisle['name']}: {sections}\n"

    endcap_desc = "  None (standard layout)\n"
    if scenario.get("endcaps"):
        endcap_desc = ""
        for ec in scenario["endcaps"]:
            endcap_desc += (
                f"  - At {ec['location']} aisle ({ec['position']}): "
                f"{ec['product']} — {ec['discount']} "
                f"({ec['display_type']})\n"
            )

    return f"""Store: {store_name} (Store ID: {layout['store_id']})
Merchandising Scenario: {scenario['name']}
{scenario.get('description', '')}

Aisles:
{aisle_desc}
Endcap Displays:
{endcap_desc}"""


def _build_shopper_instruction(persona: dict, store_name: str, scenario_key: str) -> str:
    """Build the instruction for a shopper sub-agent."""
    config = _load_config()
    retailer = config["retailer"]["name"]
    store_context = _build_store_context(store_name, scenario_key)

    # Handle both flat and nested persona formats
    behavior = persona.get("shopping_behavior", {})
    budget = behavior.get("budget", persona.get("budget", 100.00))
    impulse = behavior.get("impulse_tendency", persona.get("impulse_tendency", 0.5))
    loyalty = persona.get("loyalty_tier", "Bronze")

    cat_prefs = persona.get("category_preferences", {})
    if isinstance(cat_prefs, dict):
        prefs = ", ".join(f"{k} ({v:.0%})" for k, v in cat_prefs.items() if v >= 0.5)
    else:
        prefs = ", ".join(persona.get("preferences", []))

    demographics = persona.get("demographics", {})
    demo_line = ""
    if demographics:
        demo_line = f"\nDemographics: Age {demographics.get('age_range', 'N/A')}, Household size {demographics.get('household_size', 'N/A')}, Income {demographics.get('income_bracket', 'N/A')}"

    endcap_sens = persona.get("endcap_sensitivity", {})
    endcap_line = ""
    if endcap_sens:
        endcap_line = (
            f"\nEndcap Sensitivity: Needs {endcap_sens.get('discount_threshold', 0.1):.0%}+ discount, "
            f"Brand loyalty {endcap_sens.get('brand_loyalty', 0.5):.0%}, "
            f"Novelty seeking {endcap_sens.get('novelty_seeking', 0.5):.0%}"
        )

    return f"""You are simulating a shopper at {retailer}'s {store_name}.

Your Persona: {persona['name']}
{persona.get('description', '')}
Budget: ${budget:.2f}
Preferred Categories: {prefs}
Loyalty Tier: {loyalty}
Impulse Buy Tendency: {int(impulse * 100)}%{demo_line}{endcap_line}

{store_context}

SIMULATION INSTRUCTIONS:
1. Walk through the store aisles in a realistic order based on your persona.
2. For each aisle you visit, decide which products to add to your cart.
3. When you encounter an endcap display, decide whether to pick up the promoted
   item based on your impulse tendency and preferences.
4. Track your running total and stay within budget.
5. After visiting all relevant aisles, report your final cart.

OUTPUT FORMAT — STRUCTURED JSON:
Respond with valid JSON matching this schema:
{{
  "persona": "{persona['name']}",
  "aisles_visited": [
    {{
      "aisle": "Produce",
      "items": [{{"product": "Bananas", "quantity": 1, "price": 1.29}}],
      "endcap_interaction": {{"product": "Nano Banana Pro", "picked_up": true, "reason": "good deal"}}
    }}
  ],
  "cart": [{{"product": "Bananas", "quantity": 1, "price": 1.29}}],
  "total_spend": 45.67,
  "endcap_items": ["Nano Banana Pro"],
  "experience_rating": 4,
  "endcap_influenced": true
}}"""


def _select_personas_by_distribution(num_shoppers: int) -> list[dict]:
    """Select personas proportionally based on distribution_weight."""
    personas = _load_personas()

    if num_shoppers >= len(personas):
        return personas[:num_shoppers]

    weights = [p.get("distribution_weight", 1.0 / len(personas)) for p in personas]
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Weighted selection without replacement
    selected = []
    available = list(range(len(personas)))
    for _ in range(min(num_shoppers, len(personas))):
        available_weights = [weights[i] for i in available]
        total_w = sum(available_weights)
        if total_w == 0:
            break
        norm_weights = [w / total_w for w in available_weights]
        chosen_idx = random.choices(available, weights=norm_weights, k=1)[0]
        selected.append(personas[chosen_idx])
        available.remove(chosen_idx)

    return selected


def _create_planner():
    """Create a BuiltInPlanner with thinking enabled for reasoning."""
    from google.adk.planners import BuiltInPlanner
    from google.genai.types import ThinkingConfig

    return BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )


async def _save_memory_callback(callback_context):
    """Save session to memory after each agent turn for cross-session recall."""
    memory_service = callback_context._invocation_context.memory_service
    if memory_service is not None:
        await memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )


def create_shopper_agent(
    persona: dict,
    store_name: str = "Downtown Market",
    scenario_key: str = "baseline",
):
    """Create a single shopper simulation sub-agent."""
    from google.adk.agents import LlmAgent

    config = _load_config()
    adk_model = config["models"]["adk"]

    return LlmAgent(
        name=f"shopper_{persona['id']}",
        model=adk_model,
        planner=_create_planner(),
        instruction=_build_shopper_instruction(persona, store_name, scenario_key),
        description=f"Simulated shopper: {persona['name']} at {store_name}",
    )


def create_agent(
    store_name: str = "Downtown Market",
    scenario_key: str = "baseline",
    num_shoppers: int = 3,
):
    """Create the simulator orchestrator agent with shopper sub-agents.

    Uses the ADK clone() pattern to create shopper agents from a base
    template, ensuring proper deep-copy of planner, model config, and
    all base properties.

    Args:
        store_name: Which store to simulate (Downtown/Westside/Lakefront Market)
        scenario_key: Endcap merchandising scenario (see config/endcap_strategies.yaml)
        num_shoppers: Number of concurrent shoppers to simulate (1-8)
    """
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool

    config = _load_config()
    retailer = config["retailer"]["name"]
    adk_model = config["models"]["adk"]
    strategies = _load_strategies()
    scenario = strategies.get(scenario_key, strategies.get("baseline", {"name": "Baseline", "description": ""}))

    # Select shoppers weighted by distribution
    selected_personas = _select_personas_by_distribution(num_shoppers)

    # Create base shopper template and clone for each persona
    base_shopper = LlmAgent(
        name="shopper_template",
        model=adk_model,
        planner=_create_planner(),
        instruction="template",
        description="template",
    )
    shopper_agents = [
        base_shopper.clone(update={
            "name": f"shopper_{persona['id']}",
            "instruction": _build_shopper_instruction(persona, store_name, scenario_key),
            "description": f"Simulated shopper: {persona['name']} at {store_name}",
        })
        for persona in selected_personas
    ]

    # Available strategies list for the orchestrator
    strategy_list = "\n".join(
        f"  - {key}: {s['name']}" for key, s in strategies.items()
    )

    # Report generation tool
    try:
        from .tools.report_generator import generate_simulation_report
        report_tool = FunctionTool(func=generate_simulation_report)
        tools = [report_tool]
    except ImportError:
        tools = []

    # Add PreloadMemoryTool for cross-session memory recall
    try:
        from google.adk.tools.preload_memory_tool import PreloadMemoryTool
        tools.append(PreloadMemoryTool())
    except ImportError:
        pass

    orchestrator = LlmAgent(
        name="simulator_orchestrator",
        model=adk_model,
        planner=_create_planner(),
        instruction=f"""You are a retail simulation orchestrator for {retailer}.
You manage a world-model simulation of shoppers in {store_name}.

Current Scenario: {scenario['name']}
{scenario.get('description', '')}

Available Strategies:
{strategy_list}

You have {len(shopper_agents)} shopper agents available. Each represents a
different customer persona walking the store aisles concurrently.

When asked to run a simulation:
1. Delegate to each shopper agent to simulate their shopping trip
2. Collect all results
3. Produce an aggregate report with:
   - Total revenue across all shoppers
   - Endcap conversion rate (% of shoppers who picked up endcap items)
   - Most popular items by persona type
   - Average cart size and spend
   - Endcap ROI estimate (incremental revenue from endcap placements)
   - Recommendations for merchandising optimization
4. Use the generate_simulation_report tool to create a visual HTML report
   with BCG/McKinsey-style charts. Pass the collected results as JSON.

Compare results across scenarios when asked to evaluate merchandising strategies.""",
        description=(
            "Orchestrates simulated shopper agents to evaluate store merchandising "
            "strategies and endcap placement effectiveness."
        ),
        sub_agents=shopper_agents,
        tools=tools,
        after_agent_callback=_save_memory_callback,
    )

    return orchestrator


# For ADK CLI: `adk web` expects `root_agent` at module level
try:
    root_agent = create_agent(
        store_name="Downtown Market",
        scenario_key="seasonal_produce",
        num_shoppers=3,
    )
except ImportError:
    root_agent = None
    print("ADK not installed. Install with: pip install google-adk")
