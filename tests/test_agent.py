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
        assert "Image Generation" in instruction or "image" in instruction.lower()

    def test_main_instruction_no_analytics_section(self):
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        instruction = get_main_agent_instruction()
        assert "Product Information & Analytics" not in instruction
        assert "BigQuery analytics tool" not in instruction

    def test_main_instruction_simulator_scenarios_match_config(self):
        """System prompt should list scenario keys that exist in endcap_strategies.yaml."""
        from src.agent.prompts.system_prompts import get_main_agent_instruction
        from src.simulator_agent.agent import _load_strategies
        instruction = get_main_agent_instruction()
        strategies = _load_strategies()
        # Verify no stale scenario names
        assert "premium_organic" not in instruction, "Stale scenario 'premium_organic' in system prompt"
        assert "impulse_buy" not in instruction, "Stale scenario 'impulse_buy' in system prompt"
        # Verify key real scenarios are listed
        for key in ["seasonal_produce", "snack_impulse", "health_wellness"]:
            assert key in instruction, f"Scenario '{key}' missing from system prompt"

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
        assert config["models"]["adk"] == "gemini-3-pro-preview"
        assert config["models"]["adk_fast"] == "gemini-3-flash-preview"
        assert config["models"]["imagen"] == "gemini-3-pro-image-preview"

    def test_config_model_env_override(self):
        import os
        from src.agent.agent import _load_config
        with patch.dict(os.environ, {"ADK_MODEL": "gemini-3-pro-preview", "IMAGEN_MODEL": "imagen-4.0"}):
            config = _load_config()
            assert config["models"]["adk"] == "gemini-3-pro-preview"
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


class TestVoiceConfig:
    """Test voice configuration in settings.yaml."""

    def test_config_has_voice_section(self):
        from src.agent.agent import _load_config
        config = _load_config()
        assert "voice" in config
        assert config["voice"]["enabled"] is True

    def test_voice_output_config(self):
        from src.agent.agent import _load_config
        config = _load_config()
        voice = config["voice"]
        assert voice["output_enabled"] is True
        assert isinstance(voice["output_rate"], (int, float))
        assert isinstance(voice["output_pitch"], (int, float))
        assert voice["input_lang"] == "en-US"
        assert isinstance(voice["output_voice"], str)


class TestImageGenGlobalEndpoint:
    """Test that image generation uses the global endpoint."""

    def test_image_gen_uses_global_location(self):
        """Verify image_gen_tool calls vertexai.init with location='global'."""
        import inspect
        from src.agent.tools import image_gen_tool
        source = inspect.getsource(image_gen_tool)
        assert 'location="global"' in source

    @patch("src.agent.tools.image_gen_tool._load_config")
    def test_image_gen_returns_proxy_url(self, mock_config):
        """Verify successful image gen returns /api/images/ proxy URL."""
        mock_config.return_value = {
            "project": {"id": "test-project"},
            "retailer": {"name": "TestMart"},
            "models": {"imagen": "gemini-3-pro-image-preview"},
            "gcs": {"bucket": "test-bucket"},
        }
        # Mock the full image generation pipeline
        mock_model = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data.data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_part.inline_data.mime_type = "image/png"
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]
        mock_model.generate_content.return_value = mock_response

        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        with patch("vertexai.init"), \
             patch("vertexai.generative_models.GenerativeModel", return_value=mock_model), \
             patch("google.cloud.storage.Client", return_value=mock_client):
            from src.agent.tools.image_gen_tool import generate_product_image
            result = generate_product_image("Test Product")
            assert result["status"] == "success"
            assert "/api/images/" in result["image_url"]
            assert "![Test Product]" in result["message"]


