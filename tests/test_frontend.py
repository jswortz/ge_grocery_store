"""Unit tests for frontend HTML and server.py changes.

Validates the sprint bug fixes and enhancements without requiring
a running server or GCP credentials.
"""

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Paths
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "src" / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
SERVER_PY = FRONTEND_DIR / "server.py"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


@pytest.fixture
def html_content():
    """Load the frontend HTML file."""
    return INDEX_HTML.read_text()


@pytest.fixture
def server_content():
    """Load the server.py file."""
    return SERVER_PY.read_text()


@pytest.fixture
def config_content():
    """Load settings.yaml."""
    import yaml
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ================================================================
# 1. Compare Tab Removal
# ================================================================
class TestCompareTabRemoval:

    def test_no_compare_tab_button(self, html_content):
        """Compare tab button should be removed from HTML."""
        assert 'data-backend="compare"' not in html_content

    def test_no_compare_css(self, html_content):
        """Compare mode CSS classes should be removed."""
        assert ".compare-row" not in html_content
        assert ".compare-cell" not in html_content

    def test_no_send_compare_query_function(self, html_content):
        """sendCompareQuery function should be removed."""
        assert "sendCompareQuery" not in html_content

    def test_no_compare_in_send_message(self, html_content):
        """sendMessage should not reference compare mode."""
        # Extract the sendMessage function body
        assert "backend === 'compare'" not in html_content

    def test_no_compare_in_state_comment(self, html_content):
        """State backend union type should not mention compare."""
        # Check the State object doesn't list 'compare' as an option
        state_match = re.search(r"backend:.*//.*", html_content)
        if state_match:
            assert "'compare'" not in state_match.group(0)


# ================================================================
# 2. Imagen Label Replacement
# ================================================================
class TestImagenLabelReplacement:

    def test_frontend_uses_gemini_image(self, html_content):
        """Frontend should use 'Gemini Image' not 'Imagen'."""
        assert "Gemini Image" in html_content
        # Should not have bare "Imagen" as a label (OK in URLs/config keys)
        assert "Creative &middot; Imagen" not in html_content

    def test_agent_py_no_imagen_comment(self):
        """agent.py comment should say 'Gemini Image' not 'Imagen'."""
        agent_py = (Path(__file__).resolve().parent.parent
                    / "src" / "agent" / "agent.py").read_text()
        assert "Gemini Image" in agent_py
        assert "Imagen for actual gen" not in agent_py

    def test_image_gen_tool_docstring(self):
        """image_gen_tool.py docstring should reference Gemini Image."""
        tool_py = (Path(__file__).resolve().parent.parent
                   / "src" / "agent" / "tools" / "image_gen_tool.py").read_text()
        assert "Gemini 3 Pro Image" in tool_py
        assert "legacy Imagen API" not in tool_py

    def test_a2a_agent_uses_gemini_image(self):
        """A2A agent description should say 'Gemini Image'."""
        a2a_py = (Path(__file__).resolve().parent.parent
                  / "src" / "a2a_agent" / "agent.py").read_text()
        assert "Gemini Image" in a2a_py
        assert "Vertex AI Imagen" not in a2a_py

    def test_config_imagen_key_preserved(self, config_content):
        """Config key 'imagen' should be preserved for backward compat."""
        assert "imagen" in config_content.get("models", {})


# ================================================================
# 3. Data Source Toggle
# ================================================================
class TestDataSourceToggle:

    def test_no_empty_returns_empty(self, html_content):
        """When no stores selected, should return a dummy store spec."""
        # The old code returned [] when size === 0; new code should NOT
        assert "_none_" in html_content

    def test_all_selected_returns_explicit_list(self, html_content):
        """When all stores selected, should return explicit list (not empty)."""
        # The old early-return of [] when all selected is removed;
        # all selected stores are always sent explicitly so workspace
        # connectors (Gmail, Calendar, Jira) are included.
        assert "State.selectedDataStores.size === State.allDataStoreIds.length" not in html_content
        assert "Array.from(State.selectedDataStores).map" in html_content


# ================================================================
# 4. Agent Selector for Agent Engine
# ================================================================
class TestAgentSelectorForAgentEngine:

    def test_agent_selector_visible_for_all_backends(self, html_content):
        """Agent selector should be visible for all backends except voice-ops."""
        assert "State.backend !== 'voice-ops'" in html_content

    def test_rebuild_agent_selector_exists(self, html_content):
        """rebuildAgentSelector function should exist."""
        assert "function rebuildAgentSelector()" in html_content

    def test_state_has_agent_engines(self, html_content):
        """State should have agentEngines array."""
        assert "agentEngines: []" in html_content

    def test_state_has_selected_agent_engine_id(self, html_content):
        """State should have selectedAgentEngineId."""
        assert "selectedAgentEngineId:" in html_content


