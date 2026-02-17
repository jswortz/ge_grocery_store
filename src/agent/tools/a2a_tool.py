"""Simulator delegation tool.

Enables the main grocery assistant to delegate simulation tasks to the
shopper simulator agent deployed on Agent Engine. This demonstrates
cross-agent collaboration where the orchestrator routes simulation
requests to a specialized agent.

The simulator Agent Engine ID is configured via config/settings.yaml:
    project.simulator_agent_engine_id
"""

import json
import logging

import google.auth
import google.auth.transport.requests
import requests

logger = logging.getLogger(__name__)


def _load_config():
    from ..agent import _load_config as _agent_load_config
    return _agent_load_config()


def delegate_to_simulator(
    task_description: str,
    store_name: str = "Downtown Market",
    scenario: str = "seasonal_produce",
    num_shoppers: int = 3,
) -> dict:
    """Delegate a simulation task to the shopper simulator agent on Agent Engine.

    Sends a simulation request to the shopper simulator deployed on
    Agent Engine. Use this when users ask to simulate shopper behavior,
    test endcap merchandising strategies, or evaluate store layout changes.

    Args:
        task_description: Natural language description of the simulation to run.
        store_name: Store to simulate (Downtown Market, Westside Market, Lakefront Market).
        scenario: Merchandising scenario key (baseline, seasonal_produce, etc.).
        num_shoppers: Number of simulated shoppers (1-8).

    Returns:
        Dict with simulation results or error information.
    """
    config = _load_config()
    project_number = config.get("project", {}).get("number", "")
    location = config.get("memory", {}).get("location", "us-central1")
    simulator_id = config.get("project", {}).get("simulator_agent_engine_id", "")

    if not simulator_id:
        return {
            "status": "error",
            "message": "Simulator Agent Engine ID not configured in settings.yaml",
        }

    # Build Agent Engine streamQuery URL
    ae_base = (
        f"https://{location}-aiplatform.googleapis.com/v1"
        f"/projects/{project_number}/locations/{location}"
        f"/reasoningEngines/{simulator_id}"
    )
    url = f"{ae_base}:streamQuery"

    # Get auth token
    try:
        credentials, _ = google.auth.default()
        auth_request = google.auth.transport.requests.Request()
        credentials.refresh(auth_request)
        token = credentials.token
    except Exception as e:
        logger.warning("Could not get auth token: %s", e)
        return {
            "status": "error",
            "message": f"Authentication failed: {e}",
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Build the simulation prompt
    simulation_prompt = (
        f"{task_description}\n\n"
        f"Store: {store_name}\n"
        f"Scenario: {scenario}\n"
        f"Number of shoppers: {num_shoppers}"
    )

    payload = {
        "input": {
            "message": simulation_prompt,
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()

        # Parse NDJSON response (same format as Agent Engine streamQuery)
        texts = []
        for line in resp.text.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                parts = (event.get("content") or {}).get("parts") or []
                for part in parts:
                    if part.get("text"):
                        texts.append(part["text"])
            except (json.JSONDecodeError, TypeError):
                pass

        response_text = "\n".join(texts)

        return {
            "status": "success",
            "store": store_name,
            "scenario": scenario,
            "num_shoppers": num_shoppers,
            "simulation_results": response_text or "Simulation completed but returned no text output.",
        }

    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "message": "Simulation request timed out. Try with fewer shoppers.",
        }
    except Exception as e:
        logger.error("Simulator delegation failed: %s", e)
        return {
            "status": "error",
            "message": f"Failed to reach simulator agent: {str(e)}",
        }


def create_a2a_tool():
    """Create a FunctionTool for simulator delegation."""
    from google.adk.tools import FunctionTool

    return FunctionTool(func=delegate_to_simulator)