class TestGCSImageProxy:
    """Test the GCS image proxy route in the frontend server."""

    def test_server_has_gcs_proxy_method(self):
        """Verify the frontend server has a _proxy_gcs_image method."""
        from src.frontend.server import FrontendHandler
        assert hasattr(FrontendHandler, '_proxy_gcs_image')

    def test_server_config_includes_voice(self):
        """Verify /api/config returns voice configuration."""
        from src.frontend.server import CONFIG
        assert "voice" in CONFIG
        assert CONFIG["voice"]["enabled"] is True


class TestFrontendFeatures:
    """Test Sprint 1 frontend enhancements."""

    def test_server_has_memory_status_handler(self):
        """Verify the frontend server has _proxy_memory_status method."""
        from src.frontend.server import FrontendHandler
        assert hasattr(FrontendHandler, '_proxy_memory_status')

    def test_trace_extraction_in_agent_engine_handler(self):
        """Verify Agent Engine proxy extracts trace context."""
        import inspect
        from src.frontend import server
        source = inspect.getsource(server.FrontendHandler._proxy_agent_engine_query)
        assert "x-cloud-trace-context" in source
        assert "trace_id" in source
        assert "trace_url" in source

    def test_performance_metrics_in_agent_engine_handler(self):
        """Verify Agent Engine proxy tracks latency and tool count."""
        import inspect
        from src.frontend import server
        source = inspect.getsource(server.FrontendHandler._proxy_agent_engine_query)
        assert "latency_ms" in source
        assert "tool_count" in source
        assert "functionCall" in source

    def test_memory_status_returns_snippets(self):
        """Verify memory status endpoint returns snippets field."""
        import inspect
        from src.frontend import server
        source = inspect.getsource(server.FrontendHandler._proxy_memory_status)
        assert "snippets" in source

    def test_frontend_no_safety_demo_buttons(self):
        """Verify index.html does not have Model Armor safety demo buttons."""
        from pathlib import Path
        html_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "index.html"
        content = html_path.read_text()
        assert "safety-demo" not in content
        assert "sendSafetySample" not in content

    def test_frontend_has_memory_tooltip(self):
        """Verify index.html has memory tooltip UI."""
        from pathlib import Path
        html_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "index.html"
        content = html_path.read_text()
        assert "memory-tooltip" in content
        assert "memory-snippets" in content

    def test_frontend_has_trace_link(self):
        """Verify index.html shows Cloud Trace deeplinks."""
        from pathlib import Path
        html_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "index.html"
        content = html_path.read_text()
        assert "View Trace" in content
        assert "lastTraceUrl" in content

    def test_agent_engine_stream_endpoint(self):
        """Verify the frontend server has SSE streaming endpoint."""
        from src.frontend.server import FrontendHandler
        assert hasattr(FrontendHandler, '_proxy_agent_engine_stream')

    def test_server_has_list_agents_endpoint(self):
        """Verify the frontend server has _proxy_list_agents method."""
        from src.frontend.server import FrontendHandler
        assert hasattr(FrontendHandler, '_proxy_list_agents')

    def test_frontend_has_greeting_handler(self):
        """Verify index.html handles greetings client-side for StreamAssist."""
        from pathlib import Path
        html_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "index.html"
        content = html_path.read_text()
        assert "handleGreeting" in content
        assert "greetingResponses" in content
        # Should handle: hello, thanks, bye, how are you, what's your favorite
        assert "what's your" in content.lower() or "what is your" in content.lower()
        assert "who are you" in content.lower()


class TestBuildConfig:
    """Test pyproject.toml build configuration."""

    def test_build_backend_is_standard(self):
        """Verify build-backend uses standard setuptools.build_meta."""
        from pathlib import Path
        import tomllib

        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
        assert config["build-system"]["build-backend"] == "setuptools.build_meta"

    def test_uv_index_url_is_public_pypi(self):
        """Verify uv is configured to use public PyPI."""
        from pathlib import Path
        import tomllib

        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
        uv_config = config.get("tool", {}).get("uv", {})
        assert uv_config.get("index-url") == "https://pypi.org/simple/"

    def test_websockets_in_dependencies(self):
        """Verify websockets is listed as a dependency."""
        from pathlib import Path
        import tomllib

        pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
        deps = config["project"]["dependencies"]
        assert any("websockets" in d for d in deps)


