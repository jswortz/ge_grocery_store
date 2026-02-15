"""Unit tests for the A2A agent.

Tests agent configuration, AgentCard, and server setup without
requiring GCP credentials or live API access.
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestA2AConfig(unittest.TestCase):
    """Test A2A agent configuration loading."""

    def test_load_config_from_yaml(self):
        from src.a2a_agent.agent import _load_config

        config = _load_config()
        assert "retailer" in config
        assert "name" in config["retailer"]
        assert config["retailer"]["name"]  # Not empty

    def test_load_config_env_override(self):
        from src.a2a_agent.agent import _load_config

        with patch.dict(os.environ, {"RETAILER_NAME": "TestRetailer"}):
            config = _load_config()
            assert config["retailer"]["name"] == "TestRetailer"

    def test_config_has_model_defaults(self):
        from src.a2a_agent.agent import _load_config

        config = _load_config()
        assert "models" in config
        assert "adk" in config["models"]
        assert "gemini" in config["models"]["adk"]

    def test_config_no_hardcoded_retailers(self):
        """Ensure no forbidden retailer names are hardcoded."""
        import inspect
        from src.a2a_agent import agent as a2a_module

        source = inspect.getsource(a2a_module)
        forbidden = ["Kroger", "HEB", "H-E-B", "Walmart", "Safeway"]
        for name in forbidden:
            assert name not in source, f"Hardcoded retailer name found: {name}"


class TestAgentCard(unittest.TestCase):
    """Test A2A AgentCard generation."""

    def test_agent_card_has_required_fields(self):
        from src.a2a_agent.agent import get_agent_card

        card = get_agent_card()
        assert "name" in card
        assert "description" in card
        assert "url" in card
        assert "version" in card
        assert "capabilities" in card
        assert "skills" in card

    def test_agent_card_name(self):
        from src.a2a_agent.agent import get_agent_card

        card = get_agent_card()
        assert card["name"] == "grocery-retail-assistant"

    def test_agent_card_has_skills(self):
        from src.a2a_agent.agent import get_agent_card

        card = get_agent_card()
        skill_ids = [s["id"] for s in card["skills"]]
        assert "sop-lookup" in skill_ids
        assert "brand-guidelines" in skill_ids
        assert "sales-analytics" in skill_ids
        assert "image-generation" in skill_ids

    def test_agent_card_skills_have_descriptions(self):
        from src.a2a_agent.agent import get_agent_card

        card = get_agent_card()
        for skill in card["skills"]:
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill
            assert len(skill["description"]) > 10

    def test_agent_card_capabilities(self):
        from src.a2a_agent.agent import get_agent_card

        card = get_agent_card()
        assert card["capabilities"]["streaming"] is True

    def test_agent_card_includes_retailer(self):
        from src.a2a_agent.agent import get_agent_card

        card = get_agent_card()
        # Description should include the retailer name from config
        from src.a2a_agent.agent import _load_config
        config = _load_config()
        assert config["retailer"]["name"] in card["description"]

    def test_agent_card_url_from_env(self):
        from src.a2a_agent.agent import get_agent_card

        with patch.dict(os.environ, {"A2A_AGENT_URL": "https://test.run.app"}):
            card = get_agent_card()
            assert card["url"] == "https://test.run.app"


class TestA2AAgentCreation(unittest.TestCase):
    """Test A2A agent creation (mocked dependencies)."""

    def _mock_tool_modules(self):
        """Create mock modules for tool imports used inside create_agent()."""
        mock_bq_module = MagicMock()
        mock_bq_module.create_bq_tool.return_value = MagicMock()
        mock_img_module = MagicMock()
        mock_img_module.create_image_gen_tool.return_value = MagicMock()
        return {
            "agent.tools.bq_tool": mock_bq_module,
            "agent.tools.image_gen_tool": mock_img_module,
            "google.adk.tools.discovery_engine_search_tool": MagicMock(),
            "google.cloud.discoveryengine_v1beta": MagicMock(),
            "google.adk.tools.preload_memory_tool": MagicMock(),
        }

    def test_create_agent_returns_agent(self):
        with patch.dict(sys.modules, self._mock_tool_modules()):
            from src.a2a_agent.agent import create_agent
            agent = create_agent()
            assert agent is not None
            assert agent.name == "grocery_assistant"

    def test_create_agent_has_sub_agents(self):
        with patch.dict(sys.modules, self._mock_tool_modules()):
            from src.a2a_agent.agent import create_agent
            agent = create_agent()
            sub_agent_names = [a.name for a in agent.sub_agents]
            assert "analytics_agent" in sub_agent_names
            assert "image_agent" in sub_agent_names


class TestA2AFiles(unittest.TestCase):
    """Test that required A2A agent files exist."""

    def test_dockerfile_exists(self):
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "Dockerfile"
        assert path.exists(), "Dockerfile missing"

    def test_requirements_exist(self):
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "requirements.txt"
        assert path.exists(), "requirements.txt missing"

    def test_requirements_contain_key_deps(self):
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "requirements.txt"
        content = path.read_text()
        assert "google-adk" in content
        assert "a2a" in content  # google-adk[a2a]
        assert "uvicorn" in content

    def test_deploy_script_exists(self):
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "deploy_to_cloud_run.sh"
        assert path.exists(), "deploy script missing"

    def test_deploy_script_executable(self):
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "deploy_to_cloud_run.sh"
        assert os.access(path, os.X_OK), "deploy script not executable"

    def test_server_module_exists(self):
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "server.py"
        assert path.exists(), "server.py missing"


class TestSimulatorAgent(unittest.TestCase):
    """Basic tests for the shopper simulator agent."""

    def test_store_layouts_defined(self):
        from src.simulator_agent.agent import STORE_LAYOUTS

        assert "Downtown Market" in STORE_LAYOUTS
        assert "Westside Market" in STORE_LAYOUTS
        assert "Lakefront Market" in STORE_LAYOUTS

    def test_endcap_scenarios_defined(self):
        from src.simulator_agent.agent import ENDCAP_SCENARIOS

        assert "baseline" in ENDCAP_SCENARIOS
        assert "seasonal_produce" in ENDCAP_SCENARIOS
        assert "snack_impulse" in ENDCAP_SCENARIOS
        assert "health_wellness" in ENDCAP_SCENARIOS

    def test_shopper_personas_defined(self):
        from src.simulator_agent.agent import SHOPPER_PERSONAS

        assert len(SHOPPER_PERSONAS) == 5
        ids = [p["id"] for p in SHOPPER_PERSONAS]
        assert "budget_family" in ids
        assert "health_enthusiast" in ids
        assert "quick_stop" in ids

    def test_store_context_generation(self):
        from src.simulator_agent.agent import _build_store_context

        context = _build_store_context("Downtown Market", "seasonal_produce")
        assert "Downtown Market" in context
        assert "Seasonal Produce" in context
        assert "Nano Banana Pro" in context

    def test_shopper_instruction_generation(self):
        from src.simulator_agent.agent import _build_shopper_instruction, SHOPPER_PERSONAS

        persona = SHOPPER_PERSONAS[0]
        instruction = _build_shopper_instruction(persona, "Downtown Market", "baseline")
        assert persona["name"] in instruction
        assert str(persona["budget"]) in instruction
        assert "Budget" in instruction


if __name__ == "__main__":
    unittest.main()
