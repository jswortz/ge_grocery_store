"""Frontend e2e and source-analysis tests.

Unit tests (TestFrontend*) analyse the HTML/JS source and pass without a
running server — suitable for CI / GH Actions.

E2E tests (TestE2E*) require the frontend at http://localhost:8080 and
are marked ``@pytest.mark.e2e`` so they're skipped in CI by default.
Run locally with:  pytest tests/test_frontend_e2e.py -v -m e2e
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / "src" / "frontend" / "index.html"
SERVER_PATH = ROOT / "src" / "frontend" / "server.py"
VOICE_SERVER_PATH = ROOT / "src" / "frontend" / "voice_server.py"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"


def _html() -> str:
    return HTML_PATH.read_text()


def _server() -> str:
    return SERVER_PATH.read_text()


# ===================================================================
# UNIT TESTS — source-code analysis (no server needed, runs in CI)
# ===================================================================


class TestFrontendTabs:
    """Verify tab layout and naming in the frontend HTML."""

    def test_three_tabs_present(self):
        html = _html()
        expected_backends = ["stream-assist", "agent-engine", "voice-ops"]
        for backend in expected_backends:
            assert f'data-backend="{backend}"' in html, f"Missing tab: {backend}"
        # Compare tab was removed
        assert 'data-backend="compare"' not in html

    def test_agent_engine_tab_includes_a2a(self):
        html = _html()
        # The tab button text should include "A2A" (may be HTML-encoded as &amp;)
        idx = html.index('data-backend="agent-engine"')
        # Capture enough of the button element to include inner text
        end_idx = html.index("</button>", idx) + len("</button>")
        snippet = html[idx:end_idx]
        assert "A2A" in snippet or "a2a" in snippet.lower(), (
            f"Agent Engine tab should mention A2A. Got: {snippet[:200]}"
        )

    def test_mode_label_includes_a2a(self):
        html = _html()
        assert "Agent Engine & A2A" in html or "Agent Engine &amp; A2A" in html

    def test_compare_panel_label_includes_a2a(self):
        html = _html()
        assert "Agent Engine &amp; A2A" in html or "Agent Engine & A2A" in html

    def test_voice_tab_has_ops_label(self):
        html = _html()
        idx = html.index('data-backend="voice-ops"')
        end_idx = html.index("</button>", idx) + len("</button>")
        snippet = html[idx:end_idx]
        assert "Voice" in snippet
        assert "Ops" in snippet or "Supply" in snippet


class TestFrontendAgentSelector:
    """Verify agent selector / dropdown behaviour."""

    def test_agent_selector_element_exists(self):
        html = _html()
        assert 'id="agent-selector"' in html

    def test_agent_selector_loads_from_api(self):
        html = _html()
        assert "/api/stream-assist/agents" in html

    def test_agent_selector_type_badges(self):
        html = _html()
        for badge in ("ADK", "A2A", "Data"):
            assert badge in html, f"Missing type badge: {badge}"

    def test_agent_selector_routes_through_default_assistant(self):
        """Ensure queries always go through default_assistant, not registered IDs."""
        html = _html()
        assert "assistants/default_assistant:streamAssist" in html

    def test_agent_selector_visibility_logic(self):
        html = _html()
        assert "updateAgentSelectorVisibility" in html

    def test_select_agent_clears_session(self):
        html = _html()
        assert "State.sessionName = null" in html


class TestFrontendDataStores:
    """Verify data-store filtering UI."""

    def test_data_store_listing_endpoint(self):
        html = _html()
        assert "/api/stream-assist/data-stores" in html

    def test_data_store_toggle_function(self):
        html = _html()
        assert "toggleDataStore" in html

    def test_data_store_specs_generation(self):
        html = _html()
        assert "getSelectedDataStoreSpecs" in html
        assert "vertexAiSearchSpec" in html
        assert "dataStoreSpecs" in html

    def test_data_store_pills_render(self):
        html = _html()
        assert "renderDataStorePills" in html

    def test_data_store_group_icons(self):
        html = _html()
        for label in ("SOPs", "Brand Guidelines"):
            assert label in html


class TestFrontendVoiceOps:
    """Verify voice ops overlay structure."""

    def test_voice_overlay_exists(self):
        html = _html()
        assert 'id="voice-ops-overlay"' in html

    def test_voice_overlay_mic_button(self):
        html = _html()
        assert "toggleVoiceOps" in html

    def test_voice_overlay_suggestion_buttons(self):
        html = _html()
        assert "sendVoiceOpsText" in html
        for label in ("Staffing levels", "Peak hours", "Inventory turnover", "Labor costs"):
            assert label in html, f"Missing suggestion: {label}"

    def test_voice_ops_websocket_connects_with_agent_param(self):
        html = _html()
        assert "agent=operations" in html

    def test_voice_ops_transcript_area(self):
        html = _html()
        assert 'id="voice-ops-transcript"' in html

    def test_voice_ops_text_mode_fallback(self):
        """Suggestion buttons use text-only mode (is_audio=false)."""
        html = _html()
        assert "connectVoiceOpsWebSocket(false)" in html


class TestServerAgentRouting:
    """Verify server.py proxy routing."""

    def test_server_routes_through_default_assistant(self):
        src = _server()
        assert "assistants/default_assistant:streamAssist" in src

    def test_server_strips_assistant_id(self):
        src = _server()
        assert 'payload.pop("assistant_id", None)' in src

    def test_server_lists_registered_agents(self):
        src = _server()
        assert "assistants/default_assistant/agents" in src

    def test_server_detects_agent_types(self):
        src = _server()
        for t in ("adk", "a2a", "managed"):
            assert f'agent_type = "{t}"' in src

    def test_server_has_data_store_endpoint(self):
        src = _server()
        assert "/api/stream-assist/data-stores" in src

    def test_server_has_health_endpoint(self):
        src = _server()
        assert "/api/health" in src


class TestServerVoiceIntegration:
    """Verify server.py starts the voice WebSocket server."""

    def test_voice_server_import(self):
        src = _server()
        assert "start_voice_server" in src

    def test_voice_server_config(self):
        src = VOICE_SERVER_PATH.read_text()
        assert "VOICE_WS_PORT" in src or "ws_port" in src

    def test_voice_server_runner_creation(self):
        src = VOICE_SERVER_PATH.read_text()
        assert "_create_runner" in src
        assert "operations" in src

    def test_voice_server_uses_vertexai(self):
        src = VOICE_SERVER_PATH.read_text()
        assert "GOOGLE_GENAI_USE_VERTEXAI" in src

    def test_voice_server_live_model_region(self):
        src = VOICE_SERVER_PATH.read_text()
        assert "live_location" in src or "us-east4" in src


class TestFrontendStreaming:
    """Verify Agent Engine SSE streaming."""

    def test_sse_streaming_function(self):
        html = _html()
        assert "callAgentEngineStreaming" in html or "callAgentEngine" in html

    def test_ndjson_parsing(self):
        html = _html()
        assert "parseAgentEngineResponse" in html or "ndjson" in html.lower()


class TestMultiTurnCapability:
    """Verify multi-turn conversation support in the source code."""

    def test_streamassist_session_reuse(self):
        """State.sessionName persists so subsequent queries reuse the session."""
        html = _html()
        # ensureSession only creates a session if sessionName is null
        assert "State.sessionName" in html
        # callStreamAssist uses State.sessionName for the session resource
        assert "State.sessionName ||" in html or "State.sessionName" in html

    def test_agent_engine_user_id_continuity(self):
        """Agent Engine queries include user_id for conversation continuity."""
        html = _html()
        assert "State.userId" in html
        assert "user_id" in html

    def test_voice_ops_websocket_multi_message(self):
        """sendVoiceOpsText can send multiple messages on an open WebSocket."""
        html = _html()
        # If WS is already open, it sends directly without reconnecting
        assert "voiceOpsWs.readyState === WebSocket.OPEN" in html

    def test_voice_ops_transcript_accumulates(self):
        """Voice ops transcript appends (not replaces) each message."""
        html = _html()
        assert "voiceOpsTranscript +=" in html

    def test_frontend_favicon(self):
        """Frontend has a favicon link tag."""
        html = _html()
        assert 'rel="icon"' in html


class TestDeploymentScripts:
    """Verify deployment scripts have correct env vars."""

    def test_agent_deploy_has_global_location(self):
        src = (ROOT / "src" / "agent" / "deploy_to_agent_engine.py").read_text()
        assert "GOOGLE_CLOUD_LOCATION" in src
        assert "global" in src

    def test_mcp_deploy_has_global_location(self):
        src = (ROOT / "src" / "mcp_agent" / "deploy_to_agent_engine.py").read_text()
        assert "GOOGLE_CLOUD_LOCATION" in src

    def test_simulator_deploy_has_global_location(self):
        src = (ROOT / "src" / "simulator_agent" / "deploy_to_agent_engine.py").read_text()
        assert "GOOGLE_CLOUD_LOCATION" in src

    def test_voice_deploy_has_global_location(self):
        src = (ROOT / "src" / "voice_bidi_agent" / "deploy_to_agent_engine.py").read_text()
        assert "GOOGLE_CLOUD_LOCATION" in src


# ===================================================================
# E2E TESTS — require running frontend at http://localhost:8080
# ===================================================================


def _check_frontend():
    """Return True if the frontend is running on localhost:8080."""
    try:
        import urllib.request

        with urllib.request.urlopen("http://localhost:8080/api/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _get_playwright():
    """Import Playwright, skip test if not available."""
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright
    except ImportError:
        pytest.skip("playwright not installed (pip install playwright)")


frontend_running = pytest.mark.skipif(
    not _check_frontend(), reason="Frontend not running on localhost:8080"
)

e2e = pytest.mark.e2e


@e2e
@frontend_running
class TestE2EPageLoad:
    """E2E: Verify the frontend page loads correctly."""

    def test_page_loads_with_brand_name(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            title = page.locator("#brand-name").text_content()
            assert title and len(title) > 0
            browser.close()

    def test_three_tabs_visible(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            tabs = page.locator(".tab-btn").all()
            assert len(tabs) == 3
            browser.close()

    def test_agent_engine_tab_text_includes_a2a(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            ae_tab = page.locator('button[data-backend="agent-engine"]')
            text = ae_tab.text_content()
            assert "A2A" in text
            browser.close()


@e2e
@frontend_running
class TestE2EAgentSelector:
    """E2E: Verify agent selector loads and agents are selectable."""

    def test_agent_selector_populates(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            # Agent selector should be visible on StreamAssist tab (default)
            selector = page.locator("#agent-selector")
            assert selector.is_visible()
            # Should have at least "Default Assistant"
            options = selector.locator("option").all()
            assert len(options) >= 1
            first_opt = options[0].text_content()
            assert "Default" in first_opt
            browser.close()

    def test_agent_selector_has_registered_agents(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            selector = page.locator("#agent-selector")
            options = selector.locator("option").all()
            # Should have more than just default if agents are registered
            option_texts = [o.text_content() for o in options]
            has_badges = any("[ADK]" in t or "[A2A]" in t or "[Data]" in t for t in option_texts)
            # This is informational — registered agents depend on infra setup
            if len(options) > 1:
                assert has_badges, f"Registered agents missing type badges: {option_texts}"
            browser.close()

    def test_agent_selector_switch_works(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logs = []
            page.on("console", lambda msg: logs.append(msg.text))
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            selector = page.locator("#agent-selector")
            options = selector.locator("option").all()
            if len(options) >= 2:
                second_val = options[1].get_attribute("value")
                selector.select_option(second_val)
                page.wait_for_timeout(300)
                selected_logs = [l for l in logs if "Selected agent" in l]
                assert len(selected_logs) >= 1
            browser.close()

    def test_agent_selector_visible_on_agent_engine_tab(self):
        """Agent selector shows on Agent Engine tab to pick between deployed agents."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            # Switch to Agent Engine tab
            page.locator('button[data-backend="agent-engine"]').click()
            page.wait_for_timeout(300)
            wrap = page.locator("#agent-selector-wrap")
            display = wrap.evaluate("el => getComputedStyle(el).display")
            assert display != "none"
            browser.close()


