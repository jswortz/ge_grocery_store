"""Deploy the shopper simulator agent to Vertex AI Agent Engine.

Self-contained deployment script — builds the entire agent inline to
avoid cloudpickle module-not-found errors in the Agent Engine runtime.

Usage:
    cd src && python -m simulator_agent.deploy_to_agent_engine
"""

import os

import vertexai
from vertexai import agent_engines

PROJECT_ID = os.environ.get("PROJECT_ID", "wortz-project-352116")
LOCATION = os.environ.get("AE_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://wortz-project-352116-ge-workshop")

# Hardcoded config for deployment (avoids filesystem config dependency)
_RETAILER_NAME = "ValueFresh Market"
_ADK_MODEL = "gemini-3-flash-preview"


def find_agent_by_display_name(display_name: str) -> str:
    """Find reasoning engine by display name."""
    agent_filter_query = f'display_name="{display_name}"'
    agent_list = agent_engines.list(filter=agent_filter_query)
    for deployed_agent in agent_list:
        return deployed_agent.resource_name
    return ""


# ─── Inline Data (avoids filesystem dependencies at runtime) ─────────────────

_STORE_LAYOUTS = {
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
    },
}

_STRATEGIES = {
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
    "snack_impulse": {
        "name": "Snack Impulse Buy Strategy",
        "description": "High-visibility endcaps near checkout and beverage aisles",
        "endcaps": [
            {"location": "Beverages", "position": "exit", "product": "ValueFresh Trail Mix",
             "discount": "2 for $5", "display_type": "clip strip + floor display"},
            {"location": "Snacks", "position": "entrance", "product": "Artisan Kettle Chips",
             "discount": "$1 off", "display_type": "power wing with shelf talker"},
        ],
    },
    "health_wellness": {
        "name": "Health & Wellness Focus",
        "description": "Endcaps promoting organic and health-conscious products",
        "endcaps": [
            {"location": "Dairy", "position": "exit", "product": "Organic Greek Yogurt",
             "discount": "15% off", "display_type": "refrigerated endcap with nutritional info"},
            {"location": "Beverages", "position": "entrance", "product": "Cold-Pressed Green Juice",
             "discount": "Buy 1 Get 1 50% off", "display_type": "chiller display with sampling"},
        ],
    },
    "premium_cross_merch": {
        "name": "Premium Cross-Merchandising",
        "description": "Strategic pairing of complementary premium products across aisles",
        "endcaps": [
            {"location": "Meat & Seafood", "position": "exit", "product": "Artisan Steak Seasoning Kit",
             "discount": "15% off with meat purchase", "display_type": "branded wooden display"},
            {"location": "Produce", "position": "entrance", "product": "Premium Salad Kit",
             "discount": "Pair with protein, save $2", "display_type": "refrigerated island display"},
        ],
    },
    "back_to_school": {
        "name": "Back-to-School Lunch Packs",
        "description": "Family-oriented endcaps with lunch box essentials and snack multipacks",
        "endcaps": [
            {"location": "Snacks", "position": "exit", "product": "Variety Snack Pack (30ct)",
             "discount": "25% off", "display_type": "pallet display with school-themed signage"},
            {"location": "Beverages", "position": "exit", "product": "Juice Box 10-Pack",
             "discount": "2 for $8", "display_type": "floor stack with clip strip add-ons"},
        ],
    },
    "planogram_produce_forward": {
        "name": "Planogram A: Produce-Forward Layout",
        "description": "Produce as first department upon entry, endcaps at department transitions",
        "endcaps": [
            {"location": "Produce", "position": "entrance", "product": "Organic Berry Medley",
             "discount": "30% off", "display_type": "refrigerated island at store entrance"},
            {"location": "Bakery", "position": "entrance", "product": "Artisan Sourdough Loaf",
             "discount": "$1 off", "display_type": "warm-bread display with aroma diffuser"},
            {"location": "Dairy", "position": "exit", "product": "Premium Butter 4-Pack",
             "discount": "15% off", "display_type": "refrigerated endcap with recipe pairing"},
        ],
    },
    "planogram_perimeter_flow": {
        "name": "Planogram B: Perimeter Power Loop",
        "description": "Fresh departments ring the perimeter. Endcaps at perimeter-to-center transitions pull shoppers into center aisles",
        "endcaps": [
            {"location": "Meat & Seafood", "position": "exit", "product": "Gourmet BBQ Sauce Bundle",
             "discount": "Buy 2 for $9", "display_type": "wooden crate display at perimeter-center transition"},
            {"location": "Frozen", "position": "entrance", "product": "Premium Ice Cream Pint",
             "discount": "2 for $8", "display_type": "freezer endcap with impulse signage"},
            {"location": "Pantry", "position": "entrance", "product": "Imported Pasta Variety Pack",
             "discount": "20% off", "display_type": "gondola endcap with Italian theme"},
        ],
    },
    "planogram_impulse_corridor": {
        "name": "Planogram C: Impulse Corridor",
        "description": "Dedicated high-impulse corridor between Beverages and Checkout with eye-level endcaps",
        "endcaps": [
            {"location": "Beverages", "position": "exit", "product": "Energy Drink 4-Pack",
             "discount": "$2 off", "display_type": "chiller tower at corridor entrance"},
            {"location": "Snacks", "position": "exit", "product": "New Launch: Spicy Mango Chips",
             "discount": "Introductory $1 off", "display_type": "eye-level shelf with NEW! callout"},
            {"location": "Bakery", "position": "exit", "product": "Fresh Cookie 6-Pack",
             "discount": "Buy 1 Get 1 Free", "display_type": "warm cookie station with sampling"},
        ],
    },
}

