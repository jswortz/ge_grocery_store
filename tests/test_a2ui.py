"""Unit tests for A2UI (Agent-to-User Interface) integration.

Validates A2UI prompt generation, schema compliance, component catalog
coverage, deploy script requirements, and frontend rendering support
across all agents (main, MCP, simulator, A2A).
"""

import json
import re
from unittest.mock import patch

import pytest


# ── A2UI SDK Availability ────────────────────────────────────────────────────

class TestA2UISDKAvailability:

    def test_a2ui_sdk_importable(self):
        from a2ui.schema.manager import A2uiSchemaManager
        from a2ui.basic_catalog.provider import BasicCatalog
        assert A2uiSchemaManager is not None
        assert BasicCatalog is not None

    def test_a2ui_schema_manager_version(self):
        from a2ui.schema.manager import A2uiSchemaManager
        from a2ui.basic_catalog.provider import BasicCatalog
        mgr = A2uiSchemaManager(
            version='0.8',
            catalogs=[BasicCatalog.get_config('0.8')],
        )
        assert mgr is not None

    def test_a2ui_generates_system_prompt(self):
        from a2ui.schema.manager import A2uiSchemaManager
        from a2ui.basic_catalog.provider import BasicCatalog
        mgr = A2uiSchemaManager(
            version='0.8',
            catalogs=[BasicCatalog.get_config('0.8')],
        )
        prompt = mgr.generate_system_prompt(
            role_description="test agent",
            ui_description="test UI",
        )
        assert len(prompt) > 100
        assert "a2ui" in prompt.lower() or "component" in prompt.lower()


# ── Main Agent A2UI Prompt ───────────────────────────────────────────────────

