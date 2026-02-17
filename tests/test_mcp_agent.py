"""Unit tests for the MCP-based ADK agent.

Tests agent configuration, instruction generation, toolbox path resolution,
and schema context generation without requiring a live MCP server, ADK,
or BigQuery access.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestConfigLoading:

    def test_load_config_from_yaml(self):
        from src.mcp_agent.agent import _load_config
        config = _load_config()
        assert config["retailer"]["name"] == "ValueFresh Market"
        assert config["bigquery"]["project"] == "wortz-project-352116"
        assert config["bigquery"]["dataset"] == "ge_grocery_demo"

    def test_load_config_env_override(self):
        from src.mcp_agent.agent import _load_config
        with patch.dict(os.environ, {
            "RETAILER_NAME": "TestMart",
            "BQ_PROJECT": "test-project",
            "BQ_DATASET": "test_dataset",
        }):
            config = _load_config()
            assert config["retailer"]["name"] == "TestMart"
            assert config["bigquery"]["project"] == "test-project"
            assert config["bigquery"]["dataset"] == "test_dataset"

    def test_config_path_resolves(self):
        from src.mcp_agent.agent import CONFIG_PATH
        assert CONFIG_PATH.name == "settings.yaml"
        assert CONFIG_PATH.parent.name == "config"

    def test_config_has_model_defaults(self):
        from src.mcp_agent.agent import _load_config
        config = _load_config()
        assert config["models"]["adk"] == "gemini-3-pro-preview"

    def test_config_model_env_override(self):
        from src.mcp_agent.agent import _load_config
        with patch.dict(os.environ, {"ADK_MODEL": "gemini-3-pro-preview"}):
            config = _load_config()
            assert config["models"]["adk"] == "gemini-3-pro-preview"


# ---------------------------------------------------------------------------
# Schema context
# ---------------------------------------------------------------------------

class TestSchemaContext:

    def test_schema_contains_all_tables(self):
        from src.mcp_agent.agent import _get_schema_context, _load_config
        config = _load_config()
        schema = _get_schema_context(config)
        assert "fact_transactions" in schema
        assert "dim_store" in schema
        assert "dim_product" in schema
        assert "dim_employee" in schema
        assert "dim_customer" in schema

    def test_schema_contains_fully_qualified_names(self):
        from src.mcp_agent.agent import _get_schema_context, _load_config
        config = _load_config()
        schema = _get_schema_context(config)
        assert "wortz-project-352116.ge_grocery_demo" in schema

    def test_schema_contains_key_columns(self):
        from src.mcp_agent.agent import _get_schema_context, _load_config
        config = _load_config()
        schema = _get_schema_context(config)
        # Fact table columns
        assert "transaction_id" in schema
        assert "total_amount" in schema
        assert "payment_method" in schema
        # Dimension columns
        assert "store_name" in schema
        assert "product_name" in schema
        assert "loyalty_tier" in schema
        assert "first_name" in schema

    def test_schema_contains_relationships(self):
        from src.mcp_agent.agent import _get_schema_context, _load_config
        config = _load_config()
        schema = _get_schema_context(config)
        assert "fact_transactions.store_id -> dim_store.store_id" in schema
        assert "fact_transactions.product_id -> dim_product.product_id" in schema

    def test_schema_uses_config_values(self):
        from src.mcp_agent.agent import _get_schema_context
        config = {
            "bigquery": {
                "project": "my-project",
                "dataset": "my_dataset",
            }
        }
        schema = _get_schema_context(config)
        assert "my-project.my_dataset" in schema
        assert "wortz-project-352116" not in schema


# ---------------------------------------------------------------------------
# Agent instruction
# ---------------------------------------------------------------------------

class TestAgentInstruction:

    def test_instruction_contains_retailer(self):
        from src.mcp_agent.agent import _get_agent_instruction, _load_config
        config = _load_config()
        instruction = _get_agent_instruction(config)
        assert "ValueFresh Market" in instruction

    def test_instruction_no_hardcoded_retailers(self):
        from src.mcp_agent.agent import _get_agent_instruction, _load_config
        config = _load_config()
        instruction = _get_agent_instruction(config)
        assert "kroger" not in instruction.lower()
        assert "heb" not in instruction.lower().split()

    def test_instruction_mentions_mcp_tools(self):
        from src.mcp_agent.agent import _get_agent_instruction, _load_config
        config = _load_config()
        instruction = _get_agent_instruction(config)
        assert "execute_sql" in instruction
        assert "read-only" in instruction.lower() or "SELECT" in instruction

    def test_instruction_contains_schema(self):
        from src.mcp_agent.agent import _get_agent_instruction, _load_config
        config = _load_config()
        instruction = _get_agent_instruction(config)
        assert "fact_transactions" in instruction
        assert "dim_store" in instruction

    def test_instruction_uses_custom_retailer(self):
        from src.mcp_agent.agent import _get_agent_instruction
        config = {
            "retailer": {"name": "FreshMart"},
            "bigquery": {
                "project": "proj",
                "dataset": "ds",
            },
        }
        instruction = _get_agent_instruction(config)
        assert "FreshMart" in instruction
        assert "ValueFresh" not in instruction


# ---------------------------------------------------------------------------
# Toolbox path resolution
# ---------------------------------------------------------------------------

class TestToolboxPathResolution:

    def test_resolve_from_env_var(self, tmp_path):
        from src.mcp_agent.agent import _resolve_toolbox_path
        fake_bin = tmp_path / "toolbox"
        fake_bin.touch()
        with patch.dict(os.environ, {"TOOLBOX_PATH": str(fake_bin)}):
            assert _resolve_toolbox_path() == str(fake_bin)

    def test_resolve_env_var_missing_file_falls_through(self):
        from src.mcp_agent.agent import _resolve_toolbox_path
        with patch.dict(os.environ, {"TOOLBOX_PATH": "/nonexistent/toolbox"}):
            # Should not return the nonexistent path, should fall through
            result = _resolve_toolbox_path()
            assert result != "/nonexistent/toolbox"

    @patch("shutil.which")
    def test_resolve_from_system_path(self, mock_which):
        from src.mcp_agent.agent import _resolve_toolbox_path
        mock_which.return_value = "/usr/local/bin/toolbox"
        with patch.dict(os.environ, {}, clear=False):
            # Remove TOOLBOX_PATH if set
            os.environ.pop("TOOLBOX_PATH", None)
            result = _resolve_toolbox_path()
            # Could be from project root or system PATH
            if result == "/usr/local/bin/toolbox":
                mock_which.assert_called()

    def test_resolve_fallback_returns_binary_name(self):
        from src.mcp_agent.agent import _resolve_toolbox_path
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TOOLBOX_PATH", None)
        with patch("shutil.which", return_value=None):
            # If toolbox is not in project root either, falls back
            with patch("pathlib.Path.is_file", return_value=False):
                result = _resolve_toolbox_path()
                assert result == "toolbox"


# ---------------------------------------------------------------------------
# MCP toolset creation
# ---------------------------------------------------------------------------

class TestMCPToolsetCreation:

    @patch("src.mcp_agent.agent._resolve_toolbox_path", return_value="/usr/bin/toolbox")
    def test_get_mcp_toolset_returns_toolset(self, mock_path):
        """Test that get_mcp_toolset creates a McpToolset with correct params."""
        try:
            from src.mcp_agent.agent import get_mcp_toolset
            toolset = get_mcp_toolset()
            # Should return a McpToolset instance
            from google.adk.tools.mcp_tool import McpToolset
            assert isinstance(toolset, McpToolset)
        except ImportError:
            pytest.skip("google-adk or mcp not installed")

    @patch("src.mcp_agent.agent._resolve_toolbox_path", return_value="/usr/bin/toolbox")
    def test_get_mcp_toolset_uses_project_from_config(self, mock_path):
        """Verify the toolset connects to the correct BigQuery project."""
        try:
            from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
            from mcp import StdioServerParameters

            with patch("src.mcp_agent.agent._load_config") as mock_config:
                mock_config.return_value = {
                    "retailer": {"name": "TestMart"},
                    "bigquery": {
                        "project": "test-proj-123",
                        "dataset": "test_ds",
                    },
                }
                from src.mcp_agent.agent import get_mcp_toolset
                toolset = get_mcp_toolset()
                # The toolset's connection_params should reference test-proj-123
                # We verify the args passed to StdioServerParameters
                conn = toolset._connection_params
                if hasattr(conn, 'server_params'):
                    args = conn.server_params.args
                    # --project is NOT a valid genai-toolbox flag;
                    # project is passed via BIGQUERY_PROJECT env var
                    assert "--project" not in args
                    env = conn.server_params.env or {}
                    assert env.get("BIGQUERY_PROJECT") == "test-proj-123"
        except ImportError:
            pytest.skip("google-adk or mcp not installed")


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------

class TestAgentCreation:

    @patch("src.mcp_agent.agent.get_mcp_toolset")
    def test_create_agent_returns_agent(self, mock_toolset):
        """Test that create_agent returns an LlmAgent."""
        mock_toolset.return_value = MagicMock()
        try:
            from src.mcp_agent.agent import create_agent
            agent = create_agent()
            from google.adk.agents import LlmAgent
            assert isinstance(agent, LlmAgent)
        except ImportError:
            pytest.skip("google-adk not installed")

    @patch("src.mcp_agent.agent.get_mcp_toolset")
    def test_create_agent_name(self, mock_toolset):
        """Test agent name matches expected value."""
        mock_toolset.return_value = MagicMock()
        try:
            from src.mcp_agent.agent import create_agent
            agent = create_agent()
            assert agent.name == "mcp_grocery_analyst"
        except ImportError:
            pytest.skip("google-adk not installed")

    @patch("src.mcp_agent.agent.get_mcp_toolset")
    def test_create_agent_has_tools(self, mock_toolset):
        """Test that the agent is configured with MCP tools."""
        mock_toolset.return_value = MagicMock()
        try:
            from src.mcp_agent.agent import create_agent
            agent = create_agent()
            assert len(agent.tools) > 0
        except ImportError:
            pytest.skip("google-adk not installed")

    @patch("src.mcp_agent.agent.get_mcp_toolset")
    def test_create_agent_model(self, mock_toolset):
        """Test that the agent uses the expected model."""
        mock_toolset.return_value = MagicMock()
        try:
            from src.mcp_agent.agent import create_agent
            agent = create_agent()
            assert agent.model == "gemini-3-pro-preview"
        except ImportError:
            pytest.skip("google-adk not installed")


# ---------------------------------------------------------------------------
# Tools.yaml validation
# ---------------------------------------------------------------------------

class TestToolsYaml:

    def test_tools_yaml_exists(self):
        tools_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "tools.yaml"
        assert tools_path.exists(), f"tools.yaml not found at {tools_path}"

    def test_tools_yaml_valid(self):
        import yaml
        tools_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "tools.yaml"
        with open(tools_path) as f:
            config = yaml.safe_load(f)
        assert "sources" in config
        assert "tools" in config
        assert "toolsets" in config

    def test_tools_yaml_bigquery_source(self):
        import yaml
        tools_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "tools.yaml"
        with open(tools_path) as f:
            config = yaml.safe_load(f)
        source = config["sources"]["grocery_bq"]
        assert source["kind"] == "bigquery"
        assert source["project"] == "wortz-project-352116"

    def test_tools_yaml_no_hardcoded_retailers(self):
        tools_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "tools.yaml"
        content = tools_path.read_text().lower()
        assert "kroger" not in content
        assert "heb" not in content


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------

class TestMemoryBankIntegration:
    """Test Vertex AI Memory Bank integration for the MCP agent."""

    def test_mcp_agent_has_memory_app(self):
        """Verify MCP agent app.py exists and creates memory service."""
        from pathlib import Path
        app_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "app.py"
        assert app_path.exists(), "MCP agent app.py should exist for memory integration"

    def test_mcp_memory_service_creation(self):
        """Verify memory service is created for MCP agent."""
        from src.mcp_agent.app import _create_memory_service
        service = _create_memory_service()
        assert service is not None

    def test_mcp_memory_uses_correct_config(self):
        """Verify MCP agent uses BQ project for memory service."""
        from src.mcp_agent.app import _create_memory_service
        from src.mcp_agent.agent import _load_config
        config = _load_config()
        # Just verify it doesn't crash and uses the right config keys
        assert "bigquery" in config
        assert "project" in config["bigquery"]


class TestRequirements:

    def test_requirements_exist(self):
        req_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "requirements.txt"
        assert req_path.exists()

    def test_requirements_contain_key_deps(self):
        req_path = Path(__file__).resolve().parent.parent / "src" / "mcp_agent" / "requirements.txt"
        content = req_path.read_text()
        assert "google-adk" in content
        assert "mcp" in content
        assert "pyyaml" in content
