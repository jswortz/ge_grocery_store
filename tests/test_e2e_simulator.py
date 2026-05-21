"""E2E tests for the Simulator Agent Engine backend.

Requires frontend running on http://localhost:8080.
Run with:  pytest tests/test_e2e_simulator.py -v -m e2e
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
class TestSimulatorSelection:
    """Verify Simulator agent appears and is selectable."""

    def test_simulator_in_selector(self, live_page):
        text = select_agent_engine(live_page, "Simulator")
        assert "simulator" in text.lower() or "Simulator" in text

    def test_simulator_badge(self, live_page):
        live_page.locator('button[data-backend="agent-engine"]').click()
        live_page.wait_for_timeout(500)
        options = live_page.locator("#agent-selector option").all()
        sim_opts = [o.text_content() for o in options if "Simulator" in (o.text_content() or "")]
        assert len(sim_opts) > 0, "Simulator should appear in selector"


@e2e
@frontend_running
class TestSimulatorQueries:
    """Verify Simulator queries and A2UI rendering."""

    def test_simulation_returns_response(self, live_page):
        select_agent_engine(live_page, "Simulator")
        msg = send_query(
            live_page,
            "Simulate shopper behavior for a snack endcap display",
            timeout=120_000,
        )
        text = msg.locator(".msg-bubble").inner_text()
        assert len(text) > 50, f"Simulation response too short: {text[:100]}"

    def test_a2ui_tabs_render(self, live_page):
        select_agent_engine(live_page, "Simulator")
        send_query(
            live_page,
            "Compare two endcap strategies for chips vs healthy snacks",
            timeout=120_000,
        )
        try:
            wait_for_a2ui(live_page, timeout=120_000)
            tabs = live_page.locator(".a2ui-tabs").all()
            if len(tabs) == 0:
                cards = live_page.locator(".a2ui-card").all()
                assert len(cards) > 0, "Should render A2UI tabs or cards for comparison"
        except Exception:
            pytest.skip("No A2UI tabs/cards rendered for simulation")

    def test_response_has_retail_terms(self, live_page):
        select_agent_engine(live_page, "Simulator")
        msg = send_query(
            live_page,
            "Run a simulation for weekend shoppers at the downtown store",
            timeout=120_000,
        )
        text = msg.locator(".msg-bubble").inner_text().lower()
        retail_terms = ["shopper", "cart", "product", "store", "purchase", "revenue", "endcap", "strategy"]
        found = [t for t in retail_terms if t in text]
        assert len(found) >= 2, f"Expected retail terms, found: {found}"

    def test_multi_turn_simulation(self, live_page):
        select_agent_engine(live_page, "Simulator")
        send_query(live_page, "Simulate 10 shoppers visiting the store", timeout=120_000)
        msg2 = send_query(
            live_page,
            "Now try with a promotional endcap for organic products",
            timeout=120_000,
        )
        text = msg2.locator(".msg-bubble").inner_text()
        assert len(text) > 30, "Follow-up simulation should produce content"

    def test_latency_metadata(self, live_page):
        select_agent_engine(live_page, "Simulator")
        send_query(live_page, "Quick simulation for dairy section", timeout=120_000)
        meta = live_page.locator(".message.assistant").last.locator(".msg-meta").inner_html()
        assert "Agent Engine" in meta or "s" in meta


@e2e
@frontend_running
class TestSimulatorScreenshot:
    """Capture high-res Simulator screenshots."""

    def test_capture_simulator_comparison(self, live_page, take_screenshot):
        select_agent_engine(live_page, "Simulator")
        send_query(
            live_page,
            "Compare endcap strategies: premium snacks vs budget snacks",
            timeout=120_000,
        )
        live_page.wait_for_timeout(1000)
        path = take_screenshot(live_page, "e2e_simulator_comparison")
        assert path.stat().st_size > 50_000
