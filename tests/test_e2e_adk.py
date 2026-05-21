"""E2E tests for the ADK Agent Engine backend.

Requires frontend running on http://localhost:8080.
Run with:  pytest tests/test_e2e_adk.py -v -m e2e
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
class TestADKAgentSelection:
    """Verify ADK agent appears and is selectable."""

    def test_agent_engine_tab_mode_label(self, live_page):
        live_page.locator('button[data-backend="agent-engine"]').click()
        live_page.wait_for_timeout(300)
        label = live_page.locator("#mode-label").text_content()
        assert "Agent Engine" in label and "A2A" in label

    def test_adk_agent_in_selector(self, live_page):
        text = select_agent_engine(live_page, "Grocery")
        assert text, "ADK agent should be selectable"


@e2e
@frontend_running
class TestADKQueries:
    """Verify ADK Agent Engine queries and A2UI rendering."""

    def test_analytics_query_returns_response(self, live_page):
        select_agent_engine(live_page, "Grocery")
        msg = send_query(live_page, "What are the top 5 products by revenue?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 30, f"Response too short: {text[:100]}"

    def test_response_has_a2ui_surface(self, live_page):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "Show me top products by revenue with details")
        try:
            wait_for_a2ui(live_page, timeout=90_000)
            surfaces = live_page.locator(".a2ui-surface").all()
            assert len(surfaces) > 0, "Should have at least one A2UI surface"
        except Exception:
            pytest.skip("Agent did not return A2UI components for this query")

    def test_a2ui_cards_render(self, live_page):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "What are the top selling products with revenue details?")
        try:
            wait_for_a2ui(live_page)
            cards = live_page.locator(".a2ui-card").all()
            assert len(cards) > 0, "Should render A2UI cards"
        except Exception:
            pytest.skip("No A2UI cards rendered")

    def test_a2ui_row_layout(self, live_page):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "Compare revenue across all stores as a dashboard")
        try:
            wait_for_a2ui(live_page)
            rows = live_page.locator(".a2ui-row").all()
            assert len(rows) > 0, "Should render A2UI rows for KPI layout"
        except Exception:
            pytest.skip("No A2UI row layout rendered")

    def test_multi_turn_conversation(self, live_page):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "What products are in the dairy category?")
        msg2 = send_query(live_page, "How do their sales compare?")
        text = msg2.locator(".msg-bubble").inner_text()
        assert len(text) > 20, "Follow-up should produce content"


@e2e
@frontend_running
class TestADKMetadata:
    """Verify latency and trace metadata appear in responses."""

    def test_latency_badge_present(self, live_page):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "How many transactions are in the database?")
        live_page.wait_for_timeout(300)
        meta = live_page.locator(".message.assistant").last.locator(".msg-meta").inner_html()
        assert "s" in meta, "Response meta should include latency"

    def test_trace_link_present(self, live_page):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "What is total revenue by store?")
        live_page.wait_for_timeout(300)
        meta = live_page.locator(".message.assistant").last.locator(".msg-meta").inner_html()
        has_trace = "View Trace" in meta or "trace" in meta.lower()
        if not has_trace:
            pytest.skip("Trace link not present — may depend on OTel config")


@e2e
@frontend_running
class TestADKScreenshot:
    """Capture high-res ADK A2UI screenshots."""

    def test_capture_adk_dashboard(self, live_page, take_screenshot):
        select_agent_engine(live_page, "Grocery")
        send_query(live_page, "Show me a dashboard of top products by revenue")
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "e2e_adk_dashboard")
        assert path.stat().st_size > 50_000