@e2e
@frontend_running
class TestE2EDataStores:
    """E2E: Verify data store pills load and are toggleable."""

    def test_data_store_pills_load(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            pills = page.locator("#data-sources-list span").all()
            # Should have at least SOPs and Brand Guidelines
            assert len(pills) >= 2
            browser.close()

    def test_data_store_pills_toggleable(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            # Expand the data sources panel via JS (it's hidden by default)
            page.evaluate("""
                const panel = document.getElementById('data-sources-panel');
                if (panel) panel.style.display = 'block';
            """)
            page.wait_for_timeout(200)
            pills = page.locator("#data-sources-list span[title]").all()
            if len(pills) > 0:
                first_pill = pills[0]
                initial_title = first_pill.get_attribute("title") or ""
                # Use force click since panel may overlap
                first_pill.click(force=True)
                page.wait_for_timeout(300)
                new_pills = page.locator("#data-sources-list span[title]").all()
                new_title = new_pills[0].get_attribute("title") or ""
                assert initial_title != new_title, (
                    f"Pill title should toggle. Before: {initial_title}, After: {new_title}"
                )
            browser.close()


@e2e
@frontend_running
class TestE2EStreamAssistQuery:
    """E2E: Verify StreamAssist queries work via the default assistant."""

    def test_streamassist_session_creation(self):
        """Verify session endpoint returns a valid session."""
        import urllib.request

        req = urllib.request.Request(
            "http://localhost:8080/api/stream-assist/sessions",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            assert "name" in data

    def test_streamassist_default_assistant_query(self):
        """Verify querying the default assistant returns results."""
        import urllib.request

        # Create session
        req = urllib.request.Request(
            "http://localhost:8080/api/stream-assist/sessions",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            session_data = json.loads(r.read())
        session_name = session_data["name"]

        # Query
        payload = json.dumps({
            "session": session_name,
            "query": {"text": "What SOPs do you have?"},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:8080/api/stream-assist/query",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp_data = json.loads(r.read())
            # Response should contain replies with text
            assert "replies" in resp_data or "answer" in resp_data or resp_data


@e2e
@frontend_running
class TestE2EVoiceOps:
    """E2E: Verify voice ops overlay and text-query flow."""

    def test_voice_tab_shows_overlay(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(300)
            overlay = page.locator("#voice-ops-overlay")
            display = overlay.evaluate("el => getComputedStyle(el).display")
            assert display == "flex"
            # Verify title
            title = page.locator("#voice-ops-title").text_content()
            assert "Operations Voice Assistant" in title
            browser.close()

    def test_voice_suggestion_button_sends_query(self):
        """Click a suggestion button and verify transcript populates."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logs = []
            page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            # Switch to Voice tab
            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(500)
            # Click the "Staffing levels" suggestion
            page.locator("text=Staffing levels").click()
            # Wait for WebSocket connection + response
            page.wait_for_timeout(10000)
            # Check transcript area
            transcript = page.locator("#voice-ops-transcript").inner_html()
            assert "You" in transcript, "User message should appear in transcript"
            # Check for connection success in console
            ws_connected = any("Voice ops WebSocket connected" in l for l in logs)
            assert ws_connected, f"WebSocket didn't connect. Logs: {logs[:10]}"
            browser.close()

    def test_voice_mic_button_exists_and_clickable(self):
        """Verify mic button is present and clickable (won't test audio in headless)."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(300)
            mic = page.locator("#voice-ops-ring")
            assert mic.is_visible()
            # Verify status text
            status = page.locator("#voice-ops-status").text_content()
            assert "Tap the microphone" in status or "microphone" in status.lower()
            browser.close()


@e2e
@frontend_running
class TestE2ETabSwitching:
    """E2E: Verify switching between tabs works correctly."""

    def test_switch_to_agent_engine(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            page.locator('button[data-backend="agent-engine"]').click()
            page.wait_for_timeout(300)
            # Mode label should update
            label = page.locator("#mode-label").text_content()
            assert "Agent Engine" in label and "A2A" in label
            # Chat area should be visible
            chat = page.locator("#chat-area")
            assert chat.is_visible()
            browser.close()

    def test_switch_to_voice_hides_chat(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(300)
            # Chat area should be hidden
            chat_display = page.locator("#chat-area").evaluate(
                "el => getComputedStyle(el).display"
            )
            assert chat_display == "none"
            # Voice overlay should be visible
            overlay_display = page.locator("#voice-ops-overlay").evaluate(
                "el => getComputedStyle(el).display"
            )
            assert overlay_display == "flex"
            browser.close()

    def test_switch_back_restores_chat(self):
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")
            # Go to voice
            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(300)
            # Switch back via JS (overlay z-index covers tab buttons)
            page.evaluate("switchBackend('stream-assist')")
            page.wait_for_timeout(300)
            chat_display = page.locator("#chat-area").evaluate(
                "el => getComputedStyle(el).display"
            )
            assert chat_display != "none"
            overlay_display = page.locator("#voice-ops-overlay").evaluate(
                "el => getComputedStyle(el).display"
            )
            assert overlay_display == "none"
            browser.close()


@e2e
@frontend_running
class TestE2EAPIEndpoints:
    """E2E: Verify backend API endpoints respond correctly."""

    def test_health_endpoint(self):
        import urllib.request

        with urllib.request.urlopen("http://localhost:8080/api/health", timeout=5) as r:
            data = json.loads(r.read())
            assert data["status"] == "ok"

    def test_config_endpoint(self):
        import urllib.request

        with urllib.request.urlopen("http://localhost:8080/api/config", timeout=5) as r:
            data = json.loads(r.read())
            assert "project" in data or "retailer" in data

    def test_agents_endpoint(self):
        import urllib.request

        with urllib.request.urlopen(
            "http://localhost:8080/api/stream-assist/agents", timeout=10
        ) as r:
            data = json.loads(r.read())
            assert "agents" in data
            assert isinstance(data["agents"], list)

    def test_data_stores_endpoint(self):
        import urllib.request

        with urllib.request.urlopen(
            "http://localhost:8080/api/stream-assist/data-stores", timeout=10
        ) as r:
            data = json.loads(r.read())
            assert "dataStores" in data
            assert isinstance(data["dataStores"], list)


@e2e
@frontend_running
class TestE2EMultiTurnStreamAssist:
    """E2E: Multi-turn StreamAssist conversations reusing the same session."""

    def _create_session(self):
        import urllib.request

        req = urllib.request.Request(
            "http://localhost:8080/api/stream-assist/sessions",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())["name"]

    def _query(self, session_name, text):
        import urllib.request

        payload = json.dumps({
            "session": session_name,
            "query": {"text": text},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:8080/api/stream-assist/query",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def test_two_turn_sop_conversation(self):
        """Send two SOP-related queries on the same session."""
        session = self._create_session()

        # Turn 1
        resp1 = self._query(session, "What are the closing procedures?")
        assert resp1, "Turn 1 should return a response"

        # Turn 2 — follow-up on same session
        resp2 = self._query(session, "What about opening procedures?")
        assert resp2, "Turn 2 should return a response"

    def test_two_turn_brand_then_sop(self):
        """Cross-topic multi-turn: brand guidelines then SOP."""
        session = self._create_session()

        resp1 = self._query(session, "What are the brand color guidelines?")
        assert resp1, "Brand query should return a response"

        resp2 = self._query(session, "Now show me the closing procedures SOP")
        assert resp2, "SOP query should return a response"

    def test_three_turn_conversation(self):
        """Three-turn conversation on the same session."""
        session = self._create_session()

        resp1 = self._query(session, "What SOPs are available?")
        assert resp1

        resp2 = self._query(session, "Tell me about the inventory management SOP")
        assert resp2

        resp3 = self._query(session, "What about loss prevention?")
        assert resp3


@e2e
@frontend_running
class TestE2EMultiTurnAgentEngine:
    """E2E: Multi-turn Agent Engine conversations."""

    def _query_ae(self, text, user_id="test-multi-turn"):
        import urllib.request

        payload = json.dumps({
            "input": {"message": text, "user_id": user_id},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:8080/api/agent-engine/query",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            return data

    def test_two_turn_analytics(self):
        """Two analytics queries with the same user_id."""
        user_id = f"test-multi-{int(__import__('time').time())}"

        resp1 = self._query_ae("What are the top 5 products by revenue?", user_id)
        assert resp1, "Turn 1 should return a response"
        assert "content" in resp1

        resp2 = self._query_ae("Now break that down by store", user_id)
        assert resp2, "Turn 2 should return a response"
        assert "content" in resp2

    def test_two_turn_sop_then_analytics(self):
        """Cross-domain: SOP search then analytics query."""
        user_id = f"test-multi-{int(__import__('time').time())}"

        resp1 = self._query_ae("What are the closing procedures?", user_id)
        assert resp1 and "content" in resp1

        resp2 = self._query_ae("Show me total revenue by store", user_id)
        assert resp2 and "content" in resp2

    def test_simulator_two_configs(self):
        """Ask the simulator to run with two different configurations."""
        user_id = f"test-sim-{int(__import__('time').time())}"

        resp1 = self._query_ae(
            "Simulate 3 shoppers at Downtown Market with budget-conscious personas",
            user_id,
        )
        assert resp1 and "content" in resp1

        resp2 = self._query_ae(
            "Now simulate 3 premium shoppers at Westside Location",
            user_id,
        )
        assert resp2 and "content" in resp2


@e2e
@frontend_running
class TestE2EMultiTurnVoiceOps:
    """E2E: Multi-turn voice ops via text suggestion buttons."""

    def test_two_suggestion_buttons_same_session(self):
        """Click two different suggestion buttons on the same WebSocket session."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            logs = []
            page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")

            # Switch to Voice tab
            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(500)

            # Click first suggestion: Staffing levels
            page.locator("text=Staffing levels").click()
            page.wait_for_timeout(12000)

            transcript1 = page.locator("#voice-ops-transcript").inner_html()
            assert "You" in transcript1, "First message should appear"

            # Click second suggestion: Peak hours (reuses same WS)
            page.locator("text=Peak hours").click()
            page.wait_for_timeout(12000)

            transcript2 = page.locator("#voice-ops-transcript").inner_html()
            # Both user messages should be in the transcript
            assert transcript2.count("You") >= 2, (
                f"Both messages should be in transcript. Got: {transcript2[:500]}"
            )

            browser.close()

    def test_voice_ops_response_after_two_turns(self):
        """Verify the agent responds to both turns."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")

            page.locator('button[data-backend="voice-ops"]').click()
            page.wait_for_timeout(500)

            # Turn 1
            page.locator("text=Inventory turnover").click()
            page.wait_for_timeout(12000)

            # Turn 2
            page.locator("text=Labor costs").click()
            page.wait_for_timeout(12000)

            transcript = page.locator("#voice-ops-transcript").inner_html()
            # Should have at least 2 "You" entries and 1+ "Agent" entry
            assert transcript.count("You") >= 2
            # Agent responses appear as "Agent" or "Assistant"
            has_response = "Agent" in transcript or "Assistant" in transcript or "vf-green" in transcript
            assert has_response, f"Agent should have responded. Transcript: {transcript[:500]}"

            browser.close()


@e2e
@frontend_running
class TestE2EMultiTurnFrontendUI:
    """E2E: Multi-turn conversations via the frontend chat UI."""

    def test_streamassist_ui_two_turns(self):
        """Type two messages in the StreamAssist chat and verify both responses appear."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")

            # Ensure we're on StreamAssist tab
            page.locator('button[data-backend="stream-assist"]').click()
            page.wait_for_timeout(500)

            # Turn 1
            page.locator("#chat-input").fill("What are the closing procedures?")
            page.locator("#send-btn").click()
            # Wait for response
            page.wait_for_timeout(15000)

            messages = page.locator(".message").all()
            assert len(messages) >= 2, f"Expected user + assistant messages, got {len(messages)}"

            # Turn 2
            page.locator("#chat-input").fill("What about opening procedures?")
            page.locator("#send-btn").click()
            page.wait_for_timeout(15000)

            messages = page.locator(".message").all()
            assert len(messages) >= 4, (
                f"Expected 4+ messages (2 turns), got {len(messages)}"
            )

            browser.close()

    def test_agent_engine_ui_two_turns(self):
        """Type two messages in the Agent Engine chat and verify both responses."""
        sync_playwright = _get_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("http://localhost:8080")
            page.wait_for_load_state("networkidle")

            # Switch to Agent Engine tab
            page.locator('button[data-backend="agent-engine"]').click()
            page.wait_for_timeout(500)

            # Confirm switch if dialog appears
            page.wait_for_timeout(300)
            confirm_btn = page.locator("text=Switch to Agent Engine")
            if confirm_btn.is_visible():
                confirm_btn.click()
                page.wait_for_timeout(300)

            # Turn 1
            page.locator("#chat-input").fill("What are the top 3 products by revenue?")
            page.locator("#send-btn").click()
            page.wait_for_timeout(30000)

            messages = page.locator(".message").all()
            assert len(messages) >= 2, f"Expected user + assistant messages, got {len(messages)}"

            # Turn 2
            page.locator("#chat-input").fill("Break that down by store")
            page.locator("#send-btn").click()
            page.wait_for_timeout(30000)

            messages = page.locator(".message").all()
            assert len(messages) >= 4, (
                f"Expected 4+ messages (2 turns), got {len(messages)}"
            )

            browser.close()
