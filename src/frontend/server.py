"""Lightweight proxy server for the ValueFresh Market frontend.

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT = int(os.environ.get("PORT", 8080))
STATIC_DIR = Path(__file__).resolve().parent

# Discovery Engine StreamAssist
DE_PROJECT = "wortz-project-352116"
DE_LOCATION = "global"
DE_ENGINE = "grocery-workshop-engine"
DE_BASE = (
    f"https://discoveryengine.googleapis.com/v1alpha/projects/{DE_PROJECT}"
    f"/locations/{DE_LOCATION}/collections/default_collection"
    f"/engines/{DE_ENGINE}"
)

# Agent Engine (ADK)
AE_PROJECT_NUMBER = "679926387543"
AE_LOCATION = "us-central1"
AE_RESOURCE_ID = "3323818153208709120"
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
        else:
            self._json_error(404, "Not found")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json_response({"status": "ok"})
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
        import requests as req

        url = f"{AE_BASE}:streamQuery"
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
        }
        body = self._read_body()
        payload = json.loads(body) if body else {}

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            # Agent Engine returns newline-delimited JSON; forward raw text
            self._raw_response(resp.text, content_type="text/plain")
        except Exception as exc:
            logger.exception("Agent Engine query failed")
            self._json_error(502, str(exc))

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
    server = HTTPServer(("0.0.0.0", PORT), FrontendHandler)
    logger.info("ValueFresh Market frontend serving on http://localhost:%d", PORT)
    logger.info("Static files from %s", STATIC_DIR)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