_PERSONAS = [
    {"id": "budget_family", "name": "Budget-Conscious Family Shopper",
     "description": "Parent shopping for a family of 4, focused on value and weekly staples.",
     "budget": 140.00, "impulse_tendency": 0.30, "loyalty_tier": "Silver",
     "preferences": "produce, dairy, meat, pantry staples, store brands",
     "demographics": "Age 30-45, household 4, income $45K-$65K",
     "endcap_note": "Needs 15%+ discount, high brand loyalty, low novelty seeking",
     "distribution_weight": 0.25},
    {"id": "health_enthusiast", "name": "Health-Conscious Professional",
     "description": "Single professional focused on organic, fresh, and nutrient-dense options.",
     "budget": 100.00, "impulse_tendency": 0.50, "loyalty_tier": "Gold",
     "preferences": "produce, health foods, beverages, organic dairy",
     "demographics": "Age 25-40, household 1, income $75K-$110K",
     "endcap_note": "Low discount threshold, low brand loyalty, high novelty seeking",
     "distribution_weight": 0.15},
    {"id": "quick_stop", "name": "Quick-Stop Convenience Shopper",
     "description": "Time-pressed shopper grabbing a few items on the way home.",
     "budget": 35.00, "impulse_tendency": 0.70, "loyalty_tier": "Bronze",
     "preferences": "beverages, snacks, frozen meals, bakery grab-and-go",
     "demographics": "Age 22-55, household 1-2, income $50K-$85K",
     "endcap_note": "Very low discount threshold, high novelty seeking",
     "distribution_weight": 0.20},
    {"id": "weekend_cook", "name": "Weekend Meal Prep Cook",
     "description": "Enthusiastic home cook buying ingredients for elaborate weekend meals.",
     "budget": 170.00, "impulse_tendency": 0.40, "loyalty_tier": "Gold",
     "preferences": "produce, meat, bakery, international ingredients, specialty items",
     "demographics": "Age 28-50, household 2-3, income $65K-$100K",
     "endcap_note": "Moderate discount sensitivity, very high novelty seeking",
     "distribution_weight": 0.10},
    {"id": "elderly_regular", "name": "Senior Regular Customer",
     "description": "Retiree who shops the same store weekly. Prefers familiar brands.",
     "budget": 70.00, "impulse_tendency": 0.15, "loyalty_tier": "Gold",
     "preferences": "dairy, bakery, produce, pantry, familiar brands",
     "demographics": "Age 65-80, household 1-2, income $30K-$50K",
     "endcap_note": "Needs 20%+ discount, very high brand loyalty, avoids novelty",
     "distribution_weight": 0.10},
    {"id": "young_professional", "name": "Young Urban Professional",
     "description": "Gen-Z or young millennial, trend-aware, socially conscious.",
     "budget": 65.00, "impulse_tendency": 0.65, "loyalty_tier": "Bronze",
     "preferences": "beverages, snacks, health foods, produce, trendy brands",
     "demographics": "Age 22-30, household 1, income $55K-$80K",
     "endcap_note": "Low discount threshold, very low brand loyalty, extremely high novelty",
     "distribution_weight": 0.08},
    {"id": "parent_with_kids", "name": "Parent Shopping with Children",
     "description": "Parent navigating with 1-2 young children. Kids influence purchases.",
     "budget": 130.00, "impulse_tendency": 0.60, "loyalty_tier": "Silver",
     "preferences": "snacks, dairy, beverages, bakery, kid-friendly items",
     "demographics": "Age 28-42, household 3-4, income $55K-$85K",
     "endcap_note": "Moderate sensitivity, kids drive impulse buys",
     "distribution_weight": 0.07},
    {"id": "bargain_hunter", "name": "Extreme Bargain Hunter",
     "description": "Coupon clipper who plans trips around sales circulars.",
     "budget": 80.00, "impulse_tendency": 0.45, "loyalty_tier": "Silver",
     "preferences": "meat deals, pantry bulk, dairy, whatever is on sale",
     "demographics": "Age 35-60, household 2-4, income $35K-$55K",
     "endcap_note": "Needs 20%+ discount, low brand loyalty, moderate novelty",
     "distribution_weight": 0.03},
    {"id": "international_foodie", "name": "International Cuisine Enthusiast",
     "description": "Home cook exploring global flavors. Seeks specialty ingredients and spices.",
     "budget": 120.00, "impulse_tendency": 0.55, "loyalty_tier": "Silver",
     "preferences": "international ingredients, produce, meat, specialty sauces, spices",
     "demographics": "Age 28-55, household 2-3, income $60K-$95K",
     "endcap_note": "Low discount threshold, low brand loyalty, extremely high novelty seeking",
     "distribution_weight": 0.03},
    {"id": "pet_owner", "name": "Pet-First Shopper",
     "description": "Pet parent who always buys pet food and treats alongside regular groceries.",
     "budget": 105.00, "impulse_tendency": 0.40, "loyalty_tier": "Gold",
     "preferences": "produce, dairy, meat, pantry, pet food and treats",
     "demographics": "Age 25-50, household 1-2, income $50K-$80K",
     "endcap_note": "Moderate discount threshold, very high brand loyalty for pet products",
     "distribution_weight": 0.03},
    {"id": "party_host", "name": "Entertaining & Party Host",
     "description": "Shopping for a gathering. Buys large quantities of appetizers, drinks, and snacks.",
     "budget": 220.00, "impulse_tendency": 0.65, "loyalty_tier": "Gold",
     "preferences": "snacks, beverages, bakery, dips, meat, dairy, large quantities",
     "demographics": "Age 30-55, household 2-4, income $70K-$120K",
     "endcap_note": "Very low discount threshold, low brand loyalty, high novelty seeking",
     "distribution_weight": 0.02},
    {"id": "new_to_area", "name": "New-to-Area Explorer",
     "description": "Recently moved, unfamiliar with store layout. Explores every aisle, open to suggestions.",
     "budget": 130.00, "impulse_tendency": 0.75, "loyalty_tier": "Bronze",
     "preferences": "explores everything, open to all categories, tries new products",
     "demographics": "Age 25-40, household 1-2, income $55K-$90K",
     "endcap_note": "Lowest discount threshold, no brand loyalty, maximum novelty seeking",
     "distribution_weight": 0.02},
]


