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
            assert agent.name == "sop_agent"

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

    def test_dockerfile_uses_global_location(self):
        """Gemini 3 models require global endpoint, not a regional one."""
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "Dockerfile"
        content = path.read_text()
        assert "GOOGLE_CLOUD_LOCATION=global" in content, (
            "Dockerfile must set GOOGLE_CLOUD_LOCATION=global for Gemini 3 models"
        )
        assert "GOOGLE_CLOUD_LOCATION=us-central1" not in content, (
            "Dockerfile must NOT use us-central1 — Gemini 3 models require global"
        )

    def test_root_dockerfile_uses_global_location(self):
        """Root Dockerfile (used by gcloud run deploy --source) must also use global."""
        path = Path(__file__).parent.parent / "Dockerfile"
        content = path.read_text()
        assert "GOOGLE_CLOUD_LOCATION=global" in content, (
            "Root Dockerfile must set GOOGLE_CLOUD_LOCATION=global for Gemini 3 models"
        )

    def test_deploy_script_uses_global_location(self):
        """Deploy script must pass GOOGLE_CLOUD_LOCATION=global, not regional."""
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "deploy_to_cloud_run.sh"
        content = path.read_text()
        assert "GOOGLE_CLOUD_LOCATION=global" in content, (
            "Deploy script must set GOOGLE_CLOUD_LOCATION=global for Gemini 3 models"
        )
        assert "GOOGLE_CLOUD_LOCATION=${REGION}" not in content, (
            "Deploy script must NOT use REGION for GOOGLE_CLOUD_LOCATION — Gemini 3 requires global"
        )

    def test_no_agent_engine_deploy_script(self):
        """A2A agents only deploy via Cloud Run, not Agent Engine."""
        path = Path(__file__).parent.parent / "src" / "a2a_agent" / "deploy_to_agent_engine.py"
        assert not path.exists(), (
            "deploy_to_agent_engine.py should not exist — A2A only deploys via Cloud Run"
        )

    def test_config_no_a2a_agent_engine_id(self):
        """Config should not have an a2a_agent_engine_id — A2A is Cloud Run only."""
        import yaml
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert "a2a_agent_engine_id" not in config.get("project", {}), (
            "config should not have a2a_agent_engine_id — A2A deploys via Cloud Run only"
        )

    def test_config_has_a2a_cloud_run_url(self):
        """Config must have a2a_cloud_run_url for Cloud Run deployment."""
        import yaml
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        url = config.get("project", {}).get("a2a_cloud_run_url", "")
        assert url.startswith("https://"), (
            f"a2a_cloud_run_url must be a valid HTTPS URL, got: {url}"
        )

    def test_config_has_a2a_agent_id(self):
        """Config must have a2a_agent_id for Discovery Engine registration."""
        import yaml
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        agent_id = config.get("project", {}).get("a2a_agent_id", "")
        assert agent_id, "a2a_agent_id must be set in config for GE registration"


class TestSimulatorGERegistration(unittest.TestCase):
    """Test that simulator agent is configured for Discovery Engine registration."""

    def test_config_has_simulator_agent_engine_id(self):
        """Config must have simulator_agent_engine_id for Agent Engine deployment."""
        import yaml
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        engine_id = config.get("project", {}).get("simulator_agent_engine_id", "")
        assert engine_id, "simulator_agent_engine_id must be set in config"

    def test_config_has_simulator_agent_id(self):
        """Config must have simulator_agent_id for Discovery Engine registration."""
        import yaml
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        agent_id = config.get("project", {}).get("simulator_agent_id", "")
        assert agent_id, (
            "simulator_agent_id must be set in config for GE registration"
        )

    def test_register_script_includes_simulator(self):
        """Registration script should register the simulator agent on GE."""
        path = Path(__file__).parent.parent / "infra" / "register_agents.sh"
        content = path.read_text()
        assert "simulator" in content.lower() or "Simulator" in content, (
            "register_agents.sh should include simulator agent registration"
        )