class TestMainAgentA2UI:

    def test_main_instruction_contains_a2ui(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "<a2ui-json>" in instruction
        assert "</a2ui-json>" in instruction

    def test_main_instruction_has_begin_rendering(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "beginRendering" in instruction

    def test_main_instruction_has_surface_update(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "surfaceUpdate" in instruction

    def _find_valid_a2ui_block(self, text):
        """Find the first valid JSON A2UI block in text."""
        for match in re.finditer(r'<a2ui-json>([\s\S]*?)</a2ui-json>', text):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list) and len(data) >= 2:
                    return data, match.group(1)
            except (json.JSONDecodeError, ValueError):
                continue
        return None, None

    def test_main_a2ui_example_is_valid_json(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        data, _ = self._find_valid_a2ui_block(instruction)
        assert data is not None, "No valid <a2ui-json> block found in main instruction"
        assert len(data) >= 2

    def test_main_a2ui_example_has_correct_structure(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        data, _ = self._find_valid_a2ui_block(instruction)
        assert "beginRendering" in data[0]
        assert "surfaceUpdate" in data[1]
        assert "components" in data[1]["surfaceUpdate"]

    def test_main_a2ui_example_uses_card_component(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        _, raw = self._find_valid_a2ui_block(instruction)
        assert '"Card"' in raw

    def test_main_a2ui_suffix_function_returns_nonempty(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        suffix = get_a2ui_prompt_suffix()
        assert len(suffix) > 0

    def test_main_a2ui_suffix_has_rules(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        suffix = get_a2ui_prompt_suffix()
        assert "Rules:" in suffix or "RULES:" in suffix
        assert "beginRendering" in suffix
        assert "explicitList" in suffix


# ── MCP Agent A2UI Prompt ────────────────────────────────────────────────────

class TestMCPAgentA2UI:

    def test_mcp_a2ui_suffix_returns_nonempty(self):
        from src.mcp_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        assert len(suffix) > 0

    def test_mcp_a2ui_contains_json_block(self):
        from src.mcp_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        assert "<a2ui-json>" in suffix
        assert "</a2ui-json>" in suffix

    def test_mcp_a2ui_example_is_valid_json(self):
        from src.mcp_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        found = False
        for match in re.finditer(r'<a2ui-json>\s*(\[[\s\S]*?\])\s*</a2ui-json>', suffix):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    found = True
                    break
            except (json.JSONDecodeError, ValueError):
                continue
        assert found, "No valid <a2ui-json> block found in MCP agent suffix"

    def test_mcp_a2ui_mentions_analytics(self):
        from src.mcp_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        assert "analytics" in suffix.lower() or "data" in suffix.lower()

    def test_mcp_instruction_includes_a2ui(self):
        from src.mcp_agent.agent import _get_agent_instruction, _load_config
        config = _load_config()
        instruction = _get_agent_instruction(config)
        assert "<a2ui-json>" in instruction


# ── Simulator Agent A2UI Prompt ──────────────────────────────────────────────

class TestSimulatorAgentA2UI:

    def test_simulator_a2ui_suffix_returns_nonempty(self):
        from src.simulator_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        assert len(suffix) > 0

    def test_simulator_a2ui_contains_json_block(self):
        from src.simulator_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        assert "<a2ui-json>" in suffix
        assert "</a2ui-json>" in suffix

    def test_simulator_a2ui_example_is_valid_json(self):
        from src.simulator_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        found = False
        for match in re.finditer(r'<a2ui-json>([\s\S]*?)</a2ui-json>', suffix):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list) and len(data) >= 2:
                    assert "beginRendering" in data[0]
                    found = True
                    break
            except (json.JSONDecodeError, ValueError):
                continue
        assert found, "No valid <a2ui-json> block found in simulator suffix"

    def test_simulator_a2ui_mentions_ab_test(self):
        from src.simulator_agent.agent import _get_a2ui_suffix
        suffix = _get_a2ui_suffix()
        assert "strategy" in suffix.lower() or "a/b" in suffix.lower() or "comparison" in suffix.lower()


# ── A2A Agent A2UI AgentCard ─────────────────────────────────────────────────

class TestA2AAgentA2UI:

    A2UI_V08_COMPONENTS = [
        "Text", "Image", "Icon", "Video", "AudioPlayer",
        "Row", "Column", "List", "Card", "Tabs",
        "Divider", "Modal", "Button", "CheckBox",
        "TextField", "DateTimeInput", "MultipleChoice", "Slider",
    ]

    def test_a2a_agent_card_has_a2ui_capability(self):
        from src.a2a_agent.server import _build_agent_card
        card = _build_agent_card()
        assert card.capabilities.extensions is not None
        ext_uris = [e.uri for e in card.capabilities.extensions]
        assert any("a2ui" in uri for uri in ext_uris)

    def test_a2a_agent_card_a2ui_version(self):
        from src.a2a_agent.server import _build_agent_card
        card = _build_agent_card()
        ext_uris = [e.uri for e in card.capabilities.extensions]
        assert any("v0.8" in uri for uri in ext_uris)

    def test_a2a_agent_card_a2ui_extension_is_proper_type(self):
        from src.a2a_agent.server import _build_agent_card
        from a2a.types import AgentExtension
        card = _build_agent_card()
        for ext in card.capabilities.extensions:
            assert isinstance(ext, AgentExtension)

    def test_a2a_instruction_includes_a2ui(self):
        """The A2A agent's system prompt should include A2UI instructions."""
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        suffix = get_a2ui_prompt_suffix()
        assert "<a2ui-json>" in suffix


class TestSimulatorA2AAgentA2UI:

    def test_simulator_a2a_card_has_a2ui_capability(self):
        from src.simulator_agent.server import _build_agent_card
        card = _build_agent_card()
        assert card.capabilities.extensions is not None
        ext_uris = [e.uri for e in card.capabilities.extensions]
        assert any("a2ui" in uri for uri in ext_uris)

    def test_simulator_a2a_card_a2ui_version(self):
        from src.simulator_agent.server import _build_agent_card
        card = _build_agent_card()
        ext_uris = [e.uri for e in card.capabilities.extensions]
        assert any("v0.8" in uri for uri in ext_uris)

    def test_simulator_a2a_card_a2ui_extension_is_proper_type(self):
        from src.simulator_agent.server import _build_agent_card
        from a2a.types import AgentExtension
        card = _build_agent_card()
        for ext in card.capabilities.extensions:
            assert isinstance(ext, AgentExtension)


# ── Deploy Script Requirements ───────────────────────────────────────────────

class TestDeployScriptA2UI:

    def _read_deploy_script(self, path):
        with open(path) as f:
            return f.read()

    def test_main_deploy_has_a2ui_sdk_requirement(self):
        content = self._read_deploy_script("src/agent/deploy_to_agent_engine.py")
        assert "a2ui-agent-sdk" in content

    def test_mcp_deploy_has_a2ui_sdk_requirement(self):
        content = self._read_deploy_script("src/mcp_agent/deploy_to_agent_engine.py")
        assert "a2ui-agent-sdk" in content

    def test_simulator_deploy_has_a2ui_sdk_requirement(self):
        content = self._read_deploy_script("src/simulator_agent/deploy_to_agent_engine.py")
        assert "a2ui-agent-sdk" in content

    def test_main_deploy_has_a2ui_prompt(self):
        content = self._read_deploy_script("src/agent/deploy_to_agent_engine.py")
        assert "a2ui" in content.lower()
        assert "A2uiSchemaManager" in content

    def test_mcp_deploy_has_a2ui_prompt(self):
        content = self._read_deploy_script("src/mcp_agent/deploy_to_agent_engine.py")
        assert "a2ui" in content.lower()

    def test_simulator_deploy_has_a2ui_prompt(self):
        content = self._read_deploy_script("src/simulator_agent/deploy_to_agent_engine.py")
        assert "a2ui" in content.lower()

    def test_deploy_scripts_pin_adk_below_v2(self):
        """All deploy scripts must pin google-adk<2.0.0 to avoid breaking changes."""
        for path in [
            "src/agent/deploy_to_agent_engine.py",
            "src/mcp_agent/deploy_to_agent_engine.py",
            "src/simulator_agent/deploy_to_agent_engine.py",
        ]:
            content = self._read_deploy_script(path)
            assert "<2.0.0" in content, f"{path} missing google-adk<2.0.0 pin"


# ── A2UI JSON Schema Validation ──────────────────────────────────────────────

class TestA2UISchemaCompliance:
    """Validate that the A2UI JSON examples in prompts are schema-compliant."""

    def _extract_a2ui_blocks(self, text):
        """Extract valid A2UI JSON blocks from a string (skip SDK instruction text)."""
        blocks = []
        for match in re.finditer(r'<a2ui-json>([\s\S]*?)</a2ui-json>', text):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    blocks.append(data)
            except (json.JSONDecodeError, ValueError):
                pass
        return blocks

    def test_all_blocks_start_with_begin_rendering(self):
        """Every A2UI block must start with a beginRendering message."""
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            blocks = self._extract_a2ui_blocks(suffix_fn())
            for i, block in enumerate(blocks):
                assert "beginRendering" in block[0], (
                    f"{name} block {i}: first message must be beginRendering"
                )

    def test_all_blocks_have_surface_update(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            blocks = self._extract_a2ui_blocks(suffix_fn())
            for i, block in enumerate(blocks):
                has_update = any("surfaceUpdate" in msg for msg in block)
                assert has_update, f"{name} block {i}: missing surfaceUpdate"

    def test_surface_updates_have_components(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            blocks = self._extract_a2ui_blocks(suffix_fn())
            for i, block in enumerate(blocks):
                for msg in block:
                    if "surfaceUpdate" in msg:
                        comps = msg["surfaceUpdate"].get("components", [])
                        assert len(comps) > 0, (
                            f"{name} block {i}: surfaceUpdate has no components"
                        )

    def test_components_have_id_and_component_key(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            blocks = self._extract_a2ui_blocks(suffix_fn())
            for block in blocks:
                for msg in block:
                    if "surfaceUpdate" in msg:
                        for comp in msg["surfaceUpdate"]["components"]:
                            assert "id" in comp, f"{name}: component missing 'id'"
                            assert "component" in comp, f"{name}: component missing 'component'"

    def test_children_use_explicit_list(self):
        """Children references must use explicitList with string IDs."""
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        blocks = self._extract_a2ui_blocks(get_a2ui_prompt_suffix())
        for block in blocks:
            for msg in block:
                if "surfaceUpdate" in msg:
                    for comp in msg["surfaceUpdate"]["components"]:
                        c = list(comp["component"].values())[0]
                        if isinstance(c, dict) and "children" in c:
                            assert "explicitList" in c["children"]
                            assert isinstance(c["children"]["explicitList"], list)

    def test_begin_rendering_has_surface_id_and_root(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        blocks = self._extract_a2ui_blocks(get_a2ui_prompt_suffix())
        for block in blocks:
            br = block[0]["beginRendering"]
            assert "surfaceId" in br
            assert "root" in br


# ── Frontend A2UI Rendering Coverage ─────────────────────────────────────────

class TestFrontendA2UIRendering:
    """Validate the frontend index.html has renderers for all 18 A2UI v0.8 components."""

    COMPONENT_TYPES = [
        "Text", "Image", "Icon", "Video", "AudioPlayer",
        "Row", "Column", "List", "Card", "Tabs",
        "Divider", "Modal", "Button", "CheckBox",
        "TextField", "DateTimeInput", "MultipleChoice", "Slider",
    ]

    @pytest.fixture(autouse=True)
    def load_frontend(self):
        with open("src/frontend/index.html") as f:
            self.html = f.read()

    def test_has_a2ui_container_detection(self):
        assert "containsA2UI" in self.html

    def test_has_a2ui_json_parser(self):
        assert "parseBlocks" in self.html
        assert "<a2ui-json>" in self.html

    def test_has_render_component_function(self):
        assert "renderComponent" in self.html

    def test_has_render_surface_function(self):
        assert "renderSurface" in self.html

    def test_has_render_children_helper(self):
        assert "_renderChildren" in self.html

    @pytest.mark.parametrize("component", COMPONENT_TYPES)
    def test_component_has_case_handler(self, component):
        """Each A2UI component type must have a case in the renderComponent switch."""
        pattern = f"case '{component}'"
        assert pattern in self.html, f"Missing case handler for '{component}'"

    CSS_CLASS_MAP = {
        "AudioPlayer": "a2ui-audio",
        "DateTimeInput": "a2ui-datetime",
        "MultipleChoice": "a2ui-multiplechoice",
        "CheckBox": "a2ui-checkbox",
        "TextField": "a2ui-textfield",
    }

    @pytest.mark.parametrize("component", COMPONENT_TYPES)
    def test_component_has_css_class(self, component):
        """Each component should have an a2ui-* CSS class defined."""
        css_class = self.CSS_CLASS_MAP.get(component, f"a2ui-{component.lower()}")
        assert css_class in self.html, f"Missing CSS class '{css_class}'"

    def test_interactive_components_are_readonly(self):
        """Interactive components (CheckBox, TextField, Slider) should be disabled/readonly."""
        assert "cb.disabled = true" in self.html or "disabled = true" in self.html
        assert "readOnly = true" in self.html

    def test_unknown_component_fallback(self):
        assert "a2ui-unknown" in self.html

    def test_a2ui_surface_css_exists(self):
        assert ".a2ui-surface" in self.html

    def test_a2ui_card_css_has_hover(self):
        assert ".a2ui-card:hover" in self.html


# ── Cross-Agent A2UI Consistency ─────────────────────────────────────────────

class TestA2UICrossAgentConsistency:
    """Ensure all agents use consistent A2UI patterns."""

    def test_all_agents_use_same_a2ui_version(self):
        """All A2UI integrations must use version 0.8."""
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            suffix = suffix_fn()
            assert "0.8" in suffix or len(suffix) > 0, f"{name}: A2UI suffix empty"

    def test_all_agents_include_a2ui_rules(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            suffix = suffix_fn()
            assert "Rules:" in suffix or "RULES:" in suffix, f"{name}: missing A2UI Rules section"
            assert "beginRendering" in suffix, f"{name}: rules don't mention beginRendering"
            assert "explicitList" in suffix, f"{name}: rules don't mention explicitList"

    def test_all_agents_have_a2ui_json_tags_in_rules(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            suffix = suffix_fn()
            assert "<a2ui-json>" in suffix, f"{name}: rules don't mention <a2ui-json> tags"

    def test_no_hardcoded_retailers_in_a2ui_prompts(self):
        from src.agent.prompts.system_prompts import get_a2ui_prompt_suffix
        from src.mcp_agent.agent import _get_a2ui_suffix as mcp_suffix
        from src.simulator_agent.agent import _get_a2ui_suffix as sim_suffix

        forbidden = ["kroger", "heb", "publix", "safeway", "albertsons"]
        for name, suffix_fn in [("main", get_a2ui_prompt_suffix), ("mcp", mcp_suffix), ("simulator", sim_suffix)]:
            suffix = suffix_fn().lower()
            for word in forbidden:
                assert word not in suffix, f"{name}: forbidden retailer name '{word}' in A2UI prompt"


# ── A2UI Deploy Script Inline Prompt ─────────────────────────────────────────

class TestDeployInlineA2UI:
    """Validate the inline A2UI blocks in deploy_to_agent_engine scripts."""

    def _read(self, path):
        with open(path) as f:
            return f.read()

    def test_main_deploy_inline_a2ui_valid_json(self):
        content = self._read("src/agent/deploy_to_agent_engine.py")
        match = re.search(r'<a2ui-json>([\s\S]*?)</a2ui-json>', content)
        assert match, "No inline A2UI block in main deploy script"
        data = json.loads(match.group(1))
        assert isinstance(data, list)

    def test_simulator_deploy_inline_a2ui_valid_json(self):
        content = self._read("src/simulator_agent/deploy_to_agent_engine.py")
        match = re.search(r'<a2ui-json>([\s\S]*?)</a2ui-json>', content)
        assert match, "No inline A2UI block in simulator deploy script"
        data = json.loads(match.group(1))
        assert isinstance(data, list)

    def test_mcp_deploy_inline_a2ui_valid_json(self):
        content = self._read("src/mcp_agent/deploy_to_agent_engine.py")
        match = re.search(r'<a2ui-json>([\s\S]*?)</a2ui-json>', content)
        assert match, "No inline A2UI block in MCP deploy script"
        data = json.loads(match.group(1))
        assert isinstance(data, list)