# ================================================================
# 5. Sample Question Routing
# ================================================================
class TestSampleQuestionRouting:

    def test_analytics_sample_routes_to_mcp_agent(self, html_content):
        """Analytics sample should route to MCP Grocery Analyst on Agent Engine."""
        assert "sendSample('What are the top 5 products by revenue?', {backend:'agent-engine', agentId:'5787744546217525248'})" in html_content

    def test_image_sample_routes_to_agent_engine(self, html_content):
        """Image generation sample should route to agent-engine backend with explicit agent ID."""
        assert "sendSample('Generate a product image" in html_content
        assert "agentId:'3727910666648944640'" in html_content

    def test_simulator_sample_routes_to_agent_engine(self, html_content):
        """Simulator sample should route to agent-engine with simulator agent ID."""
        assert "sendSample('Simulate 5 shoppers" in html_content
        assert "agentId:'7053256041508634624'" in html_content

    def test_simulator_sample_label_not_a2a(self, html_content):
        """Simulator sample button should NOT say 'A2A Simulator' (it's not A2A protocol)."""
        assert "A2A Simulator" not in html_content

    def test_simulator_sample_label_correct(self, html_content):
        """Simulator sample button should say 'Shopper Simulator'."""
        assert "Shopper Simulator" in html_content

    def test_simulator_arch_panel_agent_name(self, html_content):
        """Architecture panel should use correct agent name 'simulator_orchestrator'."""
        assert "simulator_orchestrator" in html_content
        assert "simulation_orchestrator" not in html_content

    def test_simulator_arch_panel_shows_tools(self, html_content):
        """Architecture panel for simulator should show its tools."""
        assert "compare_endcap_strategies" in html_content
        assert "list_endcap_strategies" in html_content
        assert "generate_simulation_report" in html_content

    def test_send_sample_accepts_opts(self, html_content):
        """sendSample should accept an opts parameter."""
        assert "function sendSample(text, opts)" in html_content


# ================================================================
# 6. Auto-Route Image Requests
# ================================================================
class TestImageAutoRouting:

    def test_image_request_detection_regex(self, html_content):
        """sendMessage should detect image generation requests."""
        assert "isImageRequest" in html_content
        assert "generate|create|make|design" in html_content

    def test_routing_indicator_message(self, html_content):
        """Should show routing indicator when auto-routing."""
        assert "Routing to Agent Engine for image generation" in html_content


# ================================================================
# 7. Voice Transcript in Main Chat
# ================================================================
class TestVoiceTranscriptMirroring:

    def test_voice_ops_streams_assistant_to_chat(self, html_content):
        """Voice ops text/plain should stream to main chat via streaming helpers."""
        assert "addStreamingMessage" in html_content
        assert "updateStreamingMessage" in html_content
        assert "finalizeStreamingMessage" in html_content

    def test_voice_ops_finalizes_on_turn_complete(self, html_content):
        """Voice ops turn_complete should finalize the streaming message."""
        turn_complete_section = html_content[html_content.find("msg.turn_complete"):]
        assert "finalizeStreamingMessage(voiceOpsChatStreamEl, currentText)" in turn_complete_section

    def test_voice_ops_mirrors_user_to_chat(self, html_content):
        """_sendVoiceOpsTextMessage should mirror user to main chat."""
        fn_section = html_content[html_content.find("function _sendVoiceOpsTextMessage"):]
        assert "addMessage('user', text)" in fn_section

    def test_voice_ops_chat_stream_element_declared(self, html_content):
        """voiceOpsChatStreamEl variable should be declared."""
        assert "voiceOpsChatStreamEl" in html_content


# ================================================================
# 8. CLTV Sample Button
# ================================================================
class TestCLTVRouting:

    def test_cltv_sample_button_exists(self, html_content):
        """CLTV sample button should exist."""
        assert "Customer lifetime value" in html_content

    def test_cltv_routes_to_stream_assist(self, html_content):
        """CLTV should route to StreamAssist (data insights agent)."""
        assert "customer lifetime value" in html_content.lower()
        assert "Data Insights Agent" in html_content


# ================================================================
# 9. Architecture Panel
# ================================================================
class TestArchitecturePanel:

    def test_arch_panel_exists(self, html_content):
        """Architecture panel div should exist."""
        assert 'id="arch-panel"' in html_content

    def test_toggle_arch_panel_function(self, html_content):
        """toggleArchPanel function should exist."""
        assert "function toggleArchPanel()" in html_content

    def test_arch_tree_builder_defined(self, html_content):
        """buildArchTree function should handle all backends."""
        assert "buildArchTree" in html_content
        assert "'stream-assist'" in html_content
        assert "'agent-engine'" in html_content


