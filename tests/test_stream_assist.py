"""Tests for the StreamAssist client.

Unit tests use mocked HTTP responses. Integration tests hit the live API
and are marked with @pytest.mark.integration.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.client.stream_assist import (
    AgentAuthorizationError,
    RetryableAPIError,
    StreamAssistClient,
    StreamAssistReply,
    StreamAssistResponse,
)


# --- Fixtures ---

@pytest.fixture
def client():
    """Create a StreamAssistClient with test config."""
    return StreamAssistClient(
        project_id="test-project",
        location="global",
        engine_id="test-engine-123",
        agent_id="test-agent-456",
    )


@pytest.fixture
def mock_credentials():
    """Mock google.auth.default to avoid real auth."""
    with patch("src.client.stream_assist.google.auth.default") as mock_auth:
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "test-token"
        mock_auth.return_value = (mock_creds, "test-project")
        yield mock_creds


# --- Unit Tests ---

class TestStreamAssistClient:

    def test_init_global_endpoint(self):
        client = StreamAssistClient(
            project_id="proj", location="global",
            engine_id="eng", agent_id="agt",
        )
        assert "discoveryengine.googleapis.com" in client.base_url
        assert "proj" in client.base_url
        assert "eng" in client.base_url

    def test_init_regional_endpoint(self):
        client = StreamAssistClient(
            project_id="proj", location="us-central1",
            engine_id="eng", agent_id="agt",
        )
        assert "us-central1-discoveryengine.googleapis.com" in client.base_url

    def test_parse_response_basic(self):
        raw = [
            {
                "answer": {
                    "state": "SUCCEEDED",
                    "replies": [
                        {
                            "groundedContent": {
                                "content": {
                                    "text": "Here are the closing procedures.",
                                    "role": "model",
                                    "thought": False,
                                }
                            }
                        }
                    ],
                }
            },
            {"sessionInfo": {"name": "projects/p/sessions/s123"}},
        ]
        result = StreamAssistClient._parse_response(raw)
        assert isinstance(result, StreamAssistResponse)
        assert len(result.replies) == 1
        assert result.text == "Here are the closing procedures."
        assert result.session_name == "projects/p/sessions/s123"
        assert result.state == "SUCCEEDED"

    def test_parse_response_with_thoughts(self):
        raw = [
            {
                "answer": {
                    "replies": [
                        {
                            "groundedContent": {
                                "content": {
                                    "text": "Let me search for that.",
                                    "role": "model",
                                    "thought": True,
                                }
                            }
                        },
                        {
                            "groundedContent": {
                                "content": {
                                    "text": "The closing SOP requires...",
                                    "role": "model",
                                    "thought": False,
                                }
                            }
                        },
                    ],
                }
            },
        ]
        result = StreamAssistClient._parse_response(raw)
        assert len(result.replies) == 2
        assert result.thoughts == "Let me search for that."
        assert result.text == "The closing SOP requires..."

    def test_parse_response_empty(self):
        result = StreamAssistClient._parse_response([{}])
        assert len(result.replies) == 0
        assert result.text == ""

    def test_parse_response_single_object(self):
        """Non-list response should be wrapped."""
        raw = {"answer": {"replies": []}}
        result = StreamAssistClient._parse_response(raw)
        assert isinstance(result, StreamAssistResponse)
        assert len(result.raw) == 1


class TestStreamAssistReply:

    def test_defaults(self):
        reply = StreamAssistReply()
        assert reply.text == ""
        assert reply.role == "model"
        assert reply.is_thought is False


class TestStreamAssistResponse:

    def test_text_excludes_thoughts(self):
        resp = StreamAssistResponse(
            replies=[
                StreamAssistReply(text="thought", is_thought=True),
                StreamAssistReply(text="answer", is_thought=False),
            ]
        )
        assert resp.text == "answer"
        assert resp.thoughts == "thought"


class TestErrorHandling:

    def test_403_raises_auth_error(self, client, mock_credentials):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with pytest.raises(AgentAuthorizationError) as exc_info:
            client._handle_error(mock_response)
        assert "test-agent-456" in str(exc_info.value)

    def test_429_raises_retryable(self, client, mock_credentials):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.text = "Rate limited"

        with pytest.raises(RetryableAPIError):
            client._handle_error(mock_response)

    def test_500_raises_retryable(self, client, mock_credentials):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        with pytest.raises(RetryableAPIError):
            client._handle_error(mock_response)

    def test_400_failed_precondition_not_retried(self, client, mock_credentials):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = "FAILED_PRECONDITION: agent error"
        mock_response.raise_for_status.side_effect = Exception("400 error")

        with pytest.raises(Exception, match="400 error"):
            client._handle_error(mock_response)

    def test_400_other_is_retryable(self, client, mock_credentials):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.text = "Some other 400 error"

        with pytest.raises(RetryableAPIError):
            client._handle_error(mock_response)


# --- Integration Tests ---

@pytest.mark.integration
class TestStreamAssistIntegration:
    """Integration tests requiring live Discovery Engine.

    These tests require:
    - Valid GCP credentials
    - A provisioned Discovery Engine with engine_id in config
    - Run with: pytest -m integration
    """

    def test_create_session_and_query(self):
        client = StreamAssistClient.from_config()
        if not client.engine_id:
            pytest.skip("No engine_id configured")

        session_id = client.create_session()
        assert session_id
        assert "sessions" in session_id

        response = client.query("Hello, what can you help me with?", session_id)
        assert isinstance(response, StreamAssistResponse)
        assert response.text  # Should have some response
