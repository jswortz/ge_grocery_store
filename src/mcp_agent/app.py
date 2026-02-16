"""ADK Runner configuration for MCP agent with Vertex AI Memory Bank integration.

This module configures the ADK Runner for the MCP grocery analyst with
a memory service, enabling user-scoped memory persistence across sessions.
This allows the analyst to remember user preferences, past queries, and
analytical context across conversations.

For ADK CLI usage, this module exposes:
- `root_agent`: The agent for `adk web` to use
- `runner`: A pre-configured Runner with memory service
"""

import logging
import os

from google.adk.memory import InMemoryMemoryService

logger = logging.getLogger(__name__)


def _create_memory_service():
    """Create and return the appropriate memory service based on config.

    Returns:
        VertexAiMemoryBankService if memory is enabled and in production,
        InMemoryMemoryService for local development or if memory is disabled.
    """
    from .agent import _load_config

    config = _load_config()
    memory_enabled = config.get("memory", {}).get("enabled", True)

    if not memory_enabled:
        logger.info("Memory disabled in config, using InMemoryMemoryService")
        return InMemoryMemoryService()

    # Try to create VertexAiMemoryBankService for production
    try:
        from google.adk.memory import VertexAiMemoryBankService

        project_id = config["bigquery"]["project"]  # MCP agent uses BQ project
        location = config.get("memory", {}).get("location", "us-central1")

        # Use MCP agent's specific Agent Engine ID for memory scoping
        agent_engine_id = config["project"].get("mcp_agent_engine_id")

        logger.info(
            f"Creating VertexAiMemoryBankService for MCP agent: "
            f"project={project_id}, location={location}, "
            f"agent_engine_id={agent_engine_id}"
        )

        return VertexAiMemoryBankService(
            project=project_id,
            location=location,
            agent_engine_id=agent_engine_id,
        )

    except Exception as e:
        logger.warning(
            f"Could not create VertexAiMemoryBankService: {e}. "
            f"Falling back to InMemoryMemoryService for local development."
        )
        return InMemoryMemoryService()


# Export the agent for ADK CLI compatibility
try:
    from .agent import root_agent
except ImportError:
    root_agent = None
    logger.warning("Could not import root_agent from mcp_agent.agent")


# Create session service
def _create_session_service():
    """Create the appropriate session service based on environment.

    Returns:
        VertexAiSessionService for production,
        InMemorySessionService for local development.
    """
    from .agent import _load_config

    config = _load_config()

    try:
        from google.adk.sessions import VertexAiSessionService

        project_id = config["bigquery"]["project"]
        location = config.get("memory", {}).get("location", "us-central1")

        logger.info(
            f"Creating VertexAiSessionService for MCP agent: "
            f"project={project_id}, location={location}"
        )
        return VertexAiSessionService(project=project_id, location=location)

    except Exception as e:
        from google.adk.sessions import InMemorySessionService

        logger.warning(
            f"Could not create VertexAiSessionService: {e}. "
            f"Falling back to InMemorySessionService for local development."
        )
        return InMemorySessionService()


# Create a configured Runner with memory and session services
def create_runner():
    """Create a Runner with memory and session services configured.

    Returns:
        Runner instance with the MCP grocery analyst agent, memory service,
        and VertexAI session service (or InMemory fallback).
    """
    from google.adk import Runner

    from .agent import create_agent

    agent = create_agent()
    memory_service = _create_memory_service()
    session_service = _create_session_service()

    return Runner(
        agent=agent,
        app_name="mcp_grocery_analyst",
        session_service=session_service,
        memory_service=memory_service,
    )


try:
    runner = create_runner()
    logger.info("MCP Runner created with memory service")
except Exception as e:
    runner = None
    logger.warning(f"Could not create MCP runner: {e}")
