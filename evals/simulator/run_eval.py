"""Run ADK evaluations against the deployed Shopper Simulator on Agent Engine.

Per the Agent Engine evaluation guide:
  https://docs.cloud.google.com/agent-builder/agent-engine/evaluate

Usage:
    python evals/simulator/run_eval.py

Requires:
    - google-cloud-aiplatform >= 1.87.0
    - Deployed simulator agent on Agent Engine
    - gcloud auth application-default login
"""

import json
from pathlib import Path

import vertexai
from google import genai
from google.genai import types

PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
GCS_BUCKET = "gs://wortz-project-352116-ge-workshop"
SIMULATOR_AGENT_ENGINE_ID = "2103624129168015360"

EVAL_DIR = Path(__file__).parent
SCENARIOS_PATH = EVAL_DIR / "scenarios.json"
EVAL_CONFIG_PATH = EVAL_DIR / "eval_config.json"


def load_eval_dataset() -> list[dict]:
    """Load eval scenarios from scenarios.json."""
    with open(SCENARIOS_PATH) as f:
        data = json.load(f)

    dataset = []
    for case in data["eval_cases"]:
        dataset.append({
            "eval_id": case["eval_id"],
            "starting_prompt": case["conversation_scenario"]["starting_prompt"],
            "conversation_plan": case["conversation_scenario"]["conversation_plan"],
        })
    return dataset


def load_eval_config() -> dict:
    """Load eval criteria from eval_config.json."""
    with open(EVAL_CONFIG_PATH) as f:
        return json.load(f)


def run_evaluation():
    """Run inference + evaluation against the deployed simulator agent."""
    print("=" * 80)
    print("RUNNING SIMULATOR AGENT EVALUATION")
    print("=" * 80)

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    eval_dataset = load_eval_dataset()
    eval_config = load_eval_config()

    agent_resource = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}"
        f"/reasoningEngines/{SIMULATOR_AGENT_ENGINE_ID}"
    )

    print(f"\nAgent: {agent_resource}")
    print(f"Eval cases: {len(eval_dataset)}")
    print(f"Metrics: {list(eval_config['criteria'].keys())}")

    # Build eval set in the format expected by the API
    eval_cases = []
    for case in eval_dataset:
        eval_cases.append(
            types.EvalCase(
                eval_case_id=case["eval_id"],
                conversation_scenario=types.ConversationScenario(
                    starting_prompt=case["starting_prompt"],
                    conversation_plan=case["conversation_plan"],
                ),
            )
        )

    eval_set = types.EvalSet(
        eval_set_id="simulator_eval",
        eval_cases=eval_cases,
    )

    # Step 1: Run inference against the deployed agent
    print("\n[Step 1] Running inference against deployed agent...")
    dataset_with_inference = client.evals.run_inference(
        agent=agent_resource,
        eval_set=eval_set,
        config=types.RunInferenceConfig(
            eval_run_id="sim_eval_run",
        ),
    )
    print("  Inference complete.")

    # Step 2: Evaluate the results
    print("\n[Step 2] Evaluating results...")
    metrics = []
    criteria = eval_config.get("criteria", {})

    if "rubric_based_final_response_quality_v1" in criteria:
        metrics.append(types.EvalMetric(
            metric_name="rubric_based_final_response_quality_v1",
        ))
    if "hallucinations_v1" in criteria:
        metrics.append(types.EvalMetric(
            metric_name="hallucinations_v1",
        ))
    if "safety_v1" in criteria:
        metrics.append(types.EvalMetric(
            metric_name="safety_v1",
        ))
    metrics.append(types.EvalMetric(
        metric_name="tool_use_quality_v1",
    ))

    evaluation_run = client.evals.evaluate(
        eval_set=dataset_with_inference,
        metrics=metrics,
        config=types.EvaluateConfig(
            eval_run_id="sim_eval_run",
        ),
    )

    # Print results
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)

    for result in evaluation_run.eval_cases:
        print(f"\n--- {result.eval_case_id} ---")
        for metric_result in result.metric_results or []:
            print(f"  {metric_result.metric_name}: {metric_result.score}")

    print(f"\nResults stored for agent: {agent_resource}")
    return evaluation_run


if __name__ == "__main__":
    run_evaluation()