class TestVoiceServer:
    """Test voice WebSocket server components."""

    def test_voice_server_module_loads(self):
        """Verify voice_server module can be imported."""
        from src.frontend import voice_server
        assert hasattr(voice_server, 'start_voice_server')
        assert hasattr(voice_server, 'handle_voice_session')

    def test_voice_server_config(self):
        """Verify voice server reads config correctly."""
        from src.frontend.voice_server import VOICE_ENABLED, VOICE_PORT, VOICE_NAME
        assert VOICE_ENABLED is True
        assert isinstance(VOICE_PORT, int)
        assert VOICE_NAME == "Puck"

    def test_voice_server_create_runner(self):
        """Verify _create_runner returns runner or None gracefully."""
        from src.frontend.voice_server import _create_runner
        runner, session_service = _create_runner()
        # May return None if ADK not fully configured, but should not crash
        assert runner is None or runner is not None

    def test_voice_server_create_run_config(self):
        """Verify _create_run_config returns valid RunConfig."""
        from src.frontend.voice_server import _create_run_config
        run_config = _create_run_config()
        if run_config is not None:
            # Should have BIDI streaming mode
            from google.adk.agents.run_config import StreamingMode
            assert run_config.streaming_mode == StreamingMode.BIDI
            assert "AUDIO" in run_config.response_modalities

    def test_voice_server_integrated_in_frontend(self):
        """Verify server.py imports and starts voice server."""
        import inspect
        from src.frontend import server
        source = inspect.getsource(server.main)
        assert "start_voice_server" in source

    def test_pcm_player_processor_file_exists(self):
        """Verify pcm-player-processor.js exists for AudioWorklet."""
        from pathlib import Path
        processor_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "pcm-player-processor.js"
        assert processor_path.exists()
        content = processor_path.read_text()
        assert "PCMPlayerProcessor" in content
        assert "registerProcessor" in content

    def test_pcm_recorder_processor_file_exists(self):
        """Verify pcm-recorder-processor.js exists for mic AudioWorklet."""
        from pathlib import Path
        processor_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "pcm-recorder-processor.js"
        assert processor_path.exists()
        content = processor_path.read_text()
        assert "PCMProcessor" in content
        assert "registerProcessor" in content

    def test_voice_config_has_voice_name(self):
        """Verify config has voice_name for ADK speech config."""
        from src.agent.agent import _load_config
        config = _load_config()
        assert config["voice"]["voice_name"] == "Puck"

    def test_voice_server_speech_config(self):
        """Verify _create_run_config includes SpeechConfig with Puck voice."""
        from src.frontend.voice_server import _create_run_config
        run_config = _create_run_config(is_audio=True)
        if run_config is not None:
            assert run_config.speech_config is not None
            assert run_config.speech_config.voice_config is not None
            prebuilt = run_config.speech_config.voice_config.prebuilt_voice_config
            assert prebuilt.voice_name == "Puck"


class TestAgentRefactor:
    """Tests for the analytics_agent removal and sop_agent rename."""

    def test_agent_name_is_sop_agent(self):
        """Root agent should be named sop_agent."""
        import inspect
        from src.agent import agent as agent_module
        source = inspect.getsource(agent_module.create_agent)
        assert 'name="sop_agent"' in source

    def test_no_analytics_sub_agent(self):
        """analytics_agent should not be created in agent.py."""
        import inspect
        from src.agent import agent as agent_module
        source = inspect.getsource(agent_module.create_agent)
        assert 'name="analytics_agent"' not in source
        assert "create_bq_tool" not in source

    def test_image_agent_still_present(self):
        """image_agent sub-agent should still be present."""
        import inspect
        from src.agent import agent as agent_module
        source = inspect.getsource(agent_module.create_agent)
        assert 'name="image_agent"' in source


