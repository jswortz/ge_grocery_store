"""Deploy the A2A grocery agent to Vertex AI Agent Engine.

This deploys the agent to Agent Engine (like the main agent) while also
making it discoverable via A2A protocol for inter-agent communication.

Usage:
    cd src && python -m a2a_agent.deploy_to_agent_engine
"""

import os
import sys

import vertexai
from vertexai import agent_engines

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_agent.agent import create_agent

PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://wortz-project-352116-ge-workshop"


def find_agent_by_display_name(display_name: str) -> str:
    """Find reasoning engine by display name."""
    agent_filter_query = f'display_name="{display_name}"'
    agent_list = agent_engines.list(filter=agent_filter_query)
    for deployed_agent in agent_list:
        return deployed_agent.resource_name
    return ""


def deploy():
    """Deploy the A2A agent to Agent Engine."""
    print("=" * 80)
    print("DEPLOYING A2A GROCERY AGENT TO AGENT ENGINE")
    print("=" * 80)

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    agent = create_agent()
    display_name = "Grocery A2A Agent"

    app = agent_engines.AdkApp(
        agent=agent,
        app_name="grocery_a2a_agent_app",
        enable_tracing=True,
    )

    existing = find_agent_by_display_name(display_name)

    if existing:
        print(f"Found existing deployment: {existing}")
        print("Updating...")
        agent_engines.update(
            agent_engine=app,
            resource_name=existing,
            requirements=os.path.join(
                os.path.dirname(__file__), "requirements.txt"
            ),
            extra_packages=[
                os.path.dirname(__file__),
                os.path.join(os.path.dirname(__file__), "..", "agent"),
            ],
        )
        print(f"Updated: {existing}")
        return existing
    else:
        print("Creating new deployment...")
        remote_app = agent_engines.create(
            agent_engine=app,
            display_name=display_name,
            requirements=os.path.join(
                os.path.dirname(__file__), "requirements.txt"
            ),
            extra_packages=[
                os.path.dirname(__file__),
                os.path.join(os.path.dirname(__file__), "..", "agent"),
            ],
        )
        print(f"Deployed: {remote_app.resource_name}")
        return remote_app.resource_name


if __name__ == "__main__":
    resource_name = deploy()
    print(f"\nA2A Agent deployed: {resource_name}")
