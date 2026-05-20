"""E2E tests for the StreamAssist (Discovery Engine) agent backend.

Requires frontend running on http://localhost:8080.
Run with:  pytest tests/test_e2e_streamassist.py -v -m e2e
"""

from __future__ import annotations

import json

import pytest

from e2e_helpers import e2e, frontend_running, send_query


@e2e
@frontend_running
class TestStreamAssistPageLoad:
    """Verify the StreamAssist tab loads correctly."""

    def test_brand_name_from_config(self, live_page, config):
        brand = live_page.locator("#brand-name").text_content()
        assert brand == config["retailer"]["name"], (
            f"Brand name should come from config, got '{brand}'"
        )

    def test_default_assistant_in_selector(self, live_page):
        selector = live_page.locator("#agent-selector")
        first_opt = selector.locator("option").first.text_content()
        assert "Default" in first_opt


@e2e
@frontend_running
class TestStreamAssistDataStores:
    """Verify data store pills load and can be toggled."""

    def test_data_store_pills_load(self, live_page):
        pills = live_page.locator("#data-sources-list span").all()
        assert len(pills) >= 2, "Should have at least SOPs and Brand Guidelines"

    def test_data_store_pill_toggle(self, live_page):
        live_page.evaluate("""
            const panel = document.getElementById('data-sources-panel');
            if (panel) panel.style.display = 'block';
        """)
        live_page.wait_for_timeout(200)
        pills = live_page.locator("#data-sources-list span[title]").all()
        if len(pills) == 0:
            pytest.skip("No data store pills rendered")
        first = pills[0]
        before = first.get_attribute("title") or ""
        first.click(force=True)
        live_page.wait_for_timeout(300)
        after = live_page.locator("#data-sources-list span[title]").first.get_attribute("title") or ""
        assert before != after, "Pill title should toggle on click"


@e2e
@frontend_running
class TestStreamAssistQueries:
    """Verify StreamAssist queries return content."""

    def test_sop_query_returns_content(self, live_page):
        msg = send_query(live_page, "What are the store closing procedures?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 50, f"SOP response too short: {text[:100]}"

    def test_brand_guidelines_query(self, live_page):
        msg = send_query(live_page, "What are the brand color guidelines?")
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 30, f"Brand response too short: {text[:100]}"

    def test_multi_turn_preserves_session(self, live_page):
        send_query(live_page, "What departments does the store have?")
        msg2 = send_query(live_page, "Tell me more about the first one")
        text = msg2.locator(".msg-bubble").inner_text()
        assert len(text) > 20, "Multi-turn should produce a substantive response"

    def test_agent_switch_clears_session(self, live_page):
        send_query(live_page, "Hello")
        opts = live_page.locator("#agent-selector option").all()
        if len(opts) < 2:
            pytest.skip("Only one agent available")
        live_page.locator("#agent-selector").select_option(index=1)
        live_page.wait_for_timeout(500)
        session_null = live_page.evaluate("State.sessionName === null")
        assert session_null, "Session should reset on agent switch"


@e2e
@frontend_running
class TestStreamAssistScreenshot:
    """Capture a high-res screenshot of StreamAssist output."""

    def test_capture_sop_response(self, live_page, take_screenshot):
        send_query(live_page, "What are the closing procedures for the store?")
        live_page.wait_for_timeout(500)
        path = take_screenshot(live_page, "e2e_streamassist_sop")
        assert path.stat().st_size > 50_000, "Screenshot should be substantial"
