"""WebSocket voice server for ADK bidi streaming.

Implements the ADK streaming pattern for bidirectional audio:
- LiveRequestQueue for message buffering
- Runner.run_live() for streaming event processing
- SpeechConfig with Puck voice
- Base64-encoded PCM audio in JSON text frames
- Concurrent upstream/downstream tasks

Based on:
  https://github.com/bhancockio/adk-voice-agent/blob/main/app/main.py

Usage:
    # Standalone (for development):
    python -m src.frontend.voice_server

    # Integrated (launched by server.py on port 8081):
    from src.frontend.voice_server import start_voice_server
    start_voice_server(port=8081)
"""

import asyncio
import base64
import json
import logging
import os
import threading
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


CONFIG = _load_config()
VOICE_CONFIG = CONFIG.get("voice", {})
VOICE_ENABLED = VOICE_CONFIG.get("enabled", True)
VOICE_PORT = int(os.environ.get("VOICE_WS_PORT", VOICE_CONFIG.get("ws_port", 8081)))
VOICE_NAME = VOICE_CONFIG.get("voice_name", "Puck")

# Ensure Vertex AI env vars are set for the ADK genai Client.
# When running via `adk web`, the CLI sets these automatically.
# When running via server.py, we need to set them from config.
# The Live API model requires a specific region (e.g. us-east4).
_project_id = CONFIG.get("project", {}).get("id", "")
_live_location = VOICE_CONFIG.get("live_location", "us-east4")
if _project_id and not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", _project_id)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", _live_location)

# ---------------------------------------------------------------------------
# ADK streaming setup
# ---------------------------------------------------------------------------
APP_NAME = "grocery-voice"

# Module-level runners and session services (shared across sessions)
# Keyed by agent type: "default" (grocery assistant), "operations" (voice ops)
_runners = {}
_session_services = {}


