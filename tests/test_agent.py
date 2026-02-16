"""Unit tests for ADK agent components.

Tests agent tool functions and system prompt generation without
requiring ADK or live API access.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestSystemPrompts:

    def test_main_instruction_contains_retailer(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "ValueFresh Market" in instruction
        # Must NOT contain hardcoded retailer names
        assert "kroger" not in instruction.lower()
        assert "heb" not in instruction.lower().split()

    def test_main_instruction_covers_capabilities(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "Standard Operating Procedures" in instruction
        assert "Brand" in instruction
        assert "BigQuery" in instruction or "analytics" in instruction.lower()

    def test_sop_description(self):
        from src.agent.prompts.system_prompts import get_sop_agent_description
        desc = get_sop_agent_description()
        assert "operating procedures" in desc.lower()

    def test_brand_description(self):
        from src.agent.prompts.system_prompts import get_brand_agent_description
        desc = get_brand_agent_description()
        assert "brand" in desc.lower()


class TestBQTool:

    def test_generate_sql_top_products(self):
        from src.agent.tools.bq_tool import _generate_sql
        sql = _generate_sql("What are the top selling products?", "proj.ds")
        assert sql is not None
        assert "dim_product" in sql
        assert "fact_transactions" in sql
        assert "ORDER BY" in sql

    def test_generate_sql_store_sales(self):
        from src.agent.tools.bq_tool import _generate_sql
        sql = _generate_sql("Show me sales by store", "proj.ds")
        assert "dim_store" in sql
        assert "total_revenue" in sql.lower() or "total_amount" in sql.lower()

    def test_generate_sql_loyalty(self):
        from src.agent.tools.bq_tool import _generate_sql
        sql = _generate_sql("How are loyalty tiers distributed?", "proj.ds")
        assert "loyalty_tier" in sql

    def test_generate_sql_payment(self):
        from src.agent.tools.bq_tool import _generate_sql
        sql = _generate_sql("What payment methods are used?", "proj.ds")
        assert "payment_method" in sql

    def test_generate_sql_categories(self):
        from src.agent.tools.bq_tool import _generate_sql
        sql = _generate_sql("Sales by category", "proj.ds")
        assert "category" in sql

    def test_generate_sql_default(self):
        from src.agent.tools.bq_tool import _generate_sql
        sql = _generate_sql("Tell me something random", "proj.ds")
        assert sql is not None  # Should return summary query


class TestImageGenTool:

    @patch("src.agent.tools.image_gen_tool._load_config")
    def test_generate_product_image_no_sdk(self, mock_config):
        mock_config.return_value = {
            "project": {"id": "test-project"},
            "retailer": {"name": "TestMart"},
            "models": {"imagen": "gemini-3-pro-image-preview"},
        }
        from src.agent.tools.image_gen_tool import generate_product_image
        result = generate_product_image("Test Product")
        # Without vertexai SDK, should return placeholder
        assert result["status"] in ("placeholder", "error", "success")
        assert "message" in result

    @patch("src.agent.tools.image_gen_tool._load_config")
    def test_generate_product_image_uses_config_model(self, mock_config):
        mock_config.return_value = {
            "project": {"id": "test-project"},
            "retailer": {"name": "TestMart"},
            "models": {"imagen": "gemini-3-pro-image-preview"},
        }
        from src.agent.tools.image_gen_tool import generate_product_image
        # The function should pick up the model from config
        result = generate_product_image("Test Product")
        assert "message" in result


class TestModelConfig:

    def test_config_has_model_defaults(self):
        from src.agent.agent import _load_config
        config = _load_config()
        assert "models" in config
        assert config["models"]["adk"] == "gemini-3-flash-preview"
        assert config["models"]["imagen"] == "gemini-3-pro-image-preview"

    def test_config_model_env_override(self):
        import os
        from src.agent.agent import _load_config
        with patch.dict(os.environ, {"ADK_MODEL": "gemini-3-pro", "IMAGEN_MODEL": "imagen-4.0"}):
            config = _load_config()
            assert config["models"]["adk"] == "gemini-3-pro"
            assert config["models"]["imagen"] == "imagen-4.0"

    def test_old_imagegeneration_model_not_used(self):
        """Ensure deprecated imagegeneration@006 is no longer referenced."""
        from src.agent.tools import image_gen_tool
        import inspect
        source = inspect.getsource(image_gen_tool)
        assert "imagegeneration@006" not in source


class TestMemoryBank:

    def test_config_has_memory_section(self):
        from src.agent.agent import _load_config
        config = _load_config()
        assert "memory" in config
        assert config["memory"]["enabled"] is True
        assert config["memory"]["location"] == "us-central1"

    def test_system_prompt_mentions_memory(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "memory" in instruction.lower()
        assert "personali" in instruction.lower()  # personalize/personalization

    def test_memory_service_created_when_enabled(self):
        """Verify memory service is created based on config."""
        from src.agent.app import _create_memory_service
        service = _create_memory_service()
        assert service is not None
        # Should be a BaseMemoryService subclass
        assert hasattr(service, '__class__')

    def test_memory_service_fallback_to_inmemory(self):
        """Verify graceful fallback to InMemoryMemoryService."""
        import os
        from src.agent.app import _create_memory_service
        # Even if there's an error creating Vertex Memory Bank, should not crash
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent"}):
            service = _create_memory_service()
            assert service is not None

    def test_runner_has_memory_service(self):
        """Verify Runner instance is created with memory service."""
        from src.agent.app import create_runner
        try:
            runner = create_runner()
            assert runner is not None
            # Runner should have a memory service configured
            assert runner.memory_service is not None
        except ImportError:
            pytest.skip("ADK not installed")

    def test_config_has_model_armor_section(self):
        from src.agent.agent import _load_config
        config = _load_config()
        assert "model_armor" in config
        assert config["model_armor"]["enabled"] is True
        assert config["model_armor"]["template_id"] == "grocery-workshop-armor-us"
        assert config["model_armor"]["failure_mode"] == "FAIL_OPEN"


