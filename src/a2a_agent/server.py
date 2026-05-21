"""A2A server with A2UI support for the grocery retail agent.

Serves the ADK agent via the A2A protocol over HTTP with native A2UI
rendering support. When Discovery Engine (GE console) requests the A2UI
extension, the executor parses <a2ui-json> blocks from the LLM response
into A2A DataParts with mimeType=application/json+a2ui, which GE renders
as rich visual cards.

Endpoints:
- GET  /.well-known/agent.json  — AgentCard discovery (declares A2UI v0.8)
- POST /                        — A2A task execution

Usage:
    # Local
    python -m src.a2a_agent.server

    # Cloud Run (via Dockerfile)
    PORT=8080 python -m src.a2a_agent.server
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentExtension,
    AgentSkill,
    Artifact,
    DataPart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from a2ui.a2a.extension import (
    get_a2ui_agent_extension,
    try_activate_a2ui_extension,
)
from a2ui.a2a.parts import parse_response_to_parts
from google.adk.agents import LlmAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from starlette.applications import Starlette

logger = logging.getLogger(__name__)


class A2UIAgentExecutor(AgentExecutor):
    """Custom executor that runs the ADK agent and converts A2UI blocks to DataParts.

    When the A2UI extension is active (requested by GE console), this executor:
    1. Runs the ADK agent via Runner
    2. Collects the full text response
    3. Parses <a2ui-json> blocks into A2A DataParts
    4. Emits them as task artifacts so GE renders rich UI
    """

    def __init__(self, agent: LlmAgent, agent_card: AgentCard):
        super().__init__()
        self._agent = agent
        self._agent_card = agent_card
        self._runner = Runner(
            app_name=agent.name or "grocery_a2a",
            agent=agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if not context.message:
            raise ValueError("A2A request must have a message")

        a2ui_version = try_activate_a2ui_extension(context, self._agent_card)
        logger.info("A2UI extension: %s", a2ui_version or "not requested")

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                status=TaskStatus(state=TaskState.working),
                contextId=context.context_id,
                final=False,
            )
        )

        user_text = ""
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                user_text += part.root.text

        if not user_text:
            user_text = "Hello"

        try:
            user_id = "a2a_user"
            session = await self._runner.session_service.create_session(
                app_name=self._runner.app_name,
                user_id=user_id,
            )

            from google.genai.types import Content, Part as GenAIPart

            full_response = ""
            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=Content(
                    role="user",
                    parts=[GenAIPart(text=user_text)],
                ),
            ):
                if event.content and event.content.parts:
                    for p in event.content.parts:
                        if hasattr(p, "text") and p.text:
                            full_response += p.text

            logger.info("Agent response length: %d chars", len(full_response))

            if a2ui_version and "<a2ui-json>" in full_response:
                parts = parse_response_to_parts(
                    full_response,
                    fallback_text=full_response,
                )
                logger.info("Parsed %d A2UI parts", len(parts))
            else:
                parts = [Part(root=TextPart(text=full_response))]

            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    taskId=context.task_id,
                    contextId=context.context_id,
                    lastChunk=True,
                    artifact=Artifact(
                        artifactId="response",
                        parts=parts,
                    ),
                )
            )

            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    taskId=context.task_id,
                    status=TaskStatus(state=TaskState.completed),
                    contextId=context.context_id,
                    final=True,
                )
            )

        except Exception as e:
            logger.error("Agent execution failed: %s", e, exc_info=True)
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    taskId=context.task_id,
                    status=TaskStatus(
                        state=TaskState.failed,
                        message=Message(
                            role=Role.agent,
                            messageId=str(uuid.uuid4()),
                            parts=[Part(root=TextPart(text=str(e)))],
                        ),
                    ),
                    contextId=context.context_id,
                    final=True,
                )
            )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                status=TaskStatus(state=TaskState.canceled),
                contextId=context.context_id,
                final=True,
            )
        )


def _get_agent_url() -> str:
    """Resolve the agent's public URL.

    Priority: A2A_AGENT_URL env var > Cloud Run auto-detect (K_SERVICE) > localhost.
    """
    if os.environ.get("A2A_AGENT_URL"):
        return os.environ["A2A_AGENT_URL"]
    k_service = os.environ.get("K_SERVICE")
    project_number = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "")
    region = os.environ.get("CLOUD_RUN_REGION", "us-central1")
    if k_service and project_number:
        return f"https://{k_service}-{project_number}.{region}.run.app/"
    if k_service:
        return f"https://{k_service}.run.app/"
    return "http://localhost:8080/"


def _build_agent_card() -> AgentCard:
    """Build an AgentCard declaring A2UI v0.8 extension support."""
    from .agent import _load_config

    config = _load_config()
    retailer = config["retailer"]["name"]

    a2ui_ext = get_a2ui_agent_extension("0.8")

    return AgentCard(
        name="grocery-retail-assistant",
        description=(
            f"AI assistant for {retailer} grocery retail operations. "
            "Handles SOP lookup, brand guidelines, sales analytics, "
            "and product image generation with rich visual A2UI output."
        ),
        url=_get_agent_url(),
        version="1.0.0",
        capabilities=AgentCapabilities(
            streaming=True,
            extensions=[a2ui_ext],
        ),
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[
            AgentSkill(
                id="sop-lookup",
                name="SOP Lookup",
                description="Search and retrieve Standard Operating Procedures",
                tags=["sop", "procedures", "operations"],
            ),
            AgentSkill(
                id="brand-guidelines",
                name="Brand Guidelines",
                description="Search brand guidelines for marketing compliance",
                tags=["brand", "marketing", "guidelines"],
            ),
            AgentSkill(
                id="sales-analytics",
                name="Sales Analytics",
                description="Query BigQuery for sales and customer analytics",
                tags=["analytics", "sales", "bigquery"],
            ),
            AgentSkill(
                id="image-generation",
                name="Product Image Generation",
                description="Generate brand-compliant product imagery",
                tags=["image", "product", "generation"],
            ),
        ],
    )


def create_app() -> Starlette:
    """Create the ASGI application with A2A + A2UI endpoints."""
    from .agent import create_agent

    agent = create_agent()
    agent_card = _build_agent_card()

    executor = A2UIAgentExecutor(agent=agent, agent_card=agent_card)

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    a2a_server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    app = a2a_server.build()
    return app


def main():
    """Run the A2A server."""
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")

    logging.basicConfig(level=logging.INFO)

    print(f"Starting A2A+A2UI server on {host}:{port}")
    print(f"AgentCard: http://{host}:{port}/.well-known/agent.json")

    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
