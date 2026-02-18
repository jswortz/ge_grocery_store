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


def _build_store_context(store_name: str, scenario_key: str) -> str:
    """Build a textual description of the store layout with endcap placements."""
    layout = _STORE_LAYOUTS.get(store_name, _STORE_LAYOUTS["Downtown Market"])
    scenario = _STRATEGIES.get(scenario_key, _STRATEGIES["baseline"])

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
                f"{ec['product']} — {ec['discount']} ({ec['display_type']})\n"
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
    store_context = _build_store_context(store_name, scenario_key)
    return f"""You are simulating a shopper at {_RETAILER_NAME}'s {store_name}.

Your Persona: {persona['name']}
{persona['description']}
Budget: ${persona['budget']:.2f}
Preferences: {persona['preferences']}
Loyalty Tier: {persona['loyalty_tier']}
Impulse Buy Tendency: {int(persona['impulse_tendency'] * 100)}%
{persona['demographics']}
{persona['endcap_note']}

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
{{{{
  "persona": "{persona['name']}",
  "aisles_visited": [
    {{{{
      "aisle": "Produce",
      "items": [{{{{"product": "Bananas", "quantity": 1, "price": 1.29}}}}],
      "endcap_interaction": {{{{"product": "Nano Banana Pro", "picked_up": true, "reason": "good deal"}}}}
    }}}}
  ],
  "cart": [{{{{"product": "Bananas", "quantity": 1, "price": 1.29}}}}],
  "total_spend": 45.67,
  "endcap_items": ["Nano Banana Pro"],
  "experience_rating": 4,
  "endcap_influenced": true
}}}}"""


