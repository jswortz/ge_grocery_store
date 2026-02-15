"""Run evaluations against the deployed Shopper Simulator on Agent Engine.

Uses the Vertex AI GenAI evaluation SDK to run inference and evaluation
against the deployed agent. Results appear in the Agent Engine console
under "Evaluation runs".

Per the Agent Engine evaluation guide:
  https://docs.cloud.google.com/agent-builder/agent-engine/evaluate

Usage:
    python evals/simulator/run_eval.py

Requires:
    - google-genai >= 1.63.0
    - Deployed simulator agent on Agent Engine
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
GCS_DEST = "gs://wortz-project-352116-ge-workshop/evals/simulator"
SIMULATOR_AGENT_ENGINE_ID = "256585331992690688"

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
        # The prompt combines starting_prompt and conversation_plan
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


def load_eval_config() -> dict:
    """Load eval criteria from eval_config.json."""
    with open(EVAL_CONFIG_PATH) as f:
        return json.load(f)


def run_evaluation():
    """Run inference + evaluation against the deployed simulator agent."""
    print("=" * 80)
    print("RUNNING SIMULATOR AGENT EVALUATION (Agent Engine API)")
    print("=" * 80)

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = Client(
        project=PROJECT_ID,
        location=LOCATION,
        http_options=genai_types.HttpOptions(api_version="v1beta1"),
    )

    agent_resource = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/reasoningEngines/{SIMULATOR_AGENT_ENGINE_ID}"
    )

    eval_dataset = load_eval_dataset()
    eval_config = load_eval_config()

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
    print(f"  Results type: {type(dataset_with_inference).__name__}")

    # Step 2: Create evaluation run with metrics
    print("\n[Step 2] Creating evaluation run...")

    metrics = [
        types.RubricMetric.FINAL_RESPONSE_QUALITY,
        types.RubricMetric.TOOL_USE_QUALITY,
        types.RubricMetric.HALLUCINATION,
        types.RubricMetric.SAFETY,
    ]

    print(f"  Metrics: {[m.__class__.__name__ for m in metrics]}")

    # Link eval run to the deployed agent so it appears in the console
    agent_info = types.evals.AgentInfo(
        agent_resource_name=agent_resource,
        name="Shopper Simulator",
        description="12-persona shopper simulator testing planogram layouts",
    )

    evaluation_run = client.evals.create_evaluation_run(
        dataset=dataset_with_inference,
        metrics=metrics,
        dest=GCS_DEST,
        display_name="Simulator Planogram Eval",
        agent_info=agent_info,
    )

    print(f"\n  Evaluation run created: {evaluation_run.name}")

    # Step 3: Retrieve and display results
    print("\n[Step 3] Retrieving results...")
    evaluation_run = client.evals.get_evaluation_run(
        name=evaluation_run.name,
        include_evaluation_items=True,
    )

    # Print results
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
