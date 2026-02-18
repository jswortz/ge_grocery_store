"""Run evaluations for all deployed Agent Engine agents.

Orchestrates evaluation runs for all 4 deployed agents:
1. Grocery Retail Assistant (main ADK agent)
2. MCP BigQuery Analyst
3. Shopper Simulator
4. A2A Agent

Each agent's inference is run against its deployed Agent Engine instance,
and evaluation metrics are computed and stored in GCS. Results are also
visible in the Agent Engine console.

Usage:
    # Run all evaluations
    python evals/run_all_evals.py

    # Run a specific agent's evaluation
    python evals/run_all_evals.py --agent grocery_assistant
    python evals/run_all_evals.py --agent mcp_analyst
    python evals/run_all_evals.py --agent simulator
    python evals/run_all_evals.py --agent a2a_agent

Requires:
    - google-genai >= 1.63.0
    - pandas >= 2.1.0
    - gcloud auth application-default login
    - All agents deployed on Agent Engine
"""

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import vertexai
from google.genai import types as genai_types
from vertexai import Client, types

PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
GCS_BUCKET = "gs://wortz-project-352116-ge-workshop/evals"

EVALS_DIR = Path(__file__).parent

# Agent registry: maps agent name to its config
AGENTS = {
    "grocery_assistant": {
        "engine_id": "3727910666648944640",
        "display_name": "Grocery Retail Assistant",
        "description": (
            "Multi-agent grocery assistant with SOP search, brand guidelines, "
            "analytics delegation, and product image generation"
        ),
        "eval_dir": EVALS_DIR / "grocery_assistant",
        "metrics": [
            types.RubricMetric.FINAL_RESPONSE_QUALITY,
            types.RubricMetric.HALLUCINATION,
            types.RubricMetric.SAFETY,
        ],
    },
    "mcp_analyst": {
        "engine_id": "5787744546217525248",
        "display_name": "MCP Grocery Analyst",
        "description": (
            "BigQuery analytics agent using MCP Toolbox for Databases. "
            "Generates arbitrary SQL for grocery retail data analysis."
        ),
        "eval_dir": EVALS_DIR / "mcp_analyst",
        "metrics": [
            types.RubricMetric.FINAL_RESPONSE_QUALITY,
            types.RubricMetric.TOOL_USE_QUALITY,
            types.RubricMetric.HALLUCINATION,
            types.RubricMetric.SAFETY,
        ],
    },
    "simulator": {
        "engine_id": "7053256041508634624",
        "display_name": "Shopper Simulator",
        "description": (
            "12-persona shopper simulator testing planogram layouts "
            "and endcap merchandising strategies"
        ),
        "eval_dir": EVALS_DIR / "simulator",
        "metrics": [
            types.RubricMetric.FINAL_RESPONSE_QUALITY,
            types.RubricMetric.TOOL_USE_QUALITY,
            types.RubricMetric.HALLUCINATION,
            types.RubricMetric.SAFETY,
        ],
    },
    "a2a_agent": {
        "engine_id": "2240491336593571840",
        "display_name": "A2A Grocery Assistant",
        "description": (
            "A2A protocol-enabled grocery retail assistant. Supports SOP "
            "lookup, brand guidelines, analytics, and image generation "
            "via agent-to-agent protocol."
        ),
        "eval_dir": EVALS_DIR / "a2a_agent",
        "metrics": [
            types.RubricMetric.FINAL_RESPONSE_QUALITY,
            types.RubricMetric.HALLUCINATION,
            types.RubricMetric.SAFETY,
        ],
    },
}


def load_eval_dataset(eval_dir: Path) -> pd.DataFrame:
    """Load eval scenarios from scenarios.json into a DataFrame."""
    scenarios_path = eval_dir / "scenarios.json"
    with open(scenarios_path) as f:
        data = json.load(f)

    prompts = []
    session_inputs_list = []
    for case in data["eval_cases"]:
        scenario = case["conversation_scenario"]
        prompt = (
            f"{scenario['starting_prompt']}\n\n"
            f"Follow-up plan: {scenario['conversation_plan']}"
        )
        prompts.append(prompt)
        session_inputs_list.append(
            types.evals.SessionInput(
                user_id=f"eval_user_{case['eval_id']}",
                state={},
            )
        )

    return pd.DataFrame({
        "prompt": prompts,
        "session_inputs": session_inputs_list,
    })


