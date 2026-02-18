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
    config["models"].setdefault("adk_fast", "gemini-3-flash-preview")

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
    adk_model = config["models"].get("adk_fast", config["models"].get("adk", "gemini-3-flash-preview"))

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
    adk_model = config["models"].get("adk_fast", config["models"].get("adk", "gemini-3-flash-preview"))
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

    # ── Endcap A/B Comparison Tool ──────────────────────────────────────

    def compare_endcap_strategies(
        strategy_a: str = "baseline",
        strategy_b: str = "seasonal_produce",
        store: str = "Downtown Market",
        num_shoppers: int = 5,
    ) -> dict:
        """Compare two endcap merchandising strategies side-by-side.

        Runs the same set of shopper personas through two different endcap
        configurations and produces a comparative analysis. Use this to
        A/B test marketing endcap placements and measure efficacy of
        in-store assortment and placement decisions.

        Args:
            strategy_a: First strategy key to test.
            strategy_b: Second strategy key to compare against strategy_a.
            store: Store name (Downtown Market, Westside Market, Lakefront Market).
            num_shoppers: Number of shoppers per strategy (1-12).

        Returns:
            Dict with side-by-side metrics: conversion rates, revenue,
            endcap lift, and a winner recommendation.
        """
        all_strategies = _load_strategies()
        s_a = all_strategies.get(strategy_a)
        s_b = all_strategies.get(strategy_b)
        if not s_a:
            return {"status": "error", "message": f"Unknown strategy_a: '{strategy_a}'. Available: {list(all_strategies.keys())}"}
        if not s_b:
            return {"status": "error", "message": f"Unknown strategy_b: '{strategy_b}'. Available: {list(all_strategies.keys())}"}

        all_personas = _load_personas()
        layout = STORE_LAYOUTS.get(store, STORE_LAYOUTS["Downtown Market"])
        n = max(1, min(num_shoppers, len(all_personas)))
        selected = _select_personas_by_distribution(n)

        def _simulate_arm(strat_data):
            results = []
            for p in selected:
                behavior = p.get("shopping_behavior", {})
                budget = behavior.get("budget", p.get("budget", 100.0))
                impulse = behavior.get("impulse_tendency", p.get("impulse_tendency", 0.5))
                endcaps = strat_data.get("endcaps", [])
                cart_items = []
                endcap_pickups = []
                spend = 0.0
                for aisle in layout["aisles"]:
                    base_prob = 0.5
                    cat_prefs = p.get("category_preferences", {})
                    pref_key = aisle["name"].lower().split(" ")[0]
                    if isinstance(cat_prefs, dict):
                        base_prob = cat_prefs.get(pref_key, 0.4)
                    if random.random() < base_prob:
                        price = round(random.uniform(1.50, 8.99), 2)
                        if spend + price <= budget:
                            cart_items.append({"product": f"{aisle['name']} item", "price": price})
                            spend += price
                    for ec in endcaps:
                        if ec["location"] == aisle["name"]:
                            discount_boost = 0.15 if "%" in ec.get("discount", "") else 0.10
                            pickup_prob = min(impulse * 0.6 + discount_boost + 0.1, 0.95)
                            if random.random() < pickup_prob:
                                endcap_pickups.append(ec["product"])
                                ec_price = round(random.uniform(2.99, 12.99), 2)
                                if spend + ec_price <= budget:
                                    cart_items.append({"product": ec["product"], "price": ec_price})
                                    spend += ec_price
                results.append({
                    "persona": p["name"], "persona_id": p.get("id", ""),
                    "total_spend": round(spend, 2), "cart_size": len(cart_items),
                    "endcap_pickups": endcap_pickups, "endcap_converted": len(endcap_pickups) > 0,
                })
            return results

        results_a = _simulate_arm(s_a)
        results_b = _simulate_arm(s_b)

        def _metrics(results):
            n = len(results)
            total = sum(r["total_spend"] for r in results)
            conv = sum(1 for r in results if r["endcap_converted"])
            return {
                "total_revenue": round(total, 2),
                "conversion_rate": round((conv / n * 100) if n else 0, 1),
                "avg_spend": round(total / n if n else 0, 2),
                "avg_cart_size": round(sum(r["cart_size"] for r in results) / n if n else 0, 1),
                "total_endcap_pickups": sum(len(r["endcap_pickups"]) for r in results),
            }

        m_a, m_b = _metrics(results_a), _metrics(results_b)
        rev_lift = m_b["total_revenue"] - m_a["total_revenue"]
        score_a = m_a["conversion_rate"] * 0.4 + (m_a["total_revenue"] / max(m_b["total_revenue"], 1)) * 30
        score_b = m_b["conversion_rate"] * 0.4 + (m_b["total_revenue"] / max(m_a["total_revenue"], 1)) * 30
        winner = strategy_a if score_a > score_b * 1.05 else (strategy_b if score_b > score_a * 1.05 else "tie")

        return {
            "status": "success",
            "comparison": {
                "strategy_a": {"key": strategy_a, "name": s_a["name"], "metrics": m_a, "shopper_details": results_a},
                "strategy_b": {"key": strategy_b, "name": s_b["name"], "metrics": m_b, "shopper_details": results_b},
                "delta": {"revenue_lift": round(rev_lift, 2), "conversion_lift": round(m_b["conversion_rate"] - m_a["conversion_rate"], 1)},
                "winner": winner,
            },
        }

    def list_endcap_strategies() -> dict:
        """List all available endcap merchandising strategies for simulation.

        Returns:
            Dict with all strategy keys, names, descriptions, and endcap details.
        """
        all_strategies = _load_strategies()
        out = {}
        for key, s in all_strategies.items():
            out[key] = {
                "name": s["name"],
                "description": s.get("description", ""),
                "endcap_count": len(s.get("endcaps", [])),
                "endcaps": [{"location": ec["location"], "product": ec["product"], "discount": ec["discount"]} for ec in s.get("endcaps", [])],
            }
        return {"status": "success", "strategies": out, "stores": list(STORE_LAYOUTS.keys())}

    compare_tool = FunctionTool(func=compare_endcap_strategies)
    list_tool = FunctionTool(func=list_endcap_strategies)

    # Report generation tool
    try:
        from .tools.report_generator import generate_simulation_report
        report_tool = FunctionTool(func=generate_simulation_report)
        tools = [report_tool, compare_tool, list_tool]
    except ImportError:
        tools = [compare_tool, list_tool]

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