# ================================================================
# 10. Model Card Info
# ================================================================
class TestModelCardInfo:

    def test_model_card_wrap_exists(self, html_content):
        """Model card wrap element should exist."""
        assert 'id="model-card-wrap"' in html_content

    def test_update_model_card_function(self, html_content):
        """updateModelCard function should exist."""
        assert "function updateModelCard()" in html_content

    def test_server_exposes_agent_engines(self, server_content):
        """Server /api/config should expose agent_engines list."""
        assert '"agent_engines"' in server_content

    def test_server_agent_engines_have_model(self, server_content):
        """Agent engine entries should include model field."""
        assert '"model":' in server_content
        assert '"resource_name":' in server_content

    def test_server_supports_resource_id_override(self, server_content):
        """Agent Engine proxy should support resource_id override."""
        assert "resource_id" in server_content

    def test_server_simulation_report_endpoint(self, server_content):
        """Server should have a /api/simulation-report endpoint."""
        assert "/api/simulation-report" in server_content
        assert "simulation_report.html" in server_content

    def test_server_simulator_model_config(self, server_content):
        """Simulator config should use adk_fast model (with adk fallback)."""
        assert "adk_fast" in server_content


# ================================================================
# Forbidden Name Check
# ================================================================
class TestForbiddenNames:

    def test_no_hardcoded_retailer_names_html(self, html_content):
        """HTML should not contain hardcoded retailer names."""
        lower = html_content.lower()
        assert "kroger" not in lower
        assert "heb" not in lower.split()

    def test_no_hardcoded_retailer_names_server(self, server_content):
        """server.py should not contain hardcoded retailer names."""
        lower = server_content.lower()
        assert "kroger" not in lower
        assert "heb" not in lower.split()


# ================================================================
# 11. Agent Engine Thinking Display
# ================================================================
class TestAgentEngineThinkingDisplay:

    def test_parse_agent_engine_response_returns_object(self, html_content):
        """parseAgentEngineResponse should return {text, thoughts} object."""
        fn_section = html_content[html_content.find("function parseAgentEngineResponse"):]
        fn_end = fn_section.find("\n// ==")
        fn_body = fn_section[:fn_end] if fn_end > 0 else fn_section[:500]
        assert "const thoughts = []" in fn_body
        assert "return { text, thoughts }" in fn_body

    def test_parse_agent_engine_response_filters_thoughts(self, html_content):
        """parseAgentEngineResponse should filter on part.thought (not thought_signature)."""
        fn_section = html_content[html_content.find("function parseAgentEngineResponse"):]
        fn_end = fn_section.find("\n// ==")
        fn_body = fn_section[:fn_end] if fn_end > 0 else fn_section[:500]
        assert "part.thought" in fn_body
        # thought_signature is a crypto signature on real responses — filtering on
        # it discards actual text. The correct filter is part.thought.
        assert "thought_signature" not in fn_body

    def test_parse_agent_engine_response_captures_function_calls(self, html_content):
        """parseAgentEngineResponse should capture functionCall as thoughts."""
        fn_section = html_content[html_content.find("function parseAgentEngineResponse"):]
        fn_end = fn_section.find("\n// ==")
        fn_body = fn_section[:fn_end] if fn_end > 0 else fn_section[:500]
        assert "functionCall" in fn_body
        assert "Tool Call" in fn_body


# ================================================================
# 12. Data Source Selectors Hidden for Non-StreamAssist
# ================================================================
class TestDataSourceSelectorVisibility:

    def test_data_sources_hidden_for_non_stream_assist(self, html_content):
        """Data sources panel and button should be hidden for non-StreamAssist backends."""
        fn_section = html_content[html_content.find("function updateAgentSelectorVisibility"):]
        fn_end = fn_section.find("\nfunction updateModelCard")
        fn_body = fn_section[:fn_end] if fn_end > 0 else fn_section[:500]
        assert "stream-assist" in fn_body
        # Button should have an ID for visibility control
        assert 'id="data-sources-btn"' in html_content
        # Button visibility should be toggled based on backend
        assert "data-sources-btn" in fn_body


# ================================================================
# 13. StreamAssist ADK/A2A Auto-Routing
# ================================================================
class TestStreamAssistAutoRouting:

    def test_adk_a2a_agent_detection(self, html_content):
        """sendMessage should detect ADK/A2A agents for auto-routing."""
        assert "isAgentEngineAgent" in html_content
        assert "selectedAgentInfo.type === 'adk'" in html_content or \
               "selectedAgentInfo.type === 'a2a'" in html_content

    def test_agent_engine_mapping_in_server(self, server_content):
        """Server /api/config should include agent_engine_mapping."""
        assert "agent_engine_mapping" in server_content

    def test_auto_route_uses_mapping(self, html_content):
        """Auto-routing should look up resource ID from mapping."""
        assert "agent_engine_mapping" in html_content
        assert "aeMapping" in html_content


# ================================================================
# 14. Agent Refactor — sop_agent
# ================================================================
class TestAgentRefactor:

    def test_frontend_arch_tree_uses_sop_agent(self, html_content):
        """Frontend architecture tree should show sop_agent not grocery_assistant."""
        assert "'sop_agent'" in html_content
        assert "'grocery_assistant'" not in html_content
