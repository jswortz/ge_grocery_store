"""ADK Runner configuration with Vertex AI Memory Bank integration.

This module configures the ADK Runner with a memory service,
enabling user-scoped memory persistence across sessions.

The memory service uses Vertex AI Memory Bank when:
- config["memory"]["enabled"] is True
- Running in production (Agent Engine deployment)

Falls back to InMemoryMemoryService for local development.

For ADK CLI usage, this module exposes:
- `root_agent`: The agent for `adk web` to use
- `runner`: A pre-configured Runner with memory service

Note: ADK CLI (`adk web`, `adk deploy`) will automatically create a Runner
if only `root_agent` is provided. This module provides both for flexibility.
"""

import logging

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

        project_id = config["project"]["id"]
        location = config.get("memory", {}).get("location", "us-central1")

        # Agent Engine ID is optional for Memory Bank
        # If provided, memories can be scoped to specific agent deployments
        agent_engine_id = config["project"].get("agent_engine_id")

        logger.info(
            f"Creating VertexAiMemoryBankService: "
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
    logger.warning("Could not import root_agent from agent.py")


# Create a configured Runner with memory service
# Note: ADK CLI will use root_agent and create its own Runner,
# but this is available for programmatic use
def _create_session_service():
    """Create the appropriate session service based on environment.

    Returns:
        VertexAiSessionService for production (when Agent Engine ID is configured),
        InMemorySessionService for local development.
    """
    from .agent import _load_config

    config = _load_config()

    try:
        from google.adk.sessions import VertexAiSessionService

        project_id = config["project"]["id"]
        location = config.get("memory", {}).get("location", "us-central1")

        logger.info(
            f"Creating VertexAiSessionService: "
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


def create_runner():
    """Create a Runner with memory and session services configured.

    Returns:
        Runner instance with the code execution analytics agent, memory service,
        and VertexAI session service (or InMemory fallback).
    """
    from google.adk import Runner

    from .agent import create_agent

    agent = create_agent()
    memory_service = _create_memory_service()
    session_service = _create_session_service()

    return Runner(
        agent=agent,
        app_name="code_exec_analyst",
        session_service=session_service,
        memory_service=memory_service,
    )


try:
    runner = create_runner()
    logger.info("Runner created with memory service")
except Exception as e:
    runner = None
    logger.warning(f"Could not create runner: {e}")