def _create_runner(agent_type="default"):
    """Create ADK Runner for the specified agent type.

    Args:
        agent_type: "default" for the grocery assistant, "operations" for
                    the voice operations/supply chain agent.

    Returns (runner, session_service) tuple, or (None, None) if ADK
    is not available.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        if agent_type == "operations":
            from src.voice_bidi_agent.agent import create_agent
        else:
            from src.agent.agent import create_agent

        session_service = InMemorySessionService()
        agent = create_agent()
        runner = Runner(
            app_name=f"{APP_NAME}-{agent_type}",
            agent=agent,
            session_service=session_service,
        )
        logger.info(
            "ADK runner created for voice (type=%s, agent=%s, model=%s)",
            agent_type, agent.name, agent.model,
        )
        return runner, session_service
    except ImportError as e:
        logger.error("Voice runner import failed (type=%s): %s", agent_type, e)
        return None, None
    except Exception as e:
        logger.error("Voice runner creation failed (type=%s): %s", agent_type, e, exc_info=True)
        return None, None


def _get_runner(agent_type="default"):
    """Get or create the runner for the given agent type."""
    if agent_type not in _runners or _runners[agent_type] is None:
        runner, session_service = _create_runner(agent_type)
        _runners[agent_type] = runner
        _session_services[agent_type] = session_service
    return _runners[agent_type], _session_services.get(agent_type)


def _create_run_config(is_audio=True):
    """Create RunConfig for streaming with SpeechConfig.

    Uses Puck voice and output audio transcription so the client
    receives both audio and text transcriptions.
    """
    try:
        from google.adk.agents.run_config import RunConfig, StreamingMode
        from google.genai import types

        modality = "AUDIO" if is_audio else "TEXT"

        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=VOICE_NAME,
                )
            )
        )

        config = {
            "streaming_mode": StreamingMode.BIDI,
            "response_modalities": [modality],
            "speech_config": speech_config,
        }

        # Add transcription when audio is enabled
        if is_audio:
            config["output_audio_transcription"] = types.AudioTranscriptionConfig()
            config["input_audio_transcription"] = types.AudioTranscriptionConfig()

        return RunConfig(**config)
    except ImportError:
        logger.warning("ADK streaming imports not available")
        return None


async def _start_agent_session(session_id, is_audio=True, agent_type="default"):
    """Start an agent session and return (live_events, live_request_queue).

    Follows the pattern from the reference ADK voice agent implementation.

    Args:
        session_id: Unique session identifier.
        is_audio: Whether to use audio modality.
        agent_type: "default" or "operations" to select agent.
    """
    runner, session_service = _get_runner(agent_type)
    if runner is None:
        return None, None

    from google.adk.agents.live_request_queue import LiveRequestQueue

    app_name = f"{APP_NAME}-{agent_type}"

    # Create session (async in ADK)
    session = await session_service.create_session(
        app_name=app_name,
        user_id=session_id,
        session_id=session_id,
    )

    run_config = _create_run_config(is_audio=is_audio)
    if run_config is None:
        return None, None

    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    return live_events, live_request_queue


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------
async def handle_voice_session(websocket):
    """Handle a single bidi streaming voice session.

    Protocol (all JSON text frames):
      Client -> Server:
        { "mime_type": "text/plain", "data": "...", "role": "user" }
        { "mime_type": "audio/pcm", "data": "<base64>" }

      Server -> Client:
        { "mime_type": "text/plain", "data": "...", "role": "model" }
        { "mime_type": "audio/pcm", "data": "<base64>", "role": "model" }
        { "turn_complete": true }
        { "interrupted": true }
    """
    from google.genai import types

    # Parse session_id, is_audio, and agent from the WebSocket path
    # Expected path: /ws/{session_id}?is_audio=true&agent=operations
    full_path = websocket.request.path
    path_only = full_path.split("?", 1)[0]
    query_string = full_path.split("?", 1)[1] if "?" in full_path else ""

    path_parts = path_only.strip("/").split("/")
    session_id = path_parts[1] if len(path_parts) >= 2 else f"voice-{id(websocket)}"

    # Parse query parameters
    params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)
    is_audio = params.get("is_audio", "true") == "true"
    agent_type = params.get("agent", "default")

    logger.info(
        "Voice session started: session=%s audio=%s voice=%s agent=%s",
        session_id, is_audio, VOICE_NAME, agent_type,
    )

    live_events, live_request_queue = await _start_agent_session(
        session_id, is_audio=is_audio, agent_type=agent_type,
    )
    if live_events is None:
        logger.error("Voice session failed: ADK runner not available (session=%s)", session_id)
        await websocket.send(json.dumps({
            "type": "error",
            "message": "ADK runner not available for voice streaming. Check server logs.",
        }))
        await websocket.close()
        return
    logger.info("Voice session agent connected: session=%s", session_id)

    async def agent_to_client():
        """Receive events from run_live(), forward to WebSocket as JSON."""
        try:
            async for event in live_events:
                if event is None:
                    continue

                # Turn complete or interrupted
                if event.turn_complete or event.interrupted:
                    message = {
                        "turn_complete": event.turn_complete,
                        "interrupted": event.interrupted,
                    }
                    await websocket.send(json.dumps(message))
                    continue

                # Read content parts
                part = (
                    event.content
                    and event.content.parts
                    and event.content.parts[0]
                )
                if not part:
                    continue

                if not isinstance(part, types.Part):
                    continue

                # Text: forward with the event's role
                role = event.content.role if event.content.role else "model"

                if part.text and role == "user":
                    # User input transcription — always forward
                    message = {
                        "mime_type": "text/plain",
                        "data": part.text,
                        "role": "user",
                        "partial": bool(event.partial),
                    }
                    await websocket.send(json.dumps(message))
                elif part.text:
                    # Model text: partial streaming chunks or audio transcription
                    message = {
                        "mime_type": "text/plain",
                        "data": part.text,
                        "role": "model",
                        "partial": bool(event.partial),
                    }
                    await websocket.send(json.dumps(message))

                # Audio: send base64-encoded PCM
                is_audio_part = (
                    part.inline_data
                    and part.inline_data.mime_type
                    and part.inline_data.mime_type.startswith("audio/pcm")
                )
                if is_audio_part and part.inline_data.data:
                    message = {
                        "mime_type": "audio/pcm",
                        "data": base64.b64encode(part.inline_data.data).decode("ascii"),
                        "role": "model",
                    }
                    await websocket.send(json.dumps(message))

        except Exception as e:
            logger.debug("Downstream ended: %s", e)

    async def client_to_agent():
        """Receive messages from WebSocket, forward to LiveRequestQueue."""
        try:
            async for raw_message in websocket:
                message = json.loads(raw_message)
                mime_type = message.get("mime_type", "text/plain")
                data = message.get("data", "")
                role = message.get("role", "user")

                if mime_type == "text/plain":
                    content = types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=data)],
                    )
                    live_request_queue.send_content(content=content)

                elif mime_type == "audio/pcm":
                    decoded_data = base64.b64decode(data)
                    live_request_queue.send_realtime(
                        types.Blob(data=decoded_data, mime_type=mime_type)
                    )

        except Exception as e:
            logger.debug("Upstream ended: %s", e)

    # Run both tasks concurrently
    try:
        agent_task = asyncio.create_task(agent_to_client())
        client_task = asyncio.create_task(client_to_agent())
        await asyncio.gather(agent_task, client_task, return_exceptions=True)
    finally:
        live_request_queue.close()
        logger.info("Voice session ended: session=%s", session_id)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------
async def _run_server(host="0.0.0.0", port=8081):
    """Run the WebSocket voice server."""
    import websockets

    logger.info("Voice WebSocket server starting on ws://%s:%d", host, port)

    async with websockets.serve(
        handle_voice_session,
        host,
        port,
        max_size=10 * 1024 * 1024,  # 10MB
        ping_interval=20,
        ping_timeout=20,
        origins=None,
    ):
        logger.info("Voice WebSocket server ready on ws://%s:%d", host, port)
        await asyncio.Future()  # Run forever


def start_voice_server(port=None, host="0.0.0.0"):
    """Start the voice WebSocket server in a background thread.

    Called by server.py to run alongside the HTTP server.
    Returns the thread object.
    """
    if not VOICE_ENABLED:
        logger.info("Voice server disabled in config")
        return None

    actual_port = port or VOICE_PORT

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_server(host, actual_port))
        except Exception as e:
            logger.error("Voice server failed: %s", e)

    thread = threading.Thread(
        target=_run,
        name="voice-ws-server",
        daemon=True,
    )
    thread.start()
    logger.info("Voice WebSocket server thread started on port %d", actual_port)
    return thread


# ---------------------------------------------------------------------------
# Standalone entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    asyncio.run(_run_server(port=VOICE_PORT))
