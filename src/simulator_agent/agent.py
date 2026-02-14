"""World-model shopper simulator ADK agent.

Simulates individual shoppers making store purchases as concurrent sub-agents.
Each shopper agent walks the aisles of a specific store, builds a shopping cart,
and reacts to endcap merchandising placement scenarios.

Architecture:
    simulator_orchestrator (root)
    ├── shopper_agent_1 (sub-agent: walks aisles, builds cart)
    ├── shopper_agent_2 (sub-agent: different persona/store)
    └── ...N concurrent shoppers

Uses gemini-3.0-flash for all agents. Leverages ADK user simulation
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

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_config() -> dict:
    """Load config from settings.yaml."""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

    if os.environ.get("ADK_MODEL"):
        config.setdefault("models", {})["adk"] = os.environ["ADK_MODEL"]
    config.setdefault("models", {})
    config["models"].setdefault("adk", "gemini-3.0-flash")

    return config


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
        "endcaps": [],  # Populated per scenario
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

# ─── Endcap Merchandising Scenarios ──────────────────────────────────────────

ENDCAP_SCENARIOS = {
    "baseline": {
        "name": "Baseline - No Special Endcaps",
        "description": "Standard store layout with no promotional endcaps",
        "endcaps": [],
    },
    "seasonal_produce": {
        "name": "Seasonal Produce Push",
        "description": "Endcaps at Produce aisle exits featuring seasonal fruits at 20% off",
        "endcaps": [
            {
                "location": "Produce",
                "position": "exit",
                "product": "Nano Banana Pro",
                "discount": "20% off",
                "display_type": "pyramid stack with tasting station",
            },
            {
                "location": "Bakery",
                "position": "entrance",
                "product": "Fresh Mango Slices",
                "discount": "Buy 2 Get 1 Free",
                "display_type": "refrigerated endcap with recipe cards",
            },
        ],
    },
    "snack_impulse": {
        "name": "Snack Impulse Buy Strategy",
        "description": "High-visibility endcaps near checkout and beverage aisles",
        "endcaps": [
            {
                "location": "Beverages",
                "position": "exit",
                "product": "ValueFresh Trail Mix",
                "discount": "2 for $5",
                "display_type": "clip strip + floor display",
            },
            {
                "location": "Snacks",
                "position": "entrance",
                "product": "Artisan Kettle Chips",
                "discount": "$1 off",
                "display_type": "power wing with shelf talker",
            },
        ],
    },
    "health_wellness": {
        "name": "Health & Wellness Focus",
        "description": "Endcaps promoting organic and health-conscious products",
        "endcaps": [
            {
                "location": "Dairy",
                "position": "exit",
                "product": "Organic Greek Yogurt",
                "discount": "15% off",
                "display_type": "refrigerated endcap with nutritional info",
            },
            {
                "location": "Beverages",
                "position": "entrance",
                "product": "Cold-Pressed Green Juice",
                "discount": "Buy 1 Get 1 50% off",
                "display_type": "chiller display with sampling",
            },
        ],
    },
}

# ─── Shopper Personas ────────────────────────────────────────────────────────

SHOPPER_PERSONAS = [
    {
        "id": "budget_family",
        "name": "Budget-Conscious Family Shopper",
        "description": "Parent shopping for a family of 4, focused on value and weekly staples",
        "budget": 120.00,
        "preferences": ["bulk items", "store brands", "meal ingredients", "kid snacks"],
        "impulse_tendency": 0.3,  # 30% chance of picking up endcap items
        "loyalty_tier": "Silver",
    },
    {
        "id": "health_enthusiast",
        "name": "Health-Conscious Professional",
        "description": "Single professional focused on organic, fresh, and healthy options",
        "budget": 80.00,
        "preferences": ["organic", "fresh produce", "lean proteins", "plant-based"],
        "impulse_tendency": 0.5,
        "loyalty_tier": "Gold",
    },
    {
        "id": "quick_stop",
        "name": "Quick-Stop Shopper",
        "description": "Person grabbing a few items on the way home, time-constrained",
        "budget": 30.00,
        "preferences": ["ready-made meals", "beverages", "snacks"],
        "impulse_tendency": 0.7,  # High impulse tendency for quick shoppers
        "loyalty_tier": "Bronze",
    },
    {
        "id": "weekend_cook",
        "name": "Weekend Meal Prep Cook",
        "description": "Enthusiastic home cook buying ingredients for elaborate weekend meals",
        "budget": 150.00,
        "preferences": ["specialty ingredients", "fresh herbs", "quality meats", "artisan bread"],
        "impulse_tendency": 0.4,
        "loyalty_tier": "Gold",
    },
    {
        "id": "elderly_regular",
        "name": "Elderly Regular Customer",
        "description": "Senior citizen who shops the same store weekly, knows the layout well",
        "budget": 60.00,
        "preferences": ["familiar brands", "easy-open packaging", "dairy", "bread"],
        "impulse_tendency": 0.2,
        "loyalty_tier": "Gold",
    },
]


def _build_store_context(store_name: str, scenario_key: str) -> str:
    """Build a textual description of the store layout for the agent."""
    layout = STORE_LAYOUTS.get(store_name, STORE_LAYOUTS["Downtown Market"])
    scenario = ENDCAP_SCENARIOS.get(scenario_key, ENDCAP_SCENARIOS["baseline"])

    aisle_desc = ""
    for aisle in layout["aisles"]:
        sections = ", ".join(aisle["sections"])
        aisle_desc += f"  - {aisle['name']}: {sections}\n"

    endcap_desc = "  None (standard layout)\n"
    if scenario["endcaps"]:
        endcap_desc = ""
        for ec in scenario["endcaps"]:
            endcap_desc += (
                f"  - At {ec['location']} aisle ({ec['position']}): "
                f"{ec['product']} — {ec['discount']} "
                f"({ec['display_type']})\n"
            )

    return f"""Store: {store_name} (Store ID: {layout['store_id']})
