# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Constraint

**Never hardcode retail client names (e.g., "Kroger", "HEB") anywhere in source code, SQL, config, or documentation.** All retailer-specific strings are parameterized through `config/settings.yaml`. Code reads `config["retailer"]["name"]` at runtime. Tests in `tests/test_bigquery.py` and `tests/test_mcp_agent.py` enforce this with forbidden-name checks.

## Commands

```bash
# Install
pip install -e ".[dev]"

# Unit tests (no GCP credentials needed)
python -m pytest tests/test_agent.py tests/test_stream_assist.py tests/test_mcp_agent.py tests/test_a2a_agent.py "tests/test_model_armor.py::TestModelArmorConfig" -v

# All tests (requires gcloud auth + provisioned resources)
python -m pytest tests/ -v

# Single test file
python -m pytest tests/test_agent.py -v

# Single test
python -m pytest tests/test_agent.py::TestBQTool::test_generate_sql_top_products -v

# Integration tests only
python -m pytest tests/ -v -m integration

# Generate PDFs
python -m src.docs_gen.sop_generator
python -m src.docs_gen.brand_guidelines
python -m src.docs_gen.marketing_assets
python -m src.docs_gen.strategy_report

# Launch ADK agent locally
cd src/agent && adk web

# Launch MCP agent locally (requires genai-toolbox binary)
cd src/mcp_agent && adk web

# Launch frontend UI
python -m src.frontend    # http://localhost:8080

# Deploy ADK agent to Agent Engine
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent
```

## Architecture

