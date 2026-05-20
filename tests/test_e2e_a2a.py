"""E2E tests for the A2A (Agent-to-Agent) backend on Cloud Run.

Requires frontend running on http://localhost:8080.
Run with:  pytest tests/test_e2e_a2a.py -v -m e2e
"""

from __future__ import annotations

import pytest

from e2e_helpers import (
    e2e,
    frontend_running,
    select_agent_engine,
    send_query,
)


@e2e
@frontend_running
class TestA2ASelection:
    """Verify A2A agent appears and is selectable."""

    def test_a2a_in_selector(self, live_page):
        text = select_agent_engine(live_page, "A2A")
        assert text, "A2A agent should be in selector"

    def test_a2a_badge(self, live_page):
        live_page.locator('button[data-backend="agent-engine"]').click()
        live_page.wait_for_timeout(500)
        options = live_page.locator("#agent-selector option").all()
        a2a_opts = [o.text_content() for o in options if "A2A" in (o.text_content() or "")]
        assert len(a2a_opts) > 0, "A2A agent should have [A2A] badge"


@e2e
@frontend_running
class TestA2AQueries:
    """Verify A2A queries route correctly and return content."""

    def test_sop_query(self, live_page):
        select_agent_engine(live_page, "A2A")
        msg = send_query(live_page, "What are the store opening procedures?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 30, f"A2A SOP response too short: {text[:100]}"

    def test_analytics_query(self, live_page):
        select_agent_engine(live_page, "A2A")
        msg = send_query(live_page, "What are the top products by revenue?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 30, f"A2A analytics response too short: {text[:100]}"

    def test_multi_turn(self, live_page):
        select_agent_engine(live_page, "A2A")
        send_query(live_page, "What product categories do we carry?")
        msg2 = send_query(live_page, "Which category has the highest revenue?")
        text = msg2.locator(".msg-bubble").inner_text()
        assert len(text) > 20, "A2A multi-turn should produce content"

    def test_latency_metadata(self, live_page):
        select_agent_engine(live_page, "A2A")
        send_query(live_page, "How many stores do we have?")
        meta = live_page.locator(".message.assistant").last.locator(".msg-meta").inner_html()
        assert len(meta) > 5, "Response should have metadata"


@e2e
@frontend_running
class TestA2AScreenshot:
    """Capture high-res A2A response screenshot."""

    def test_capture_a2a_response(self, live_page, take_screenshot):
        select_agent_engine(live_page, "A2A")
        send_query(live_page, "Show me a summary of top products and store performance")
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "e2e_a2a_response")
        assert path.stat().st_size > 50_000
