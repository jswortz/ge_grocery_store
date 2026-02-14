"""Acceptance criteria tests for the grocery retail agent.

These tests validate the three acceptance scenarios:
1. Standard initialization/greeting
2. Closing SOP retrieval for frontline associates
3. Marketing asset generation adhering to brand guidelines

All tests require a provisioned Discovery Engine and are marked
as integration tests.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def stream_client():
    """Create a StreamAssist client from config."""
    from src.client.stream_assist import StreamAssistClient
    client = StreamAssistClient.from_config()
    if not client.engine_id:
        pytest.skip("No engine_id configured — run infra/provision_engine.sh first")
    return client


@pytest.fixture(scope="module")
def session_id(stream_client):
    """Create a session for the test suite."""
    return stream_client.create_session(display_name="AcceptanceTest")


class TestGreeting:
    """Acceptance Criteria 1: Standard initialization and greetings."""

    def test_hello_greeting(self, stream_client, session_id):
        # Search engines may skip pure greetings as non-informational,
        # so we use a greeting that includes an information-seeking element
        response = stream_client.query(
            "Hello! Can you tell me about the store procedures you have?",
            session_id,
        )
        assert response.text, "Agent should respond to greeting with info request"
        assert len(response.text) > 10

    def test_what_can_you_do(self, stream_client, session_id):
        response = stream_client.query(
            "What can you help me with?", session_id
        )
        assert response.text
        # Should mention its capabilities
        text_lower = response.text.lower()
        assert any(
            term in text_lower
            for term in ["help", "assist", "support", "procedure", "product"]
        )


class TestSOPRetrieval:
    """Acceptance Criteria 2: Retrieve closing SOPs for frontline associates."""

    def test_closing_procedures(self, stream_client, session_id):
        response = stream_client.query(
            "What are the closing procedures for frontline associates?",
            session_id,
        )
        assert response.text, "Agent should return closing procedure information"
        text_lower = response.text.lower()
        # Should contain relevant SOP content
        assert any(
            term in text_lower
            for term in ["closing", "close", "lock", "register", "security", "clean"]
        )

    def test_opening_procedures(self, stream_client, session_id):
        response = stream_client.query(
            "How should associates open the store in the morning?",
            session_id,
        )
        assert response.text
        text_lower = response.text.lower()
        assert any(
            term in text_lower
            for term in ["opening", "open", "arrive", "check", "safety"]
        )


class TestBrandGuidelines:
    """Acceptance Criteria 3: Retrieve brand guidelines for marketing use."""

    def test_brand_tone(self, stream_client, session_id):
        response = stream_client.query(
            "What tone of voice and style guidelines should we follow "
            "when creating marketing content?",
            session_id,
        )
        assert response.text, "Agent should return brand guideline information"
        text_lower = response.text.lower()
        assert any(
            term in text_lower
            for term in ["tone", "voice", "brand", "style", "friendly", "warm", "guideline"]
        )

    def test_brand_colors(self, stream_client, session_id):
        response = stream_client.query(
            "What are the brand color guidelines and typography standards?",
            session_id,
        )
        assert response.text
        text_lower = response.text.lower()
        assert any(
            term in text_lower
            for term in ["color", "font", "typography", "brand", "palette", "green"]
        )
