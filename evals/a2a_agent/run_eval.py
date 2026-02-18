"""Run evaluations against the deployed A2A Agent on Agent Engine.

Uses the Vertex AI GenAI evaluation SDK to run inference and evaluation
against the deployed agent. Results appear in the Agent Engine console
under "Evaluation runs".

Per the Agent Engine evaluation guide:
  https://docs.cloud.google.com/agent-builder/agent-engine/evaluate

Usage:
    python evals/a2a_agent/run_eval.py

Requires:
    - google-genai >= 1.63.0
    - Deployed A2A agent on Agent Engine
    - gcloud auth application-default login
"""

import json
from pathlib import Path

import pandas as pd
import vertexai
from google.genai import types as genai_types
from vertexai import Client, types

PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
GCS_DEST = "gs://wortz-project-352116-ge-workshop/evals/a2a_agent"
AGENT_ENGINE_ID = "2240491336593571840"

EVAL_DIR = Path(__file__).parent
SCENARIOS_PATH = EVAL_DIR / "scenarios.json"
EVAL_CONFIG_PATH = EVAL_DIR / "eval_config.json"


def load_eval_dataset() -> pd.DataFrame:
    """Load eval scenarios from scenarios.json into a DataFrame."""
    with open(SCENARIOS_PATH) as f:
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


def run_evaluation():
    """Run inference + evaluation against the deployed A2A agent."""
    print("=" * 80)
    print("RUNNING A2A AGENT EVALUATION (Agent Engine API)")
    print("=" * 80)

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = Client(
        project=PROJECT_ID,
        location=LOCATION,
        http_options=genai_types.HttpOptions(api_version="v1beta1"),
    )

    agent_resource = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/reasoningEngines/{AGENT_ENGINE_ID}"
    )

    eval_dataset = load_eval_dataset()

    print(f"\nAgent: {agent_resource}")
    print(f"Eval cases: {len(eval_dataset)}")
    print(f"GCS destination: {GCS_DEST}")

    # Step 1: Run inference against the deployed agent
    print("\n[Step 1] Running inference against deployed agent...")
    dataset_with_inference = client.evals.run_inference(
        agent=agent_resource,
        src=eval_dataset,
    )
    print("  Inference complete.")

    # Step 2: Create evaluation run with metrics
    print("\n[Step 2] Creating evaluation run...")

    metrics = [
        types.RubricMetric.FINAL_RESPONSE_QUALITY,
        types.RubricMetric.HALLUCINATION,
        types.RubricMetric.SAFETY,
    ]

    agent_info = types.evals.AgentInfo(
        agent_resource_name=agent_resource,
        name="A2A Grocery Assistant",
        description=(
            "A2A protocol-enabled grocery retail assistant deployed on "
            "Agent Engine. Supports SOP lookup, brand guidelines, "
            "analytics, and image generation via agent-to-agent protocol."
        ),
    )

    evaluation_run = client.evals.create_evaluation_run(
        dataset=dataset_with_inference,
        metrics=metrics,
        dest=GCS_DEST,
        display_name="A2A Agent Eval",
        agent_info=agent_info,
    )

    print(f"\n  Evaluation run created: {evaluation_run.name}")

    # Step 3: Retrieve and display results
    print("\n[Step 3] Retrieving results...")
    evaluation_run = client.evals.get_evaluation_run(
        name=evaluation_run.name,
        include_evaluation_items=True,
    )

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)

    if hasattr(evaluation_run, 'show'):
        evaluation_run.show()
    else:
        print(f"Run name: {evaluation_run.name}")
        if hasattr(evaluation_run, 'state'):
            print(f"State: {evaluation_run.state}")
        if hasattr(evaluation_run, 'results'):
            print(f"Results: {evaluation_run.results}")

    print(f"\nResults visible in Agent Engine console:")
    print(f"  https://console.cloud.google.com/vertex-ai/agents?project={PROJECT_ID}")
    print(f"\nResults stored at: {GCS_DEST}")
    return evaluation_run


if __name__ == "__main__":
    run_evaluation()
