"""Lightweight proxy server for the grocery retail frontend.

Serves static files and proxies API calls to Discovery Engine (StreamAssist)
and Agent Engine so the browser never needs raw GCP credentials.

Usage:
    python -m src.frontend.server          # from project root
    python server.py                       # from this directory

Requires google-auth (uses Application Default Credentials).
Listens on http://localhost:8080
"""

import json
import logging
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import google.auth
import google.auth.transport.requests
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_config():
    """Load config from settings.yaml."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


CONFIG = _load_config()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT = int(os.environ.get("PORT", 8080))
STATIC_DIR = Path(__file__).resolve().parent

# Discovery Engine StreamAssist
DE_PROJECT = os.environ.get("PROJECT_ID", CONFIG.get("project", {}).get("id", ""))
DE_LOCATION = os.environ.get("DE_LOCATION", CONFIG.get("project", {}).get("location", "global"))
DE_ENGINE = os.environ.get("ENGINE_ID", CONFIG.get("project", {}).get("engine_id", ""))
DE_BASE = (
    f"https://discoveryengine.googleapis.com/v1alpha/projects/{DE_PROJECT}"
    f"/locations/{DE_LOCATION}/collections/default_collection"
    f"/engines/{DE_ENGINE}"
)

# Agent Engine (ADK)
AE_PROJECT_NUMBER = os.environ.get("AE_PROJECT_NUMBER", CONFIG.get("project", {}).get("number", ""))
AE_LOCATION = os.environ.get("AE_LOCATION", CONFIG.get("memory", {}).get("location", "us-central1"))
AE_RESOURCE_ID = os.environ.get("AE_RESOURCE_ID", CONFIG.get("project", {}).get("agent_engine_id", ""))
AE_BASE = (
    f"https://{AE_LOCATION}-aiplatform.googleapis.com/v1"
    f"/projects/{AE_PROJECT_NUMBER}/locations/{AE_LOCATION}"
    f"/reasoningEngines/{AE_RESOURCE_ID}"
)

# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
_credentials = None


def _get_token() -> str:
    """Return a valid access token using ADC."""
    global _credentials
    if _credentials is None:
        _credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    if not _credentials.valid:
        _credentials.refresh(google.auth.transport.requests.Request())
    return _credentials.token


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class FrontendHandler(SimpleHTTPRequestHandler):
    """Serves static files from STATIC_DIR and proxies /api/* requests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # --- Routing --------------------------------------------------------

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/stream-assist/sessions":
            self._proxy_create_session()
        elif path == "/api/stream-assist/query":
            self._proxy_stream_assist_query()
        elif path == "/api/agent-engine/query":
            self._proxy_agent_engine_query()
        elif path == "/api/agent-engine/stream":
            self._proxy_agent_engine_stream()
        else:
            self._json_error(404, "Not found")

    def do_GET(self):
        path = urlparse(self.path).path
        query_params = parse_qs(urlparse(self.path).query)

        if path == "/api/health":
            self._json_response({"status": "ok"})
            return
        if path == "/api/config":
            # Return safe, public config fields for frontend
            safe_config = {
                "retailer": {
                    "name": CONFIG.get("retailer", {}).get("name", "Grocery Retail"),
                    "tagline": CONFIG.get("retailer", {}).get("tagline", ""),
                },
                "project": {
                    "id": DE_PROJECT,
                    "number": AE_PROJECT_NUMBER,
                    "location": DE_LOCATION,
                    "engine_id": DE_ENGINE,
                    "agent_engine_id": AE_RESOURCE_ID,
                    "agent_engine_location": AE_LOCATION,
                },
                "voice": CONFIG.get("voice", {
                    "enabled": True,
                    "input_lang": "en-US",
                    "output_enabled": True,
                    "output_voice": "Google US English",
                    "output_rate": 1.0,
                    "output_pitch": 1.0,
                }),
            }
            self._json_response(safe_config)
            return
        if path == "/api/memory/status":
            self._proxy_memory_status(query_params)
            return
        if path.startswith("/api/images/"):
            self._proxy_gcs_image(path)
            return
        # Fall through to static file serving
        super().do_GET()

    # --- StreamAssist proxies -------------------------------------------

    def _proxy_create_session(self):
        """POST /api/stream-assist/sessions -> DE sessions endpoint."""
        import requests as req

        url = f"{DE_BASE}/sessions"
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": DE_PROJECT,
        }
        body = self._read_body()
        payload = json.loads(body) if body else {"displayName": "FrontendSession"}

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            self._json_response(resp.json())
        except Exception as exc:
            logger.exception("Session creation failed")
            self._json_error(502, str(exc))

    def _proxy_stream_assist_query(self):
        """POST /api/stream-assist/query -> DE streamAssist endpoint."""
        import requests as req

        url = f"{DE_BASE}/assistants/default_assistant:streamAssist"
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": DE_PROJECT,
        }
        body = self._read_body()
        payload = json.loads(body) if body else {}

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            self._json_response(resp.json())
        except Exception as exc:
            logger.exception("StreamAssist query failed")
            self._json_error(502, str(exc))

    # --- Agent Engine proxy ---------------------------------------------

    def _proxy_agent_engine_query(self):
        """POST /api/agent-engine/query -> Agent Engine streamQuery."""
        import time
        import requests as req

        url = f"{AE_BASE}:streamQuery"
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
        }
        body = self._read_body()
        payload = json.loads(body) if body else {}

        try:
            t0 = time.monotonic()
            resp = req.post(url, headers=headers, json=payload, timeout=120)
            latency_ms = int((time.monotonic() - t0) * 1000)
            resp.raise_for_status()

            # Extract Cloud Trace context for observability deeplinks
            trace_header = resp.headers.get("x-cloud-trace-context", "")
            trace_id = trace_header.split("/")[0] if trace_header else ""

            # Count tool invocations in the response
            tool_count = 0
            for line in resp.text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    parts = (event.get("content") or {}).get("parts") or []
                    for part in parts:
                        if "functionCall" in part:
                            tool_count += 1
                except (json.JSONDecodeError, TypeError):
                    pass

            # Build response with trace and performance metadata
            response_data = {
                "content": resp.text,
                "metadata": {
                    "latency_ms": latency_ms,
                    "tool_count": tool_count,
                },
            }
            if trace_id:
                response_data["metadata"]["trace_id"] = trace_id
                response_data["metadata"]["trace_url"] = (
                    f"https://console.cloud.google.com/traces/list"
                    f"?project={DE_PROJECT}&tid={trace_id}"
                )

            self._json_response(response_data)
        except Exception as exc:
            logger.exception("Agent Engine query failed")
            self._json_error(502, str(exc))

    # --- Agent Engine SSE streaming proxy --------------------------------

    def _proxy_agent_engine_stream(self):
        """POST /api/agent-engine/stream -> Agent Engine streamQuery with SSE."""
        import requests as req

        url = f"{AE_BASE}:streamQuery"
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
        }
        body = self._read_body()
        payload = json.loads(body) if body else {}

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=120, stream=True)
            resp.raise_for_status()

            # Send as Server-Sent Events
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Extract trace ID from response headers
            trace_header = resp.headers.get("x-cloud-trace-context", "")
            trace_id = trace_header.split("/")[0] if trace_header else ""
            if trace_id:
                event = json.dumps({"type": "trace", "trace_id": trace_id,
                    "trace_url": f"https://console.cloud.google.com/traces/list?project={DE_PROJECT}&tid={trace_id}"})
                self.wfile.write(f"data: {event}\n\n".encode())
                self.wfile.flush()

            # Stream each line as an SSE event
            for line in resp.iter_lines(decode_unicode=True):
                if line and line.strip():
                    event = json.dumps({"type": "content", "data": line.strip()})
                    self.wfile.write(f"data: {event}\n\n".encode())
                    self.wfile.flush()

            # Send done event
            self.wfile.write(b"data: {\"type\": \"done\"}\n\n")
            self.wfile.flush()

        except Exception as exc:
            logger.exception("Agent Engine stream failed")
            try:
                error = json.dumps({"type": "error", "message": str(exc)})
                self.wfile.write(f"data: {error}\n\n".encode())
                self.wfile.flush()
            except Exception:
                pass

    # --- Memory Bank proxy ----------------------------------------------

    def _proxy_memory_status(self, query_params):
        """GET /api/memory/status?user_id=... -> Memory Bank retrieve count."""
        import requests as req

        user_id = query_params.get("user_id", [""])[0]
        if not user_id:
            self._json_response({"count": 0, "error": "No user_id provided"})
            return

        resource_name = (
            f"projects/{AE_PROJECT_NUMBER}/locations/{AE_LOCATION}"
            f"/reasoningEngines/{AE_RESOURCE_ID}"
        )
        url = (
            f"https://{AE_LOCATION}-aiplatform.googleapis.com/v1beta1"
            f"/{resource_name}/memories:retrieve"
        )
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
        }
        payload = {"scope": {"user_id": user_id}}

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=15)
            if resp.ok:
                data = resp.json()
                memories = data.get("memories", [])
                # Extract snippet text from each memory for tooltip display
                snippets = []
                for m in memories[:5]:  # Limit to 5 most recent
                    fact = m.get("fact", "")
                    if fact:
                        snippet = fact[:120] + "..." if len(fact) > 120 else fact
                        snippets.append(snippet)
                self._json_response({
                    "count": len(memories),
                    "user_id": user_id,
                    "snippets": snippets,
                })
            else:
                self._json_response({"count": 0, "user_id": user_id, "snippets": []})
        except Exception as exc:
            logger.warning("Memory status check failed: %s", exc)
            self._json_response({"count": 0, "user_id": user_id, "snippets": []})

    # --- GCS image proxy ------------------------------------------------

    def _proxy_gcs_image(self, path):
        """GET /api/images/<blob_path> -> GCS blob content.

        Serves generated images from GCS through the proxy so the frontend
        can display them without signed URLs or CORS issues.
        """
        from google.cloud import storage

        blob_path = path.removeprefix("/api/images/")
        if not blob_path:
            self._json_error(400, "No image path specified")
            return

        gcs_bucket = CONFIG.get("gcs", {}).get(
            "bucket", f"{DE_PROJECT}-ge-workshop"
        )

        try:
            client = storage.Client(project=DE_PROJECT)
            bucket = client.bucket(gcs_bucket)
            blob = bucket.blob(blob_path)

            if not blob.exists():
                self._json_error(404, "Image not found")
                return

            image_bytes = blob.download_as_bytes()
            content_type = blob.content_type or "image/png"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(image_bytes)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(image_bytes)

        except Exception as exc:
            logger.warning("GCS image proxy failed: %s", exc)
            self._json_error(500, f"Failed to fetch image: {exc}")

    # --- Helpers --------------------------------------------------------

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _raw_response(self, text, status=200, content_type="text/plain"):
        body = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status, message):
        self._json_response({"error": message}, status=status)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def log_message(self, fmt, *args):
        logger.info(fmt, *args)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main():
    retailer_name = CONFIG.get("retailer", {}).get("name", "Grocery Retail")

    # Start voice WebSocket server in background thread
    try:
        from src.frontend.voice_server import start_voice_server
        voice_thread = start_voice_server()
        if voice_thread:
            logger.info("Voice WebSocket server started alongside HTTP server")
    except Exception as exc:
        logger.warning("Voice server not started: %s", exc)

    server = HTTPServer(("0.0.0.0", PORT), FrontendHandler)
    logger.info("%s frontend serving on http://localhost:%d", retailer_name, PORT)
    logger.info("Static files from %s", STATIC_DIR)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
