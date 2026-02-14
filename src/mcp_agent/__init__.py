"""ADK agent package using MCP Toolbox for BigQuery.

This agent uses the MCP (Model Context Protocol) Toolbox for Databases
to interface with BigQuery, replacing manual SQL pattern matching with
the prebuilt BigQuery MCP server from googleapis/genai-toolbox.

Usage:
    # Local development (from project root)
    adk web src/mcp_agent

    # Programmatic
    from src.mcp_agent.agent import root_agent
"""

from . import agent
