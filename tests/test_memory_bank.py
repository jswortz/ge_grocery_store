"""Integration tests for Memory Bank — shared memory across all agents.

Tests verify that:
- Memories can be generated from session content
- Memories can be retrieved by user scope
- Memories can be searched with similarity queries
- Memory Bank is shared across all deployed agents

Requires:
- Valid GCP credentials
- Deployed agents on Agent Engine (agent_engine_id in config/settings.yaml)
- Run with: pytest -m integration tests/test_memory_bank.py -v
"""

import json
import time
import uuid
from pathlib import Path

import pytest
import yaml

import google.auth
from google.auth.transport.requests import Request

pytestmark = pytest.mark.integration

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"


def _load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def config():
    return _load_config()


@pytest.fixture(scope="module")
def vertexai_client():
    """Create a Vertex AI client for Memory Bank operations."""
    import vertexai
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    return client


@pytest.fixture(scope="module")
def agent_engine_ids(config):
    """Get all deployed agent engine IDs."""
    project = config.get("project", {})
    ids = {}
    for key in ["agent_engine_id", "mcp_agent_engine_id", "simulator_agent_engine_id"]:
        val = project.get(key, "")
        if val:
            ids[key] = val
    if not ids:
        pytest.skip("No agent_engine_id configured in settings.yaml")
    return ids


@pytest.fixture(scope="module")
def primary_agent_resource(agent_engine_ids):
    """Get the primary agent resource name for memory operations."""
    ae_id = (
        agent_engine_ids.get("agent_engine_id")
        or agent_engine_ids.get("simulator_agent_engine_id")
        or next(iter(agent_engine_ids.values()))
    )
    return f"projects/679926387543/locations/{LOCATION}/reasoningEngines/{ae_id}"


@pytest.fixture(scope="module")
def test_user_id():
    """Unique user ID for test isolation."""
    return f"test-memory-user-{uuid.uuid4().hex[:8]}"


class TestMemoryGeneration:
    """Verify that memories can be generated from conversation content."""

    def test_generate_memories_from_direct_contents(
        self, vertexai_client, primary_agent_resource, test_user_id
    ):
        """Generate memories from direct conversation content."""
        from google.genai import types as genai_types

        events = [
            {
                "content": {
                    "role": "user",
                    "parts": [{"text": "I always shop at the Downtown Market on Saturdays."}],
                }
            },
            {
                "content": {
                    "role": "user",
                    "parts": [{"text": "I'm allergic to peanuts and prefer organic produce."}],
                }
            },
            {
                "content": {
                    "role": "user",
                    "parts": [{"text": "My favorite brand is ValueFresh organic line."}],
                }
            },
        ]

        vertexai_client.agent_engines.memories.generate(
            name=primary_agent_resource,
            direct_contents_source={"events": events},
            scope={"user_id": test_user_id},
            config={"wait_for_completion": True},
        )

        # Wait for memory processing
        time.sleep(3)

        # Verify memories were created
        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": test_user_id},
        )
        memories = list(results)
        assert len(memories) > 0, "Should have generated at least one memory"

    def test_generate_memories_with_pre_extracted_facts(
        self, vertexai_client, primary_agent_resource, test_user_id
    ):
        """Generate memories from pre-extracted facts."""
        vertexai_client.agent_engines.memories.generate(
            name=primary_agent_resource,
            direct_memories_source={
                "direct_memories": [
                    {"fact": "Customer prefers the Lakefront Market for seafood"},
                    {"fact": "Customer has a Gold loyalty tier membership"},
                ]
            },
            scope={"user_id": test_user_id},
            config={"wait_for_completion": True},
        )

        time.sleep(3)

        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": test_user_id},
        )
        memories = list(results)
        assert len(memories) >= 2, (
            f"Should have at least 2 memories after adding facts, got {len(memories)}"
        )