def _build_simulator_agent():
    """Build a fully self-contained simulator agent for Agent Engine.

    This inlines all the store layout, scenario, and persona data so
    the pickled agent has zero external module dependencies.
    """
    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.genai.types import ThinkingConfig

    planner = BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    )

    store_name = "Downtown Market"
    scenario_key = "seasonal_produce"
    retailer = _RETAILER_NAME
    model = _ADK_MODEL

    layout = _STORE_LAYOUTS[store_name]
    scenario = _STRATEGIES[scenario_key]

    aisle_desc = ""
    for aisle in layout["aisles"]:
        sections = ", ".join(aisle["sections"])
        aisle_desc += f"  - {aisle['name']}: {sections}\n"

    endcap_desc = ""
    for ec in scenario["endcaps"]:
        endcap_desc += (
            f"  - At {ec['location']} aisle ({ec['position']}): "
            f"{ec['product']} — {ec['discount']} ({ec['display_type']})\n"
        )

    store_context = f"""Store: {store_name} (Store ID: {layout['store_id']})
Merchandising Scenario: {scenario['name']}
{scenario['description']}

Aisles:
{aisle_desc}
Endcap Displays:
{endcap_desc}"""

    strategy_list = "\n".join(
        f"  - {key}: {s['name']}" for key, s in _STRATEGIES.items()
    )

    # Build shopper sub-agents for all personas
    shopper_agents = []
    for p in _PERSONAS:
        instruction = f"""You are simulating a shopper at {retailer}'s {store_name}.

Your Persona: {p['name']}
{p['description']}
Budget: ${p['budget']:.2f}
Preferences: {p['preferences']}
Loyalty Tier: {p['loyalty_tier']}
Impulse Buy Tendency: {int(p['impulse_tendency'] * 100)}%
{p['demographics']}
{p['endcap_note']}

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
  "persona": "{p['name']}",
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

        shopper_agents.append(
            LlmAgent(
                name=f"shopper_{p['id']}",
                model=model,
                planner=planner,
                instruction=instruction,
                description=f"Simulated shopper: {p['name']} at {store_name}",
            )
        )

    orchestrator = LlmAgent(
        name="simulator_orchestrator",
        model=model,
        planner=planner,
        instruction=f"""You are a retail simulation orchestrator for {retailer}.
