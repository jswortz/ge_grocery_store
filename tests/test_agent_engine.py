"""Integration tests for the deployed ADK agent on Vertex AI Agent Engine.

Tests query the deployed agent via the Agent Engine REST API to verify:
- SOP search (Discovery Engine → sop-store)
- Analytics (BigQuery star schema)
- Brand guidelines search (Discovery Engine → brand-guidelines-store)

Requires:
- Valid GCP credentials
- Agent deployed to Agent Engine (agent_engine_id in config/settings.yaml)
- Run with: pytest -m integration tests/test_agent_engine.py -v
"""

import json
from pathlib import Path

import pytest
import requests
import yaml

import google.auth
from google.auth.transport.requests import Request

pytestmark = pytest.mark.integration

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def config():
    return _load_config()


@pytest.fixture(scope="module")
def agent_engine_id(config):
    ae_id = config["project"].get("agent_engine_id", "")
    if not ae_id:
        pytest.skip("No agent_engine_id configured in settings.yaml")
    return ae_id


@pytest.fixture(scope="module")
def project_number():
    """Resolve project number from credentials."""
    credentials, project = google.auth.default()
    # Use the project number from the service agent resource name format
    # or fall back to a known value
    return "679926387543"


@pytest.fixture(scope="module")
def auth_headers():
    credentials, _ = google.auth.default()
    if not credentials.valid:
        credentials.refresh(Request())
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }


def _stream_query(project_number, agent_engine_id, auth_headers, message, user_id="pytest-user"):
    """Send a query to the deployed agent via REST API and return the final text."""
    url = (
        f"https://us-central1-aiplatform.googleapis.com/v1/"
        f"projects/{project_number}/locations/us-central1/"
        f"reasoningEngines/{agent_engine_id}:streamQuery"
    )
    payload = {
        "input": {
            "message": message,
            "user_id": user_id,
        }
    }
    resp = requests.post(url, headers=auth_headers, json=payload, timeout=120)
    resp.raise_for_status()

    # Response is newline-delimited JSON events
    text_parts = []
    for line in resp.text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            parts = event.get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])
        except json.JSONDecodeError:
            continue

    return "\n".join(text_parts)


class TestAgentEngineSOPSearch:
    """Verify SOP search works on the deployed agent."""

    def test_closing_procedures(self, project_number, agent_engine_id, auth_headers):
        text = _stream_query(
            project_number, agent_engine_id, auth_headers,
            "What are the closing procedures for frontline associates?",
        )
        assert text, "Agent should return closing procedure information"
        text_lower = text.lower()
        assert any(
            term in text_lower
            for term in ["closing", "close", "register", "security", "clean", "lock"]
        ), f"Response should mention closing-related terms, got: {text[:200]}"

    def test_opening_procedures(self, project_number, agent_engine_id, auth_headers):
        text = _stream_query(
            project_number, agent_engine_id, auth_headers,
            "What are the opening procedures?",
        )
        assert text, "Agent should return opening procedure information"
        text_lower = text.lower()
        assert any(
            term in text_lower
            for term in ["opening", "open", "arrive", "safety", "check", "morning"]
        ), f"Response should mention opening-related terms, got: {text[:200]}"


class TestAgentEngineAnalytics:
    """Verify BigQuery analytics works on the deployed agent."""

    def test_top_products(self, project_number, agent_engine_id, auth_headers):
        text = _stream_query(
            project_number, agent_engine_id, auth_headers,
            "What are the top 3 selling products by revenue?",
        )
        assert text, "Agent should return product analytics"
        # Should contain actual product names or revenue figures
        assert any(
            char.isdigit() for char in text
        ), "Response should contain numeric data"

    def test_store_sales(self, project_number, agent_engine_id, auth_headers):
        text = _stream_query(
            project_number, agent_engine_id, auth_headers,
            "Show me total sales by store",
        )
        assert text, "Agent should return store sales data"
        text_lower = text.lower()
        assert any(
            term in text_lower
            for term in ["market", "store", "revenue", "sales", "downtown", "westside", "lakefront"]
        ), f"Response should mention stores, got: {text[:200]}"


class TestAgentEngineBrandGuidelines:
    """Verify brand guidelines search works on the deployed agent."""

    def test_brand_colors(self, project_number, agent_engine_id, auth_headers):
        text = _stream_query(
            project_number, agent_engine_id, auth_headers,
            "What are the brand colors and typography guidelines?",
        )
        assert text, "Agent should return brand guideline information"
        text_lower = text.lower()
        assert any(
            term in text_lower
            for term in ["color", "brand", "green", "font", "typography", "palette", "guideline"]
        ), f"Response should mention brand elements, got: {text[:200]}"