This is a **workshop demo repo** demonstrating **Gemini Enterprise** (the product name for Google Cloud's Discovery Engine API) for grocery retail. "Discovery Engine" is the API; "Gemini Enterprise" is the customer-facing product name. Use "Gemini Enterprise (Discovery Engine API)" when both precision and branding matter. Full architecture docs at `docs/architecture.md`.

### Gemini 3 Model Regime

All agents use the Gemini 3 model family (`config/settings.yaml` → `models` section):
- `gemini-3-pro-preview` → Root agent orchestrator, MCP agent (complex reasoning + tool use)
- `gemini-3-flash-preview` → Sub-agents: analytics_agent, image_agent, simulator (low latency)
- `gemini-3-pro-image-preview` → Image generation (native Gemini 3 image output)

### Seven subsystems

**Frontend Web UI** (`src/frontend/`): Branded single-page chat app with threaded Python proxy server (`ThreadingMixIn` + `HTTPServer` to handle concurrent requests during long API calls). Three backend modes: StreamAssist, Agent Engine, and Voice Ops. Agent selector dropdown for StreamAssist assistant routing with type badges: `[Data]` for Data Insights Agent, `[Research]` for Deep Research, `[ADK]`/`[A2A]` for agent types. `sendSample()` supports `agentId` for both StreamAssist and Agent Engine backends to auto-select the target agent (e.g., CLTV button routes to Data Insights Agent). Voice input via Gemini Live (WebSocket port 8081). Model Armor safety demo buttons. Memory Bank tooltip. Cloud Trace deeplinks. Proxy routes: `/api/stream-assist/*`, `/api/agent-engine/*`, `/api/images/*`, `/api/memory/status`, `/api/config`. Client-side greeting handler for conversational queries. Uses ADC for auth. Launch with `python -m src.frontend`.

**StreamAssist Client** (`src/client/stream_assist.py`): REST client for the Discovery Engine `streamAssist` endpoint. Key class is `StreamAssistClient` with `create_session()` and `query()` methods. Uses tenacity retry logic for transient errors (429, 5xx). Parses responses into `StreamAssistResponse` dataclasses. Configured via `StreamAssistClient.from_config()` which reads `config/settings.yaml`.

**ADK Agent** (`src/agent/`): Google Agent Development Kit multi-agent architecture:
- Root agent `grocery_assistant` (Gemini 3 Pro) with `DiscoveryEngineSearchTool` (searches sop-store and brand-guidelines-store via the engine, restricted with `data_store_specs` to exclude workspace data stores)
- `analytics_agent` sub-agent (Gemini 3 Flash) with `query_grocery_data` FunctionTool (BigQuery)
- `image_agent` sub-agent (Gemini 3 Flash) with `generate_product_image` FunctionTool (Gemini 3 Pro Image)
- `delegate_to_simulator` tool — calls Simulator Agent Engine via `streamQuery` REST API
- `PreloadMemoryTool` for cross-session user-scoped memory via Vertex AI Memory Bank

Key design choices:
- Uses `DiscoveryEngineSearchTool` (a `FunctionTool` subclass) instead of `VertexAiSearchTool` because `VertexAiSearchTool` adds a built-in Gemini retrieval tool that cannot coexist with the `transfer_to_agent` function tools injected by sub-agents.
- Memory Bank integration via `app.py` pattern: Each agent (main, MCP, simulator) has an `app.py` that creates a `VertexAiMemoryBankService` (or `InMemoryMemoryService` for local dev) and configures it on the ADK `App` instance. This enables shared user-scoped memories across all agents.

**MCP Agent** (`src/mcp_agent/`): Alternative analytics agent using MCP Toolbox for Databases (`genai-toolbox`). Connects to BigQuery via MCP over stdio. The LLM generates arbitrary SQL (vs. pattern-matched SQL in `bq_tool.py`). Requires the `toolbox` binary. 9 BigQuery tools available: `execute_sql`, `list_table_ids`, `get_table_info`, `forecast`, `analyze_contribution`, etc.

**Document Generators** (`src/docs_gen/`): ReportLab-based PDF generators. Each module has a `generate_*()` function that reads retailer name from config and outputs to `data/`. These are standalone scripts, not part of the agent runtime.

### Config-driven design

Central config loader in `src/agent/agent.py:_load_config()` reads `config/settings.yaml` with env var overrides for Agent Engine deployment (`RETAILER_NAME`, `PROJECT_ID`, `ENGINE_ID`, `BQ_PROJECT`, `BQ_DATASET`). All submodules (bq_tool, image_gen_tool, system_prompts, mcp_agent) delegate to this loader or implement the same pattern.

### Deployed resources

- **Agent Engine (Main)**: `reasoningEngines/3727910666648944640` — Grocery Retail Assistant (OTel enabled)
- **Agent Engine (MCP)**: `reasoningEngines/5787744546217525248` — MCP Grocery Analyst (OTel enabled)
- **Agent Engine (Simulator)**: `reasoningEngines/7053256041508634624` — Shopper Simulator w/ endcap A/B testing (OTel enabled)
- **Cloud Run (A2A)**: `https://grocery-a2a-agent-in2bk2mdwa-uc.a.run.app` — A2A protocol agent
- **Discovery Engine**: `grocery-workshop-engine` (global, SEARCH_TIER_ENTERPRISE)
- **Model Armor**: `grocery-workshop-armor-us` template (us multi-region, applied to Discovery Engine assistant)
- **Data stores**: `sop-store` (GCS), `brand-guidelines-store` (GCS), plus workspace stores (Gmail, Calendar, Jira — excluded from agent search)
- **BigQuery**: `wortz-project-352116.ge_grocery_demo` (star schema with 12K+ transactions)

### BigQuery star schema

Dataset `ge_grocery_demo` in `wortz-project-352116`:
- `fact_transactions` (12K rows) — FK to store, employee, product, customer
- `dim_store` (3 rows) — store_name, city, state
- `dim_product` (20 rows) — includes `image_uri` and `description` for multi-modal enrichment
- `dim_employee` (15 rows) — role hierarchy: Store Manager > Department Manager > Cashier > Stock Clerk
- `dim_customer` (40 rows) — loyalty_tier: Gold/Silver/Bronze

DDL in `infra/bigquery/create_schema.sql`, seed data in `infra/bigquery/seed_data.sql`.

### Test structure (269 unit + 42 integration)

- `tests/test_agent.py` (53) — **unit tests**, system prompts, SQL gen, tool configs, memory, voice, frontend, agent refactor, simulator scenario validation
- `tests/test_stream_assist.py` (14 unit + 1 integration) — StreamAssist client, parsing, error handling, infra scripts
- `tests/test_mcp_agent.py` (34) — **unit tests**, validates MCP agent config, schema context, instructions, toolbox path resolution
- `tests/test_a2a_agent.py` (31) — **unit tests**, validates A2A agent config, AgentCard, skills, Cloud Run files, simulator agent, report generator, model config
- `tests/test_frontend.py` (52) — **unit tests**, compare-tab removal, Imagen labels, data-source toggle, agent selector, routing, voice, architecture panel, model card, thinking display, simulator labels, report endpoint
- `tests/test_frontend_e2e.py` (75) — **unit tests**, tabs, agent selector, data stores, voice ops, streaming, multi-turn, deployment scripts, E2E page load, API endpoints
- `tests/test_model_armor.py` (10 unit + 5 integration) — validates Model Armor config, API schema, live template and assistant
- `tests/test_discovery_engine.py` (4) — **integration**, validates Discovery Engine SearchService directly against SOP and brand data stores
- `tests/test_agent_engine.py` (5) — **integration**, validates deployed ADK agent via Agent Engine REST API (SOP search, analytics, brand guidelines)
- `tests/test_bigquery.py` (12) — **integration**, validates schema and forbidden names against live BigQuery
- `tests/test_memory_bank.py` (9) — **integration**, validates Memory Bank service and user-scoped memory persistence
- `tests/test_acceptance.py` (6) — **integration**, validates acceptance criteria (greeting, SOP retrieval, brand guidelines) via StreamAssist

### Infrastructure scripts

`infra/provision_engine.sh` creates a Discovery Engine chat app. `infra/provision_datastore.sh` creates data stores, uploads PDFs to GCS, and imports documents. `infra/upload_assets.sh` handles GCS/Drive uploads. `infra/provision_model_armor.sh` creates a Model Armor template and enables it on the Discovery Engine assistant (requires `modelarmor.googleapis.com` API and `roles/modelarmor.admin`). All scripts read project config from `config/settings.yaml`.