def run_agent_evaluation(
    client: Client,
    agent_name: str,
    agent_config: dict,
) -> dict:
    """Run evaluation for a single agent.

    Returns:
        Dict with eval_run_name and status.
    """
    engine_id = agent_config["engine_id"]
    eval_dir = agent_config["eval_dir"]
    gcs_dest = f"{GCS_BUCKET}/{agent_name}"

    agent_resource = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/reasoningEngines/{engine_id}"
    )

    print(f"\n{'=' * 80}")
    print(f"EVALUATING: {agent_config['display_name']}")
    print(f"  Agent: {agent_resource}")
    print(f"  GCS: {gcs_dest}")
    print(f"{'=' * 80}")

    eval_dataset = load_eval_dataset(eval_dir)
    print(f"  Eval cases: {len(eval_dataset)}")

    # Step 1: Run inference
    print("\n  [Step 1] Running inference...")
    dataset_with_inference = client.evals.run_inference(
        agent=agent_resource,
        src=eval_dataset,
    )
    print("  Inference complete.")

    # Step 2: Create evaluation run
    print("  [Step 2] Creating evaluation run...")

    agent_info = types.evals.AgentInfo(
        agent_resource_name=agent_resource,
        name=agent_config["display_name"],
        description=agent_config["description"],
    )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    evaluation_run = client.evals.create_evaluation_run(
        dataset=dataset_with_inference,
        metrics=agent_config["metrics"],
        dest=gcs_dest,
        display_name=f"{agent_config['display_name']} Eval {timestamp}",
        agent_info=agent_info,
    )

    print(f"  Evaluation run: {evaluation_run.name}")

    # Step 3: Show results
    print("  [Step 3] Retrieving results...")
    evaluation_run = client.evals.get_evaluation_run(
        name=evaluation_run.name,
        include_evaluation_items=True,
    )

    if hasattr(evaluation_run, 'show'):
        evaluation_run.show()
    else:
        print(f"  Run: {evaluation_run.name}")
        if hasattr(evaluation_run, 'state'):
            print(f"  State: {evaluation_run.state}")

    return {
        "agent": agent_name,
        "eval_run_name": evaluation_run.name,
        "status": "completed",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run Agent Engine evaluations for all deployed agents"
    )
    parser.add_argument(
        "--agent",
        choices=list(AGENTS.keys()),
        help="Run evaluation for a specific agent only",
    )
    args = parser.parse_args()

    agents_to_eval = (
        {args.agent: AGENTS[args.agent]} if args.agent else AGENTS
    )

    print("=" * 80)
    print("AGENT ENGINE EVALUATION RUNNER")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Agents: {', '.join(agents_to_eval.keys())}")
    print(f"  Time: {datetime.now().isoformat()}")
    print("=" * 80)

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = Client(
        project=PROJECT_ID,
        location=LOCATION,
        http_options=genai_types.HttpOptions(api_version="v1beta1"),
    )

    results = []
    failures = []

    for agent_name, agent_config in agents_to_eval.items():
        try:
            result = run_agent_evaluation(client, agent_name, agent_config)
            results.append(result)
        except Exception as e:
            print(f"\n  ERROR evaluating {agent_name}: {e}")
            traceback.print_exc()
            failures.append({"agent": agent_name, "error": str(e)})

    # Summary
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    print(f"\nCompleted: {len(results)}/{len(agents_to_eval)}")
    for r in results:
        print(f"  {r['agent']}: {r['eval_run_name']}")

    if failures:
        print(f"\nFailed: {len(failures)}")
        for f in failures:
            print(f"  {f['agent']}: {f['error']}")

    print(f"\nResults visible in Agent Engine console:")
    print(f"  https://console.cloud.google.com/vertex-ai/agents?project={PROJECT_ID}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
