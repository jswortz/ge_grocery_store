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
from socketserver import ThreadingMixIn
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
        elif path == "/api/bigquery/chart":
            self._proxy_bigquery_chart()
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
            project_cfg = CONFIG.get("project", {})
            models_cfg = CONFIG.get("models", {})
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
                    "data_agent_id": project_cfg.get("data_agent_id", ""),
                },
                "agent_engines": [
                    {
                        "id": AE_RESOURCE_ID,
                        "name": "Grocery Retail Assistant",
                        "type": "adk",
                        "model": models_cfg.get("adk", "gemini-3-pro-preview"),
                        "resource_name": f"reasoningEngines/{AE_RESOURCE_ID}",
                    },
                    {
                        "id": project_cfg.get("mcp_agent_engine_id", ""),
                        "name": "MCP Grocery Analyst",
                        "type": "mcp",
                        "model": models_cfg.get("adk", "gemini-3-pro-preview"),
                        "resource_name": f"reasoningEngines/{project_cfg.get('mcp_agent_engine_id', '')}",
                    },
                    {
                        "id": project_cfg.get("simulator_agent_engine_id", ""),
                        "name": "Shopper Simulator",
                        "type": "simulator",
                        "model": models_cfg.get("adk_fast", "gemini-3-flash-preview"),
                        "resource_name": f"reasoningEngines/{project_cfg.get('simulator_agent_engine_id', '')}",
                    },
                    {
                        "id": project_cfg.get("a2a_agent_engine_id", ""),
                        "name": "A2A Grocery Agent",
                        "type": "a2a",
                        "model": models_cfg.get("adk", "gemini-3-pro-preview"),
                        "resource_name": f"reasoningEngines/{project_cfg.get('a2a_agent_engine_id', '')}",
                        "a2a_url": project_cfg.get("a2a_cloud_run_url", ""),
                    },
                ],
                "voice": CONFIG.get("voice", {
                    "enabled": True,
                    "input_lang": "en-US",
                    "output_enabled": True,
                    "output_voice": "Google US English",
                    "output_rate": 1.0,
                    "output_pitch": 1.0,
                }),
                "agent_engine_mapping": {
                    project_cfg.get("agent_id", ""): AE_RESOURCE_ID,
                    project_cfg.get("a2a_agent_id", ""): project_cfg.get("a2a_agent_engine_id", ""),
                },
            }
            self._json_response(safe_config)
            return
        if path == "/api/memory/status":
            self._proxy_memory_status(query_params)
            return
        if path == "/api/stream-assist/agents":
            self._proxy_list_agents()
            return
        if path == "/api/stream-assist/data-stores":
            self._proxy_list_data_stores()
            return
        if path.startswith("/api/images/"):
            self._proxy_gcs_image(path)
            return
        # Fall through to static file serving
        super().do_GET()

    # --- StreamAssist proxies -------------------------------------------

    def _proxy_list_agents(self):
        """GET /api/stream-assist/agents -> list assistants and registered agents."""
        import requests as req

        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "X-Goog-User-Project": DE_PROJECT,
        }

        try:
            agents = []

            # 1. List top-level assistants
            resp = req.get(f"{DE_BASE}/assistants", headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for assistant in data.get("assistants", []):
                name = assistant.get("name", "")
                display_name = assistant.get("displayName", name.split("/")[-1])
                agent_id = name.split("/")[-1] if "/" in name else name
                agents.append({
                    "id": agent_id,
                    "name": display_name,
                    "fullName": name,
                    "type": "assistant",
                    "actions": [],
                })

            # 2. List registered agents under default_assistant
            try:
                agents_url = f"{DE_BASE}/assistants/default_assistant/agents"
                resp2 = req.get(agents_url, headers=headers, timeout=15)
                resp2.raise_for_status()
                agents_data = resp2.json()
                for agent in agents_data.get("agents", []):
                    name = agent.get("name", "")
                    display_name = agent.get("displayName", name.split("/")[-1])
                    agent_id = name.split("/")[-1] if "/" in name else name
                    state = agent.get("state", "UNKNOWN")
                    if state != "ENABLED":
                        continue
                    agent_type = "managed"
                    if "adkAgentDefinition" in agent:
                        agent_type = "adk"
                    elif "a2aAgentDefinition" in agent:
                        agent_type = "a2a"
                    agents.append({
                        "id": agent_id,
                        "name": display_name,
                        "fullName": name,
                        "type": agent_type,
                        "description": agent.get("description", ""),
                        "actions": [],
                    })
            except Exception as exc2:
                logger.debug("Could not list registered agents: %s", exc2)

            self._json_response({"agents": agents})
        except Exception as exc:
            logger.warning("List agents failed: %s", exc)
            self._json_response({"agents": [
                {"id": "default_assistant", "name": "Default Assistant", "fullName": "",
                 "type": "assistant", "actions": []},
            ]})

    def _proxy_list_data_stores(self):
        """GET /api/stream-assist/data-stores -> list Discovery Engine data stores."""
        import requests as req

        # List data stores at the collection level
        url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{DE_PROJECT}"
            f"/locations/{DE_LOCATION}/collections/default_collection/dataStores"
        )
        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "X-Goog-User-Project": DE_PROJECT,
        }

        try:
            resp = req.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            stores = []
            for ds in data.get("dataStores", []):
                ds_name = ds.get("name", "")
                ds_id = ds_name.split("/")[-1] if "/" in ds_name else ds_name
                display_name = ds.get("displayName", ds_id)
                # Determine source type from the data store config
                content_config = ds.get("contentConfig", "")
                solution_types = ds.get("solutionTypes", [])
                stores.append({
                    "id": ds_id,
                    "name": display_name,
                    "contentConfig": content_config,
                    "solutionTypes": solution_types,
                })
            self._json_response({"dataStores": stores})
        except Exception as exc:
            logger.warning("List data stores failed: %s", exc)
            # Return known defaults as fallback
            self._json_response({"dataStores": [
                {"id": "sop-store", "name": "SOPs", "contentConfig": "CONTENT_REQUIRED", "solutionTypes": []},
                {"id": "brand-guidelines-store", "name": "Brand Guidelines", "contentConfig": "CONTENT_REQUIRED", "solutionTypes": []},
            ]})

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
        """POST /api/stream-assist/query -> DE streamAssist endpoint.

        Always routes through 'default_assistant'. Registered agents (ADK,
        A2A, managed) are automatically available to the assistant for
        query routing — the StreamAssist API only supports assistant-level
        endpoints, not individual agent endpoints.
        """
        import requests as req

        body = self._read_body()
        payload = json.loads(body) if body else {}

        # Strip assistant_id — always route through default_assistant.
        # Agent routing is handled via agentsSpec.agentSpecs[] in payload.
        payload.pop("assistant_id", None)
        url = f"{DE_BASE}/assistants/default_assistant:streamAssist"

        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": DE_PROJECT,
        }

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

        body = self._read_body()
        payload = json.loads(body) if body else {}

        # Ensure user_id is present (required by ADK >= 1.19)
        if "input" in payload and "user_id" not in payload["input"]:
            payload["input"]["user_id"] = payload.get("user_id", "frontend-user")
        elif "input" not in payload:
            payload.setdefault("input", {})["user_id"] = "frontend-user"

        # Allow frontend to specify an alternative agent engine resource ID
        resource_id = payload.pop("resource_id", None)
        if resource_id:
            url = (
                f"https://{AE_LOCATION}-aiplatform.googleapis.com/v1"
                f"/projects/{AE_PROJECT_NUMBER}/locations/{AE_LOCATION}"
                f"/reasoningEngines/{resource_id}:streamQuery"
            )
        else:
            url = f"{AE_BASE}:streamQuery"

        headers = {
            "Authorization": f"Bearer {_get_token()}",
            "Content-Type": "application/json",
        }

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

        # Ensure user_id is present (required by ADK >= 1.19)
        if "input" in payload and "user_id" not in payload["input"]:
            payload["input"]["user_id"] = payload.get("user_id", "frontend-user")
        elif "input" not in payload:
            payload.setdefault("input", {})["user_id"] = "frontend-user"

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

    # --- BigQuery chart data proxy --------------------------------------

    def _proxy_bigquery_chart(self):
        """POST /api/bigquery/chart -> execute SQL and return rows as JSON.

        Accepts: {"query": "user's natural language query"}
        Returns: {"columns": [...], "rows": [[...], ...], "chart_type": "line|bar|pie"}

        Maps common analytics questions to SQL queries against ge_grocery_demo.
        """
        from google.cloud import bigquery

        body = self._read_body()
        payload = json.loads(body) if body else {}
        user_query = payload.get("query", "").lower()

        bq_project = CONFIG.get("bigquery", {}).get("project", DE_PROJECT)
        bq_dataset = CONFIG.get("bigquery", {}).get("dataset", "ge_grocery_demo")
        table_prefix = f"`{bq_project}.{bq_dataset}`"

        # Map user queries to SQL + chart config
        sql, chart_type, chart_title = self._map_query_to_sql(
            user_query, table_prefix
        )

        if not sql:
            self._json_response({
                "columns": [], "rows": [],
                "chart_type": "bar",
                "title": "Chart not available",
                "error": "Could not generate chart for this query",
            })
            return

        try:
            client = bigquery.Client(project=bq_project)
            query_job = client.query(sql)
            results = query_job.result()

            columns = [field.name for field in results.schema]
            rows = [list(row.values()) for row in results]
            # Convert non-serializable types
            clean_rows = []
            for row in rows:
                clean_row = []
                for val in row:
                    if hasattr(val, 'isoformat'):
                        clean_row.append(val.isoformat())
                    elif isinstance(val, (int, float, str, bool)) or val is None:
                        clean_row.append(val)
                    else:
                        clean_row.append(str(val))
                clean_rows.append(clean_row)

            self._json_response({
                "columns": columns,
                "rows": clean_rows,
                "chart_type": chart_type,
                "title": chart_title,
            })
        except Exception as exc:
            logger.warning("BigQuery chart query failed: %s", exc)
            self._json_response({
                "columns": [], "rows": [],
                "chart_type": "bar",
                "title": "Query error",
                "error": str(exc),
            })

    @staticmethod
    def _map_query_to_sql(query, table_prefix):
        """Map a natural language query to a SQL query, chart type, and title."""
        import re

        # Sales/revenue over time
        if re.search(r'(sales|revenue|total.?amount)\b.*\b(over time|by (day|date|month|week)|trend|daily|monthly|weekly)', query):
            if 'month' in query:
                return (
                    f"SELECT FORMAT_TIMESTAMP('%Y-%m', transaction_ts) AS month, "
                    f"ROUND(SUM(total_amount), 2) AS total_sales "
                    f"FROM {table_prefix}.fact_transactions "
                    f"GROUP BY month ORDER BY month",
                    "bar", "Monthly Sales Revenue"
                )
            return (
                f"SELECT DATE(transaction_ts) AS date, "
                f"ROUND(SUM(total_amount), 2) AS total_sales "
                f"FROM {table_prefix}.fact_transactions "
                f"GROUP BY date ORDER BY date",
                "line", "Daily Sales Revenue"
            )

        # Transactions over time
        if re.search(r'(transaction|order)s?\b.*\b(over time|by (day|date|month|week)|trend|daily|monthly|weekly)', query):
            if 'month' in query:
                return (
                    f"SELECT FORMAT_TIMESTAMP('%Y-%m', transaction_ts) AS month, "
                    f"COUNT(*) AS transaction_count "
                    f"FROM {table_prefix}.fact_transactions "
                    f"GROUP BY month ORDER BY month",
                    "bar", "Monthly Transaction Count"
                )
            return (
                f"SELECT DATE(transaction_ts) AS date, "
                f"COUNT(*) AS transaction_count "
                f"FROM {table_prefix}.fact_transactions "
                f"GROUP BY date ORDER BY date",
                "line", "Daily Transaction Count"
            )

        # Top products (by revenue or quantity)
        if re.search(r'top.*(product|item|seller)', query):
            limit = 10
            if re.search(r'top\s+(\d+)', query):
                limit = int(re.search(r'top\s+(\d+)', query).group(1))
            if 'quantity' in query or 'units' in query or 'sold' in query:
                return (
                    f"SELECT p.product_name, SUM(t.quantity) AS total_quantity "
                    f"FROM {table_prefix}.fact_transactions t "
                    f"JOIN {table_prefix}.dim_product p USING(product_id) "
                    f"GROUP BY p.product_name ORDER BY total_quantity DESC LIMIT {limit}",
                    "bar", f"Top {limit} Products by Quantity Sold"
                )
            return (
                f"SELECT p.product_name, ROUND(SUM(t.total_amount), 2) AS total_revenue "
                f"FROM {table_prefix}.fact_transactions t "
                f"JOIN {table_prefix}.dim_product p USING(product_id) "
                f"GROUP BY p.product_name ORDER BY total_revenue DESC LIMIT {limit}",
                "bar", f"Top {limit} Products by Revenue"
            )

        # Sales by store
        if re.search(r'(sales|revenue)\b.*\b(by|per|each)\s+store', query):
            return (
                f"SELECT s.store_name, ROUND(SUM(t.total_amount), 2) AS total_sales "
                f"FROM {table_prefix}.fact_transactions t "
                f"JOIN {table_prefix}.dim_store s USING(store_id) "
                f"GROUP BY s.store_name ORDER BY total_sales DESC",
                "bar", "Sales by Store"
            )

        # Sales by category
        if re.search(r'(sales|revenue)\b.*\b(by|per|each)\s+(category|department)', query):
            return (
                f"SELECT p.category, ROUND(SUM(t.total_amount), 2) AS total_sales "
                f"FROM {table_prefix}.fact_transactions t "
                f"JOIN {table_prefix}.dim_product p USING(product_id) "
                f"GROUP BY p.category ORDER BY total_sales DESC",
                "bar", "Sales by Category"
            )

        # Payment methods
        if re.search(r'payment.*(method|type|breakdown|mix)', query):
            return (
                f"SELECT payment_method, COUNT(*) AS count, "
                f"ROUND(SUM(total_amount), 2) AS total "
                f"FROM {table_prefix}.fact_transactions "
                f"GROUP BY payment_method ORDER BY total DESC",
                "pie", "Payment Method Distribution"
            )

        # Loyalty tier analysis
        if re.search(r'(loyalty|tier|customer)\b.*\b(breakdown|distribution|spend|revenue)', query):
            return (
                f"SELECT c.loyalty_tier, COUNT(DISTINCT c.customer_id) AS customers, "
                f"ROUND(SUM(t.total_amount), 2) AS total_spend "
                f"FROM {table_prefix}.fact_transactions t "
                f"JOIN {table_prefix}.dim_customer c USING(customer_id) "
                f"GROUP BY c.loyalty_tier ORDER BY total_spend DESC",
                "bar", "Customer Loyalty Tier Analysis"
            )

        # Sales by employee
        if re.search(r'(sales|revenue|performance)\b.*\b(by|per|each)\s+(employee|staff|cashier)', query):
            return (
                f"SELECT CONCAT(e.first_name, ' ', e.last_name) AS employee, "
                f"e.role, ROUND(SUM(t.total_amount), 2) AS total_sales "
                f"FROM {table_prefix}.fact_transactions t "
                f"JOIN {table_prefix}.dim_employee e USING(employee_id) "
                f"GROUP BY employee, e.role ORDER BY total_sales DESC",
                "bar", "Sales by Employee"
            )

        # Generic "graph" or "chart" request - default to daily sales
        if re.search(r'(graph|chart|plot|visuali)', query):
            return (
                f"SELECT DATE(transaction_ts) AS date, "
                f"ROUND(SUM(total_amount), 2) AS total_sales "
                f"FROM {table_prefix}.fact_transactions "
                f"GROUP BY date ORDER BY date",
                "line", "Daily Sales Overview"
            )

        return None, None, None

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

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    server = ThreadedHTTPServer(("0.0.0.0", PORT), FrontendHandler)
    logger.info("%s frontend serving on http://localhost:%d", retailer_name, PORT)
    logger.info("Static files from %s", STATIC_DIR)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
