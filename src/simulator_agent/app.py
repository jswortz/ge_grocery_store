"""ADK Runner configuration for simulator agent with Vertex AI Memory Bank integration.

This module configures the ADK Runner for the shopper simulator with
a memory service. Memory persistence for the simulator enables tracking
shopper behavior patterns across multiple simulation runs.

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

        project_id = config["project"]["id"]
        location = config.get("memory", {}).get("location", "us-central1")

        # Use simulator agent's specific Agent Engine ID for memory scoping
        agent_engine_id = config["project"].get("simulator_agent_engine_id")

        logger.info(
            f"Creating VertexAiMemoryBankService for simulator: "
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
    logger.warning("Could not import root_agent from simulator_agent.agent")


# Create a configured Runner with memory service
def create_runner():
    """Create a Runner with memory service configured.

    Returns:
        Runner instance with the simulator orchestrator agent and memory service.
    """
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService

    from .agent import create_agent

    agent = create_agent()
    memory_service = _create_memory_service()
    session_service = InMemorySessionService()

    return Runner(
        agent=agent,
        app_name="simulator_orchestrator",
        session_service=session_service,
        memory_service=memory_service,
    )


try:
    runner = create_runner()
    logger.info("Simulator Runner created with memory service")
except Exception as e:
    runner = None
    logger.warning(f"Could not create simulator runner: {e}")