def _build_simulator_agent():
    """Build a fully self-contained simulator agent for Agent Engine.

    This inlines all the store layout, scenario, and persona data so
    the pickled agent has zero external module dependencies.

    Key enhancement: supports marketing endcap A/B testing via the
    compare_endcap_strategies tool, allowing users to pit two strategies
    against each other to measure relative efficacy on conversion,
    revenue lift, and ROI.
    """
    import json
    import random

    from google.adk.agents import LlmAgent
    from google.adk.planners import BuiltInPlanner
    from google.adk.tools import FunctionTool
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

    strategy_list = "\n".join(
        f"  - {key}: {s['name']}" for key, s in _STRATEGIES.items()
    )

    # ── Marketing Endcap A/B Comparison Tool ─────────────────────────────

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
            strategy_a: First strategy key to test. Available:
                baseline, seasonal_produce, snack_impulse, health_wellness,
                premium_cross_merch, back_to_school, planogram_produce_forward,
                planogram_perimeter_flow, planogram_impulse_corridor
            strategy_b: Second strategy key to compare against strategy_a.
            store: Store name (Downtown Market, Westside Market, Lakefront Market).
            num_shoppers: Number of shoppers per strategy (1-12). Same personas
                used in both arms for controlled comparison.

        Returns:
            Dict with side-by-side metrics: conversion rates, revenue,
            endcap lift, and a winner recommendation.
        """
        s_a = _STRATEGIES.get(strategy_a)
        s_b = _STRATEGIES.get(strategy_b)
        if not s_a:
            return {"status": "error", "message": f"Unknown strategy_a: '{strategy_a}'. Available: {list(_STRATEGIES.keys())}"}
        if not s_b:
            return {"status": "error", "message": f"Unknown strategy_b: '{strategy_b}'. Available: {list(_STRATEGIES.keys())}"}

        layout = _STORE_LAYOUTS.get(store, _STORE_LAYOUTS["Downtown Market"])
        num_shoppers = max(1, min(num_shoppers, len(_PERSONAS)))

        # Select personas (weighted by distribution)
        weights = [p.get("distribution_weight", 1 / len(_PERSONAS)) for p in _PERSONAS]
        total_w = sum(weights)
        norm = [w / total_w for w in weights]
        selected_indices = []
        available = list(range(len(_PERSONAS)))
        for _ in range(num_shoppers):
            if not available:
                break
            aw = [norm[i] for i in available]
            tw = sum(aw)
            if tw == 0:
                break
            nw = [w / tw for w in aw]
            chosen = random.choices(available, weights=nw, k=1)[0]
            selected_indices.append(chosen)
            available.remove(chosen)
        selected = [_PERSONAS[i] for i in selected_indices]

        def _simulate_arm(strategy_key, strategy_data):
            """Deterministically simulate shoppers for one strategy arm."""
            results = []
            for p in selected:
                endcaps = strategy_data.get("endcaps", [])
                cart_items = []
                endcap_pickups = []
                spend = 0.0

                # Walk aisles and make purchasing decisions
                for aisle in layout["aisles"]:
                    # Base purchases based on category preferences
                    pref_key = aisle["name"].lower().split(" ")[0]
                    cat_prefs = {"produce": 0.7, "bakery": 0.5, "dairy": 0.6,
                                 "meat": 0.5, "frozen": 0.4, "beverages": 0.5,
                                 "snacks": 0.5, "pantry": 0.5, "health": 0.4,
                                 "household": 0.3, "international": 0.3, "seafood": 0.5}
                    base_prob = cat_prefs.get(pref_key, 0.4)
                    if random.random() < base_prob:
                        item_price = round(random.uniform(1.50, 8.99), 2)
                        if spend + item_price <= p["budget"]:
                            cart_items.append({"product": f"{aisle['name']} item", "price": item_price})
                            spend += item_price

                    # Check endcap interactions
                    for ec in endcaps:
                        if ec["location"] == aisle["name"]:
                            impulse = p["impulse_tendency"]
                            # Higher discount = higher pickup probability
                            discount_boost = 0.15 if "%" in ec.get("discount", "") else 0.10
                            pickup_prob = impulse * 0.6 + discount_boost + 0.1
                            pickup_prob = min(pickup_prob, 0.95)

                            if random.random() < pickup_prob:
                                endcap_pickups.append(ec["product"])
                                # Estimate endcap item price
                                ec_price = round(random.uniform(2.99, 12.99), 2)
                                if spend + ec_price <= p["budget"]:
                                    cart_items.append({"product": ec["product"], "price": ec_price})
                                    spend += ec_price

                results.append({
                    "persona": p["name"],
                    "persona_id": p["id"],
                    "total_spend": round(spend, 2),
                    "cart_size": len(cart_items),
                    "endcap_pickups": endcap_pickups,
                    "endcap_converted": len(endcap_pickups) > 0,
                    "impulse_tendency": p["impulse_tendency"],
                    "budget": p["budget"],
                })
            return results

        results_a = _simulate_arm(strategy_a, s_a)
        results_b = _simulate_arm(strategy_b, s_b)

        def _arm_metrics(results, strategy_data):
            n = len(results)
            total_rev = sum(r["total_spend"] for r in results)
            converted = sum(1 for r in results if r["endcap_converted"])
            conv_rate = (converted / n * 100) if n > 0 else 0
            avg_spend = total_rev / n if n > 0 else 0
            avg_cart = sum(r["cart_size"] for r in results) / n if n > 0 else 0
            total_pickups = sum(len(r["endcap_pickups"]) for r in results)
            return {
                "total_revenue": round(total_rev, 2),
                "conversion_rate": round(conv_rate, 1),
                "avg_spend": round(avg_spend, 2),
                "avg_cart_size": round(avg_cart, 1),
                "total_endcap_pickups": total_pickups,
                "shoppers": n,
            }

        metrics_a = _arm_metrics(results_a, s_a)
        metrics_b = _arm_metrics(results_b, s_b)

        # Determine winner
        score_a = metrics_a["conversion_rate"] * 0.4 + (metrics_a["total_revenue"] / max(metrics_b["total_revenue"], 1)) * 30 + metrics_a["total_endcap_pickups"] * 3
        score_b = metrics_b["conversion_rate"] * 0.4 + (metrics_b["total_revenue"] / max(metrics_a["total_revenue"], 1)) * 30 + metrics_b["total_endcap_pickups"] * 3
        if score_a > score_b * 1.05:
            winner = strategy_a
        elif score_b > score_a * 1.05:
            winner = strategy_b
        else:
            winner = "tie (within 5% margin)"

        rev_lift = metrics_b["total_revenue"] - metrics_a["total_revenue"]
        conv_lift = metrics_b["conversion_rate"] - metrics_a["conversion_rate"]

        return {
            "status": "success",
            "comparison": {
                "strategy_a": {
                    "key": strategy_a,
                    "name": s_a["name"],
                    "description": s_a.get("description", ""),
                    "endcap_count": len(s_a.get("endcaps", [])),
                    "metrics": metrics_a,
                    "shopper_details": results_a,
                },
                "strategy_b": {
                    "key": strategy_b,
                    "name": s_b["name"],
                    "description": s_b.get("description", ""),
                    "endcap_count": len(s_b.get("endcaps", [])),
                    "metrics": metrics_b,
                    "shopper_details": results_b,
                },
                "delta": {
                    "revenue_lift": round(rev_lift, 2),
                    "conversion_lift": round(conv_lift, 1),
                    "revenue_lift_pct": round((rev_lift / max(metrics_a["total_revenue"], 1)) * 100, 1),
                },
                "winner": winner,
            },
            "store": store,
            "num_shoppers_per_arm": num_shoppers,
            "available_strategies": list(_STRATEGIES.keys()),
        }

    def list_endcap_strategies() -> dict:
        """List all available endcap merchandising strategies for simulation.

        Returns the full catalog of strategies including their endcap placements,
        discount types, and display configurations. Use this to help users
        choose which strategies to test or compare.

        Returns:
            Dict with all strategy keys, names, descriptions, and endcap details.
        """
        strategies = {}
        for key, s in _STRATEGIES.items():
            strategies[key] = {
                "name": s["name"],
                "description": s.get("description", ""),
                "endcap_count": len(s.get("endcaps", [])),
                "endcaps": [
                    {
                        "location": ec["location"],
                        "product": ec["product"],
                        "discount": ec["discount"],
                        "display_type": ec["display_type"],
                    }
                    for ec in s.get("endcaps", [])
                ],
            }
        return {
            "status": "success",
            "strategies": strategies,
            "stores": list(_STORE_LAYOUTS.keys()),
        }

    compare_tool = FunctionTool(func=compare_endcap_strategies)
    list_tool = FunctionTool(func=list_endcap_strategies)

    # ── Build shopper sub-agents using clone() pattern ────────────────────

    base_shopper = LlmAgent(
        name="shopper_template",
        model=model,
        planner=planner,
        instruction="template",
        description="template",
    )

    shopper_agents = []
    for p in _PERSONAS:
        shopper_agents.append(
            base_shopper.clone(update={
                "name": f"shopper_{p['id']}",
                "instruction": _build_shopper_instruction(p, store_name, scenario_key),
                "description": f"Simulated shopper: {p['name']} at {store_name}",
            })
        )

    orchestrator = LlmAgent(
        name="simulator_orchestrator",
        model=model,
        planner=planner,
        instruction=f"""You are a retail simulation orchestrator for {retailer}.
