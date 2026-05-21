"""Curated screenshot capture suite for README and VP demos.

Each test sends a carefully chosen query to produce rich A2UI output,
then captures a high-res screenshot suitable for documentation.

Requires frontend running on http://localhost:8080.
Run with:  pytest tests/test_e2e_screenshots.py -v -m e2e
"""

from __future__ import annotations

import pytest

from e2e_helpers import (
    e2e,
    frontend_running,
    select_agent_engine,
    send_query,
    wait_for_a2ui,
)


@e2e
@frontend_running
class TestReadmeScreenshots:
    """Capture README-quality screenshots of A2UI across all agents."""

    def test_readme_adk_kpi_dashboard(self, live_page, take_screenshot):
        select_agent_engine(live_page, "Grocery")
        send_query(
            live_page,
            "What are the top 5 products by revenue this quarter? Show as a dashboard.",
        )
        try:
            wait_for_a2ui(live_page)
        except Exception:
            pass
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_adk_kpi_dashboard")
        assert path.stat().st_size > 50_000

    def test_readme_adk_sop_checklist(self, live_page, take_screenshot):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "What are the closing procedures for the store?")
        try:
            wait_for_a2ui(live_page)
        except Exception:
            pass
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_adk_sop_checklist")
        assert path.stat().st_size > 50_000

    def test_readme_simulator_ab_comparison(self, live_page, take_screenshot):
        select_agent_engine(live_page, "Simulator")
        send_query(
            live_page,
            "Compare endcap strategies: premium snacks vs budget-friendly options for weekend shoppers",
            timeout=120_000,
        )
        try:
            wait_for_a2ui(live_page, timeout=120_000)
        except Exception:
            pass
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_simulator_ab")
        assert path.stat().st_size > 50_000

    def test_readme_simulator_personas(self, live_page, take_screenshot):
        select_agent_engine(live_page, "Simulator")
        send_query(
            live_page,
            "Simulate 5 different shopper personas visiting the dairy section",
            timeout=120_000,
        )
        try:
            wait_for_a2ui(live_page, timeout=120_000)
        except Exception:
            pass
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_simulator_personas")
        assert path.stat().st_size > 50_000

    def test_readme_mcp_analytics(self, live_page, take_screenshot):
        select_agent_engine(live_page, "MCP")
        send_query(
            live_page,
            "Show revenue by store for the last 6 months with key metrics",
        )
        try:
            wait_for_a2ui(live_page)
        except Exception:
            pass
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_mcp_analytics")
        assert path.stat().st_size > 50_000

    def test_readme_a2a_response(self, live_page, take_screenshot):
        select_agent_engine(live_page, "A2A")
        send_query(
            live_page,
            "What are the top products and how do stores compare on revenue?",
        )
        try:
            wait_for_a2ui(live_page)
        except Exception:
            pass
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_a2a_response")
        assert path.stat().st_size > 50_000

    def test_readme_streamassist_sop(self, live_page, take_screenshot):
        send_query(live_page, "What are the store closing procedures?")
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "readme_streamassist_sop")
        assert path.stat().st_size > 50_000

    def test_readme_full_ui_overview(self, live_page, take_screenshot):
        """Capture the full UI with welcome screen visible."""
        path = take_screenshot(live_page, "readme_ui_overview", full_page=True)
        assert path.stat().st_size > 50_000