Merchandising Scenario: {scenario['name']}
{scenario['description']}

Aisles:
{aisle_desc}
Endcap Displays:
{endcap_desc}"""


def _build_shopper_instruction(persona: dict, store_name: str, scenario_key: str) -> str:
    """Build the instruction for a shopper sub-agent."""
    config = _load_config()
    retailer = config["retailer"]["name"]
    store_context = _build_store_context(store_name, scenario_key)
    prefs = ", ".join(persona["preferences"])

    return f"""You are simulating a shopper at {retailer}'s {store_name}.

Your Persona: {persona['name']}
{persona['description']}
Budget: ${persona['budget']:.2f}
Preferences: {prefs}
Loyalty Tier: {persona['loyalty_tier']}
Impulse Buy Tendency: {int(persona['impulse_tendency'] * 100)}%

{store_context}

SIMULATION INSTRUCTIONS:
1. Walk through the store aisles in a realistic order based on your persona.
2. For each aisle you visit, decide which products to add to your cart.
3. When you encounter an endcap display, decide whether to pick up the promoted
   item based on your impulse tendency and preferences.
4. Track your running total and stay within budget.
5. After visiting all relevant aisles, report your final cart.

OUTPUT FORMAT:
For each aisle visited, report:
- Aisle name
- Items picked up (product, quantity, estimated price)
- Whether you interacted with any endcap display
- Running total

Final report should include:
- Complete cart contents
- Total spend
- Items picked up from endcap displays (if any)
- Overall shopping experience rating (1-5)
- Whether endcap merchandising influenced your purchases"""


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
        instruction=_build_shopper_instruction(persona, store_name, scenario_key),
        description=f"Simulated shopper: {persona['name']} at {store_name}",
    )


def create_agent(
    store_name: str = "Downtown Market",
    scenario_key: str = "baseline",
    num_shoppers: int = 3,
):
    """Create the simulator orchestrator agent with shopper sub-agents.

    Args:
        store_name: Which store to simulate (Downtown/Westside/Lakefront Market)
        scenario_key: Endcap merchandising scenario (baseline/seasonal_produce/
                      snack_impulse/health_wellness)
        num_shoppers: Number of concurrent shoppers to simulate (1-5)
    """
    from google.adk.agents import LlmAgent

    config = _load_config()
    retailer = config["retailer"]["name"]
    adk_model = config["models"]["adk"]
    scenario = ENDCAP_SCENARIOS.get(scenario_key, ENDCAP_SCENARIOS["baseline"])

    # Select shoppers
    selected_personas = SHOPPER_PERSONAS[:min(num_shoppers, len(SHOPPER_PERSONAS))]

    # Create shopper sub-agents
    shopper_agents = [
        create_shopper_agent(persona, store_name, scenario_key)
        for persona in selected_personas
    ]

    orchestrator = LlmAgent(
        name="simulator_orchestrator",
        model=adk_model,
        instruction=f"""You are a retail simulation orchestrator for {retailer}.
You manage a world-model simulation of shoppers in {store_name}.

Current Scenario: {scenario['name']}
{scenario['description']}

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

Compare results across scenarios when asked to evaluate merchandising strategies.""",
        description=(
            "Orchestrates simulated shopper agents to evaluate store merchandising "
            "strategies and endcap placement effectiveness."
        ),
        sub_agents=shopper_agents,
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
