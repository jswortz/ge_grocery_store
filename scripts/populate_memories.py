"""Populate realistic shopper memories across all deployed agents.

Uses the Vertex AI Memory Bank API to create demo-ready memories
for several user personas. These memories enable the agents to
demonstrate personalized responses during live demos.

Usage:
    python scripts/populate_memories.py

Requires:
    - Valid GCP credentials (gcloud auth application-default login)
    - Deployed agents on Agent Engine (IDs in config/settings.yaml)
"""

import time
from pathlib import Path

import vertexai
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"

PROJECT_ID = "wortz-project-352116"
PROJECT_NUMBER = "679926387543"
LOCATION = "us-central1"


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# Demo user personas with realistic memory facts
DEMO_PERSONAS = {
    "demo-shopper-maria": {
        "description": "Maria - Health-conscious Gold loyalty member",
        "facts": [
            "Customer's name is Maria Garcia",
            "Customer is a Gold loyalty tier member with 12,450 points",
            "Customer always shops at the Downtown Market on Saturday mornings",
            "Customer is allergic to peanuts and tree nuts",
            "Customer prefers organic produce and free-range eggs",
            "Customer follows a Mediterranean diet",
            "Customer's favorite products are Organic Valley Milk and Nano Banana Pro",
            "Customer usually spends $120-150 per weekly shopping trip",
        ],
    },
    "demo-shopper-james": {
        "description": "James - Budget-focused family shopper",
        "facts": [
            "Customer's name is James Thompson",
            "Customer is a Silver loyalty tier member",
            "Customer shops at Westside Market with his family of four",
            "Customer prefers bulk buying for pantry staples",
            "Customer always looks for weekly promotions and BOGO deals",
            "Customer's kids are lactose intolerant",
            "Customer typically visits on Sunday afternoons",
            "Customer's average transaction is around $85",
        ],
    },
    "demo-shopper-sarah": {
        "description": "Sarah - Gourmet cooking enthusiast",
        "facts": [
            "Customer's name is Sarah Chen",
            "Customer is a Gold loyalty tier member with 8,200 points",
            "Customer prefers the Lakefront Market for its seafood selection",
            "Customer is an avid home chef who buys premium ingredients",
            "Customer subscribes to the weekly recipe newsletter",
            "Customer frequently buys imported cheeses and specialty oils",
            "Customer shops on Wednesday evenings after work",
            "Customer asked about catering options for a dinner party last visit",
        ],
    },
    "demo-manager-alex": {
        "description": "Alex - Store manager using analytics",
        "facts": [
            "User is Alex Rivera, Store Manager at Downtown Market",
            "User frequently checks weekly revenue reports by category",
            "User tracks employee performance metrics monthly",
            "User is planning an endcap promotion for organic produce",
            "User wants to compare Downtown Market performance vs other stores",
            "User asked about customer retention rates for Gold tier members last week",
            "User prefers data visualized as tables with percentage changes",
        ],
    },
    "demo-analyst-pat": {
        "description": "Pat - Regional analytics power user",
        "facts": [
            "User is Pat Johnson, Regional Analyst",
            "User runs cross-store comparison reports every Monday",
            "User tracks price elasticity for top 10 products",
            "User monitors inventory turnover rates by category",
            "User needs monthly executive summary with YoY trends",
            "User prefers forecasting with confidence intervals",
            "User is evaluating vendor performance for the Q2 review",
        ],
    },
}


def populate_memories(config: dict):
    """Populate memories for all demo personas across all deployed agents."""
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

    # Get all agent engine IDs
    project = config.get("project", {})
    agent_ids = {}
    for key in ["agent_engine_id", "mcp_agent_engine_id", "simulator_agent_engine_id"]:
        val = project.get(key, "")
        if val:
            agent_ids[key] = val

    if not agent_ids:
        print("ERROR: No agent_engine_id values found in config/settings.yaml")
        return

    print(f"Found {len(agent_ids)} deployed agents:")
    for key, aid in agent_ids.items():
        print(f"  {key}: {aid}")
    print()

    total_memories = 0
    for user_id, persona in DEMO_PERSONAS.items():
        print(f"\nPopulating memories for: {persona['description']}")
        print(f"  User ID: {user_id}")
        print(f"  Facts: {len(persona['facts'])}")

        for agent_key, agent_id in agent_ids.items():
            resource_name = (
                f"projects/{PROJECT_NUMBER}/locations/{LOCATION}"
                f"/reasoningEngines/{agent_id}"
            )

            try:
                client.agent_engines.memories.generate(
                    name=resource_name,
                    direct_memories_source={
                        "direct_memories": [
                            {"fact": fact} for fact in persona["facts"]
                        ]
                    },
                    scope={"user_id": user_id},
                    config={"wait_for_completion": True},
                )
                agent_label = agent_key.replace("_engine_id", "").replace("_agent", "")
                print(f"    -> {agent_label}: OK")
                total_memories += len(persona["facts"])
            except Exception as e:
                print(f"    -> {agent_key}: FAILED ({e})")

        # Brief pause between personas to avoid rate limiting
        time.sleep(1)

    print(f"\nDone. Populated {total_memories} total memory facts across "
          f"{len(DEMO_PERSONAS)} personas and {len(agent_ids)} agents.")
    print("\nVerify with: python -m pytest tests/test_memory_bank.py -v")


def main():
    config = _load_config()
    populate_memories(config)


if __name__ == "__main__":
    main()
