"""A2A server for the grocery retail agent.

Serves the ADK agent via the A2A protocol over HTTP, exposing:
- GET  /.well-known/agent.json  — AgentCard discovery
- POST /a2a                     — A2A task execution

Uses google-adk's built-in A2A support to wrap the agent for serving.

Usage:
    # Local
    python -m src.a2a_agent.server

    # Cloud Run (via Dockerfile)
    PORT=8080 python -m src.a2a_agent.server
"""

import os

import uvicorn


def create_app():
    """Create the ASGI application with A2A endpoints."""
    from google.adk.agents import LlmAgent
    from google.adk.a2a import to_a2a

    from .agent import create_agent, get_agent_card

    agent = create_agent()
    agent_card = get_agent_card()

    # Wrap the ADK agent with A2A protocol support
    # to_a2a() creates a Starlette/ASGI app with:
    #   - /.well-known/agent.json (AgentCard)
    #   - /a2a (task endpoint)
    app = to_a2a(
        agent=agent,
        agent_card=agent_card,
    )

    return app


def main():
    """Run the A2A server."""
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Starting A2A server on {host}:{port}")
    print(f"AgentCard: http://{host}:{port}/.well-known/agent.json")
    print(f"A2A endpoint: http://{host}:{port}/a2a")

    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
