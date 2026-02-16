"""Traffic simulator for deployed grocery retail agents.

Sends synthetic multi-turn conversations to all deployed agents via the
Agent Engine REST API. Uses eval scenarios as conversation seeds to generate
diverse query patterns that populate telemetry, sessions, and usage metrics.

Usage:
    python scripts/traffic_simulator.py
    python scripts/traffic_simulator.py --agents main --queries 5
    python scripts/traffic_simulator.py --agents main,mcp --queries 10

Requires:
    - Valid GCP credentials (gcloud auth application-default login)
    - Deployed agents on Agent Engine (IDs in config/settings.yaml)
"""

import argparse
import json
import logging
import random
import time
from pathlib import Path

import google.auth
import google.auth.transport.requests
import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"

PROJECT_NUMBER = "679926387543"
LOCATION = "us-central1"

# Agent definitions
AGENTS = {
    "main": {
        "config_key": "agent_engine_id",
        "display_name": "Grocery Assistant",
        "scenarios_file": "grocery_assistant/scenarios.json",
    },
    "mcp": {
        "config_key": "mcp_agent_engine_id",
        "display_name": "MCP Grocery Analyst",
        "scenarios_file": "mcp_analyst/scenarios.json",
    },
    "simulator": {
        "config_key": "simulator_agent_engine_id",
        "display_name": "Shopper Simulator",
        "scenarios_file": "simulator/scenarios.json",
    },
}

# Additional ad-hoc queries to supplement eval scenarios
ADHOC_QUERIES = {
    "main": [
        "What are the closing procedures for frontline associates?",
        "Show me the brand typography standards",
        "What are the top 10 products by units sold?",
        "What store has the highest revenue?",
        "What are the SOP guidelines for handling food recalls?",
        "What is our return policy for perishable items?",
        "Generate a product image for organic avocados",
        "What are current retail trends in sustainable packaging?",
        "How many Gold loyalty tier customers do we have?",
        "What payment methods are most popular?",
    ],
    "mcp": [
        "What tables are available in the grocery dataset?",
        "Show me revenue by store for the last quarter",
        "What is the average transaction amount by payment method?",
        "Which employees have the most transactions?",
        "What are the top 5 product categories by revenue?",
        "Show me customer distribution by loyalty tier",
        "What is the average basket size by store?",
        "Which products have the highest unit price?",
        "How many customers signed up this year?",
        "What is the revenue trend by month?",
    ],
    "simulator": [
        "Run a baseline simulation with 3 shoppers at Downtown Market",
        "Simulate the seasonal produce endcap strategy",
        "Compare baseline vs promotional endcap performance",
    ],
}

# Simulated user IDs for traffic diversity
TRAFFIC_USER_IDS = [
    "traffic-user-alpha",
    "traffic-user-beta",
    "traffic-user-gamma",
    "traffic-user-delta",
    "traffic-user-epsilon",
]


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _get_token():
    """Get a valid access token using ADC."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


def _load_scenarios(scenarios_file: str) -> list[str]:
    """Load starting prompts from an eval scenarios file."""
    path = EVALS_DIR / scenarios_file
    if not path.exists():
        return []

    with open(path) as f:
        data = json.load(f)

    prompts = []
    for case in data.get("eval_cases", []):
        scenario = case.get("conversation_scenario", {})
        prompt = scenario.get("starting_prompt", "")
        if prompt:
            prompts.append(prompt)
    return prompts


def _query_agent(agent_id: str, message: str, user_id: str, token: str) -> dict:
    """Send a query to an Agent Engine deployment."""
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1"
        f"/projects/{PROJECT_NUMBER}/locations/{LOCATION}"
        f"/reasoningEngines/{agent_id}:streamQuery"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "message": message,
            "user_id": user_id,
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    return {
        "status_code": resp.status_code,
        "success": resp.ok,
        "response_length": len(resp.text),
        "trace_id": resp.headers.get("x-cloud-trace-context", "").split("/")[0],
    }


def run_traffic(
    config: dict,
    agent_keys: list[str],
    num_queries: int,
    delay: float = 2.0,
):
    """Run traffic simulation against specified agents."""
    token = _get_token()
    project = config.get("project", {})

    results = {"agents": {}, "total_queries": 0, "total_success": 0, "total_failures": 0}

    for agent_key in agent_keys:
        agent_def = AGENTS[agent_key]
        agent_id = project.get(agent_def["config_key"], "")
        if not agent_id:
            logger.warning("No agent ID for %s, skipping", agent_key)
            continue

        logger.info("=" * 60)
        logger.info("Agent: %s (%s)", agent_def["display_name"], agent_id)
        logger.info("=" * 60)

        # Build query pool from scenarios + ad-hoc queries
        queries = _load_scenarios(agent_def["scenarios_file"])
        queries.extend(ADHOC_QUERIES.get(agent_key, []))

        if not queries:
            logger.warning("No queries available for %s", agent_key)
            continue

        # Select queries for this run
        selected = []
        for _ in range(num_queries):
            selected.append(random.choice(queries))

        agent_results = {"queries": 0, "success": 0, "failures": 0, "details": []}

        for i, query in enumerate(selected, 1):
            user_id = random.choice(TRAFFIC_USER_IDS)
            logger.info("  [%d/%d] User=%s Query=%s", i, num_queries, user_id, query[:60])

            try:
                result = _query_agent(agent_id, query, user_id, token)
                agent_results["queries"] += 1

                if result["success"]:
                    agent_results["success"] += 1
                    logger.info("    -> OK (%d bytes, trace=%s)",
                                result["response_length"], result["trace_id"][:12] or "none")
                else:
                    agent_results["failures"] += 1
                    logger.warning("    -> FAILED (HTTP %d)", result["status_code"])

                agent_results["details"].append({
                    "query": query,
                    "user_id": user_id,
                    **result,
                })

            except Exception as e:
                agent_results["queries"] += 1
                agent_results["failures"] += 1
                logger.error("    -> ERROR: %s", e)
                agent_results["details"].append({
                    "query": query,
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                })

            # Delay between queries to avoid rate limiting
            if i < num_queries:
                time.sleep(delay)

        results["agents"][agent_key] = agent_results
        results["total_queries"] += agent_results["queries"]
        results["total_success"] += agent_results["success"]
        results["total_failures"] += agent_results["failures"]

        logger.info("  Summary: %d/%d successful",
                     agent_results["success"], agent_results["queries"])

    # Final report
    logger.info("")
    logger.info("=" * 60)
    logger.info("TRAFFIC SIMULATION COMPLETE")
    logger.info("=" * 60)
    logger.info("Total queries: %d", results["total_queries"])
    logger.info("Successful:    %d", results["total_success"])
    logger.info("Failed:        %d", results["total_failures"])
    if results["total_queries"] > 0:
        rate = results["total_success"] / results["total_queries"] * 100
        logger.info("Success rate:  %.1f%%", rate)

    return results


def main():
    parser = argparse.ArgumentParser(description="Traffic simulator for deployed agents")
    parser.add_argument(
        "--agents",
        default="main,mcp",
        help="Comma-separated agent keys to target (main, mcp, simulator)",
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=5,
        help="Number of queries per agent (default: 5)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between queries in seconds (default: 2.0)",
    )
    args = parser.parse_args()

    agent_keys = [k.strip() for k in args.agents.split(",")]
    for k in agent_keys:
        if k not in AGENTS:
            parser.error(f"Unknown agent key: {k}. Must be one of: {', '.join(AGENTS)}")

    config = _load_config()
    run_traffic(config, agent_keys, args.queries, args.delay)


if __name__ == "__main__":
    main()