Available Stores: Downtown Market, Westside Market, Lakefront Market

You have {len(shopper_agents)} shopper agents available. Each represents a
different customer persona walking the store aisles concurrently.

CAPABILITIES:
1. **Run Single Simulation** — Delegate to shopper agents to simulate their
   shopping trips under the current endcap scenario. Collect results and produce
   an aggregate report (revenue, conversion rate, cart size, ROI).

2. **A/B Test Endcap Strategies** — Use the compare_endcap_strategies tool to
   pit two merchandising strategies against each other. This runs the same
   shopper personas through both configurations and produces side-by-side
   metrics. Use this when users ask to "test", "compare", or "A/B test"
   different endcap placements or marketing strategies.

3. **List Available Strategies** — Use the list_endcap_strategies tool to show
   users all available endcap configurations they can test.

4. **Generate Report** — Use generate_simulation_report to create a visual
   HTML report with BCG/McKinsey-style charts.

When presenting A/B test results, always include:
- Side-by-side conversion rates
- Revenue comparison (total and per-shopper average)
- Endcap pickup counts and which products converted best
- A clear winner recommendation with rationale

Compare results across scenarios when asked to evaluate merchandising strategies.""",
        description=(
            "Orchestrates simulated shopper agents to evaluate store merchandising "
            "strategies and endcap placement effectiveness. Supports A/B testing "
            "of different marketing endcap configurations."
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