You manage a world-model simulation of shoppers in {store_name}.

Current Scenario: {scenario['name']}
{scenario['description']}

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

Compare results across scenarios when asked to evaluate merchandising strategies.""",
        description=(
            "Orchestrates simulated shopper agents to evaluate store merchandising "
            "strategies and endcap placement effectiveness."
        ),
        sub_agents=shopper_agents,
    )

    return orchestrator


def deploy():
    """Deploy the simulator agent to Agent Engine."""
    print("=" * 80)
    print("DEPLOYING SHOPPER SIMULATOR TO AGENT ENGINE")
    print("=" * 80)

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    agent = _build_simulator_agent()
    display_name = "Shopper Simulator Agent"

    app = agent_engines.AdkApp(
        agent=agent,
        app_name="shopper_simulator_app",
        enable_tracing=True,
    )

    existing = find_agent_by_display_name(display_name)

    if existing:
        print(f"Deleting existing deployment: {existing}")
        agent_engines.delete(existing, force=True)
        print("  Deleted.")

    print("Creating new deployment...")
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        requirements=[
            "google-adk>=1.19.0",
            "google-cloud-aiplatform",
        ],
    )
    print(f"Deployed: {remote_app.resource_name}")
    return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy()
    print(f"\nSimulator Agent deployed: {resource_name}")