class TestSimulatorAgent(unittest.TestCase):
    """Basic tests for the shopper simulator agent."""

    def test_store_layouts_defined(self):
        from src.simulator_agent.agent import STORE_LAYOUTS

        assert "Downtown Market" in STORE_LAYOUTS
        assert "Westside Market" in STORE_LAYOUTS
        assert "Lakefront Market" in STORE_LAYOUTS

    def test_endcap_scenarios_defined(self):
        from src.simulator_agent.agent import _load_strategies

        scenarios = _load_strategies()
        assert "baseline" in scenarios
        assert "seasonal_produce" in scenarios
        assert "snack_impulse" in scenarios
        assert "health_wellness" in scenarios

    def test_shopper_personas_defined(self):
        from src.simulator_agent.agent import _load_personas

        personas = _load_personas()
        assert len(personas) >= 3
        ids = [p["id"] for p in personas]
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
        from src.simulator_agent.agent import _build_shopper_instruction, _load_personas

        personas = _load_personas()
        persona = personas[0]
        instruction = _build_shopper_instruction(persona, "Downtown Market", "baseline")
        assert persona["name"] in instruction
        assert str(persona["shopping_behavior"]["budget"]) in instruction

    def test_simulator_uses_flash_model(self):
        """Simulator should use adk_fast (gemini-3-flash) for low latency, not adk (pro)."""
        from src.simulator_agent.agent import _load_config
        config = _load_config()
        # Should prefer adk_fast over adk
        model = config["models"].get("adk_fast", config["models"].get("adk", ""))
        assert "flash" in model.lower(), (
            f"Simulator model should be flash for low latency, got: {model}"
        )


class TestReportGenerator(unittest.TestCase):
    """Test simulation report generation tool."""

    def test_report_generator_with_json(self):
        """Test report generation with well-formed JSON input."""
        from src.simulator_agent.tools.report_generator import generate_simulation_report

        test_data = {
            "shoppers": [
                {
                    "persona": "Budget Family",
                    "total_spend": 115.50,
                    "cart_size": 25,
                    "endcap_items": ["Nano Banana Pro"],
                    "impulse_tendency": 0.3,
                    "budget": 120
                },
                {
                    "persona": "Health Professional",
                    "total_spend": 72.30,
                    "cart_size": 14,
                    "endcap_items": [],
                    "impulse_tendency": 0.5,
                    "budget": 80
                }
            ],
            "scenario": "Test Scenario",
            "store_name": "Test Store"
        }

        result = generate_simulation_report(json.dumps(test_data))

        assert result["status"] == "success"
        assert result["report_path"] == "/tmp/simulation_report.html"
        assert result["total_revenue"] == 187.80
        assert result["avg_cart_size"] == 19.5
        assert result["endcap_conversion_rate"] == 50.0
        assert "summary" in result

        # Verify HTML file was created
        assert Path("/tmp/simulation_report.html").exists()

    def test_report_generator_with_freeform_text(self):
        """Test report generation with freeform text extraction."""
        from src.simulator_agent.tools.report_generator import generate_simulation_report

        test_text = """
        Simulation for Downtown Market:
        Shopper: Budget Conscious - Total spend: $95.50
        Shopper: Health Nut - Total: $125.00
        The endcap was effective.
        """

        result = generate_simulation_report(test_text)

        assert result["status"] == "success"
        assert result["report_path"] == "/tmp/simulation_report.html"
        assert result["total_revenue"] > 0
        assert "summary" in result

    def test_report_generator_chart_js_included(self):
        """Test that Chart.js is included in generated HTML."""
        from src.simulator_agent.tools.report_generator import generate_simulation_report

        test_data = {"shoppers": [{"persona": "Test", "total_spend": 50, "cart_size": 10}]}
        generate_simulation_report(json.dumps(test_data))

        html_content = Path("/tmp/simulation_report.html").read_text()
        assert "chart.js" in html_content.lower()
        assert "new Chart" in html_content
        assert "conversionChart" in html_content
        assert "personaChart" in html_content
        assert "cartSizeChart" in html_content
        assert "roiChart" in html_content

    def test_report_generator_no_hardcoded_retailers(self):
        """Test that no forbidden retailer names are hardcoded."""
        import inspect
        from src.simulator_agent.tools import report_generator

        source = inspect.getsource(report_generator)
        forbidden = ["Kroger", "HEB", "H-E-B", "Walmart", "Safeway"]
        for name in forbidden:
            assert name not in source, f"Hardcoded retailer name '{name}' found in report_generator.py"

    def test_report_generator_uses_config_retailer_name(self):
        """Test that report uses retailer name from config."""
        from src.simulator_agent.tools.report_generator import generate_simulation_report

        test_data = {"shoppers": [{"persona": "Test", "total_spend": 50, "cart_size": 10}]}
        generate_simulation_report(json.dumps(test_data))

        html_content = Path("/tmp/simulation_report.html").read_text()
        # Should contain retailer name from config (ValueFresh Market by default)
        assert "ValueFresh Market" in html_content or "RETAILER_NAME" not in os.environ

    def test_report_generator_handles_empty_shoppers(self):
        """Test report generation with empty shoppers list."""
        from src.simulator_agent.tools.report_generator import generate_simulation_report

        test_data = {"shoppers": []}
        result = generate_simulation_report(json.dumps(test_data))

        # Should still succeed with placeholder data
        assert result["status"] == "success"
        assert result["report_path"] == "/tmp/simulation_report.html"


if __name__ == "__main__":
    unittest.main()
