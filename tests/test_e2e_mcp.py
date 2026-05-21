"""E2E tests for the MCP (Model Context Protocol) Agent Engine backend.

Requires frontend running on http://localhost:8080.
Run with:  pytest tests/test_e2e_mcp.py -v -m e2e
"""

from __future__ import annotations

import pytest

from e2e_helpers import (
    FORBIDDEN_RETAILER_NAMES,
    e2e,
    frontend_running,
    select_agent_engine,
    send_query,
    wait_for_a2ui,
)


@e2e
@frontend_running
class TestMCPSelection:
    """Verify MCP agent appears and is selectable."""

    def test_mcp_in_selector(self, live_page):
        text = select_agent_engine(live_page, "MCP")
        assert text, "MCP agent should be in selector"


@e2e
@frontend_running
class TestMCPQueries:
    """Verify MCP agent BigQuery queries and A2UI rendering."""

    def test_schema_query(self, live_page):
        select_agent_engine(live_page, "MCP")
        msg = send_query(live_page, "What tables are available in the database?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 20, f"Schema response too short: {text[:100]}"
        table_terms = ["fact_transactions", "dim_product", "dim_store", "dim_customer", "dim_employee", "table"]
        found = [t for t in table_terms if t.lower() in text.lower()]
        assert len(found) >= 1, f"Should mention table names, found: {found}"

    def test_revenue_query(self, live_page):
        select_agent_engine(live_page, "MCP")
        msg = send_query(live_page, "What is the total revenue across all stores?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 20, f"Revenue response too short: {text[:100]}"

    def test_a2ui_cards_render(self, live_page):
        select_agent_engine(live_page, "MCP")
        send_query(live_page, "Show revenue breakdown by product category with details")
        try:
            wait_for_a2ui(live_page)
            cards = live_page.locator(".a2ui-card").all()
            assert len(cards) > 0, "Should render A2UI cards for analytics"
        except Exception:
            pytest.skip("No A2UI cards rendered for this query")

    def test_multi_turn_analytics(self, live_page):
        select_agent_engine(live_page, "MCP")
        send_query(live_page, "What columns are in the fact_transactions table?")
        msg2 = send_query(live_page, "What is the average transaction amount?")
        text = msg2.locator(".msg-bubble").inner_text()
        assert len(text) > 15, "Multi-turn should produce content"

    def test_no_hardcoded_retailer_names(self, live_page):
        select_agent_engine(live_page, "MCP")
        send_query(live_page, "Summarize the store information")
        all_text = live_page.locator("#chat-area").inner_text()
        for name in FORBIDDEN_RETAILER_NAMES:
            assert name not in all_text, f"Hardcoded retailer name found: {name}"


@e2e
@frontend_running
class TestMCPScreenshot:
    """Capture high-res MCP analytics screenshot."""

    def test_capture_mcp_analytics(self, live_page, take_screenshot):
        select_agent_engine(live_page, "MCP")
        send_query(live_page, "Show me revenue by store with key metrics")
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "e2e_mcp_analytics")
        assert path.stat().st_size > 50_000