You manage a world-model simulation of shoppers to evaluate merchandising
strategies and endcap placement effectiveness.

Default Store: {store_name}
Default Scenario: {_STRATEGIES[scenario_key]['name']}

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
   users all available endcap configurations they can test. Each strategy
   includes specific product placements, discount types, and display formats.

When presenting A/B test results, always include:
- Side-by-side conversion rates (% of shoppers who picked up endcap items)
- Revenue comparison (total and per-shopper average)
- Endcap pickup counts and which products converted best
- A clear winner recommendation with rationale
- Suggestions for optimizing the winning strategy further""",
        description=(
            "Orchestrates simulated shopper agents to evaluate store merchandising "
            "strategies and endcap placement effectiveness. Supports A/B testing "
            "of different marketing endcap configurations."
        ),
        sub_agents=shopper_agents,
        tools=[compare_tool, list_tool],
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

    env_vars = {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        "GOOGLE_CLOUD_LOCATION": "global",  # Gemini 3 models require global endpoint
    }

    print("Creating new deployment...")
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        requirements=[
            "google-adk>=1.19.0",
            "google-cloud-aiplatform",
        ],
        env_vars=env_vars,
    )
    print(f"Deployed: {remote_app.resource_name}")
    return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy()
    print(f"\nSimulator Agent deployed: {resource_name}")