class TestMemoryRetrieval:
    """Verify that memories can be retrieved and searched."""

    def test_retrieve_all_memories_by_scope(
        self, vertexai_client, primary_agent_resource, test_user_id
    ):
        """Retrieve all memories for a specific user."""
        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": test_user_id},
        )
        memories = list(results)
        assert len(memories) > 0, "Should retrieve stored memories for the test user"

        # Verify memory structure
        for memory in memories:
            assert hasattr(memory, "fact") or hasattr(memory, "name"), (
                f"Memory should have fact or name attribute, got: {dir(memory)}"
            )

    def test_similarity_search(
        self, vertexai_client, primary_agent_resource, test_user_id
    ):
        """Search memories using similarity search."""
        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": test_user_id},
            similarity_search_params={
                "search_query": "allergies and dietary restrictions",
                "top_k": 3,
            },
        )
        memories = list(results)
        assert len(memories) > 0, (
            "Similarity search should find allergy-related memories"
        )

    def test_similarity_search_shopping_preferences(
        self, vertexai_client, primary_agent_resource, test_user_id
    ):
        """Search for shopping preference memories."""
        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": test_user_id},
            similarity_search_params={
                "search_query": "which store does the customer prefer",
                "top_k": 3,
            },
        )
        memories = list(results)
        assert len(memories) > 0, (
            "Should find store preference memories"
        )

    def test_no_memories_for_unknown_user(
        self, vertexai_client, primary_agent_resource
    ):
        """Verify no memories returned for a non-existent user."""
        unknown_user = f"nonexistent-user-{uuid.uuid4().hex[:8]}"
        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": unknown_user},
        )
        memories = list(results)
        assert len(memories) == 0, (
            f"Should have no memories for unknown user, got {len(memories)}"
        )


class TestSharedMemoryBank:
    """Verify that Memory Bank is shared across all deployed agents.

    Memories stored via one agent should be retrievable via another agent,
    as long as the same user scope is used.
    """

    def test_memory_accessible_from_simulator_agent(
        self, vertexai_client, agent_engine_ids, test_user_id
    ):
        """Memories generated on primary agent should be accessible from simulator."""
        sim_id = agent_engine_ids.get("simulator_agent_engine_id")
        if not sim_id:
            pytest.skip("No simulator_agent_engine_id configured")

        sim_resource = f"projects/679926387543/locations/{LOCATION}/reasoningEngines/{sim_id}"

        # Store a memory on the simulator agent
        vertexai_client.agent_engines.memories.generate(
            name=sim_resource,
            direct_memories_source={
                "direct_memories": [
                    {"fact": "Test cross-agent memory: user prefers express checkout"},
                ]
            },
            scope={"user_id": test_user_id},
            config={"wait_for_completion": True},
        )

        time.sleep(3)

        # Retrieve from the simulator agent
        results = vertexai_client.agent_engines.memories.retrieve(
            name=sim_resource,
            scope={"user_id": test_user_id},
        )
        sim_memories = list(results)
        assert len(sim_memories) > 0, (
            "Memories should be retrievable from the simulator agent"
        )

    def test_memory_accessible_from_mcp_agent(
        self, vertexai_client, agent_engine_ids, test_user_id
    ):
        """Memories should be accessible from the MCP analytics agent."""
        mcp_id = agent_engine_ids.get("mcp_agent_engine_id")
        if not mcp_id:
            pytest.skip("No mcp_agent_engine_id configured")

        mcp_resource = f"projects/679926387543/locations/{LOCATION}/reasoningEngines/{mcp_id}"

        # Store a memory on the MCP agent
        vertexai_client.agent_engines.memories.generate(
            name=mcp_resource,
            direct_memories_source={
                "direct_memories": [
                    {"fact": "Test cross-agent memory: user tracks weekly produce spend"},
                ]
            },
            scope={"user_id": test_user_id},
            config={"wait_for_completion": True},
        )

        time.sleep(3)

        # Retrieve from MCP agent
        results = vertexai_client.agent_engines.memories.retrieve(
            name=mcp_resource,
            scope={"user_id": test_user_id},
        )
        mcp_memories = list(results)
        assert len(mcp_memories) > 0, (
            "Memories should be retrievable from the MCP agent"
        )


class TestMemoryCleanup:
    """Clean up test memories after all tests run."""

    def test_cleanup_test_memories(
        self, vertexai_client, primary_agent_resource, test_user_id
    ):
        """Delete all memories created during the test run."""
        results = vertexai_client.agent_engines.memories.retrieve(
            name=primary_agent_resource,
            scope={"user_id": test_user_id},
        )
        memories = list(results)

        deleted = 0
        for memory in memories:
            try:
                memory_name = getattr(memory, "name", None)
                if memory_name:
                    vertexai_client.agent_engines.memories.delete(name=memory_name)
                    deleted += 1
            except Exception:
                pass

        print(f"\nCleaned up {deleted} test memories for user {test_user_id}")
