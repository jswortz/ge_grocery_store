"""A2A cross-agent communication tool.

Enables the main grocery assistant to delegate tasks to the A2A-enabled
agent running on Cloud Run. This demonstrates the Agent-to-Agent protocol
for cross-agent collaboration in a production setting.

The A2A agent endpoint is configured via config/settings.yaml:
    project.a2a_cloud_run_url
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
    """Delegate a simulation task to the A2A shopper simulator agent.

    Sends a task to the A2A agent running on Cloud Run, which wraps the
    shopper simulator. Use this when users ask to simulate shopper behavior,
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
    a2a_url = config.get("project", {}).get("a2a_cloud_run_url", "")

    if not a2a_url:
        return {
            "status": "error",
            "message": "A2A agent URL not configured in settings.yaml",
        }

    # Build A2A task request
    a2a_endpoint = f"{a2a_url}/a2a"

    # Get auth token for Cloud Run
    try:
        credentials, _ = google.auth.default()
        auth_request = google.auth.transport.requests.Request()
        credentials.refresh(auth_request)
        token = credentials.token
    except Exception as e:
        logger.warning("Could not get auth token: %s", e)
        token = None

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # A2A protocol task message
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"{task_description}\n\n"
                            f"Store: {store_name}\n"
                            f"Scenario: {scenario}\n"
                            f"Number of shoppers: {num_shoppers}"
                        ),
                    }
                ],
            },
        },
        "id": "a2a-sim-request",
    }

    try:
        resp = requests.post(a2a_endpoint, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        result = resp.json()

        # Extract the response text from A2A protocol response
        task_result = result.get("result", {})
        artifacts = task_result.get("artifacts", [])
        response_text = ""
        for artifact in artifacts:
            for part in artifact.get("parts", []):
                if "text" in part:
                    response_text += part["text"]

        if not response_text:
            # Try extracting from task status message
            status = task_result.get("status", {})
            message = status.get("message", {})
            for part in message.get("parts", []):
                if "text" in part:
                    response_text += part["text"]

        return {
            "status": "success",
            "store": store_name,
            "scenario": scenario,
            "num_shoppers": num_shoppers,
            "simulation_results": response_text or json.dumps(task_result),
        }

    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "message": "Simulation request timed out. Try with fewer shoppers.",
        }
    except Exception as e:
        logger.error("A2A delegation failed: %s", e)
        return {
            "status": "error",
            "message": f"Failed to reach A2A agent: {str(e)}",
        }


def create_a2a_tool():
    """Create a FunctionTool for A2A cross-agent delegation."""
    from google.adk.tools import FunctionTool

    return FunctionTool(func=delegate_to_simulator)
