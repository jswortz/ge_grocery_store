# System Architecture

This document describes the architecture of the Gemini Enterprise Grocery Workshop. For setup instructions, see the [Setup Guide](setup.md).

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Presentation Layer](#presentation-layer)
3. [Agent Layer](#agent-layer)
4. [Search & Retrieval Layer](#search--retrieval-layer)
5. [Data Layer](#data-layer)
6. [MCP Integration](#mcp-integration)
7. [Deployment Architecture](#deployment-architecture)
8. [Configuration System](#configuration-system)
9. [Cross-References](#cross-references)

---

## High-Level Overview

The system is organized into four layers, each interfacing with Google Cloud services.

![System Architecture](diagrams/01_system_architecture.png)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                             │
│                                                                     │
│   ┌──────────────────────────┐     ┌─────────────────────────────┐  │
│   │   Frontend Web UI        │     │  StreamAssist Python Client  │  │
│   │   src/frontend/          │     │  src/client/stream_assist.py │  │
│   │   index.html + server.py │     │  REST client + retry logic   │  │
│   └──────────┬───────────────┘     └──────────────┬──────────────┘  │
│              │                                    │                  │
└──────────────┼────────────────────────────────────┼──────────────────┘
               │                                    │
               ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT LAYER                                 │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                    ADK Root Agent                             │  │
│   │                 "grocery_assistant"                            │  │
│   │              (gemini-3.0-flash)                               │  │
│   │                                                               │  │
│   │  DiscoveryEngineSearchTool  ──────┐                           │  │
│   │  (FunctionTool subclass)         │                           │  │
│   │                                   │                           │  │
│   │  ┌──────────────┐  ┌────────────────────┐                    │  │
│   │  │analytics_agent│  │   image_agent      │                    │  │
│   │  │  (sub-agent)  │  │   (sub-agent)      │                    │  │
│   │  │               │  │                    │                    │  │
│   │  │ BigQuery SQL  │  │  Imagen API        │                    │  │
│   │  │ FunctionTool  │  │  FunctionTool      │                    │  │
│   │  └──────┬───────┘  └────────┬───────────┘                    │  │
│   └─────────┼───────────────────┼────────────────────────────────┘  │
│             │                   │                                    │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              MCP Agent (Alternative)                         │   │
│   │           "mcp_grocery_analyst"                              │   │
│   │           src/mcp_agent/agent.py                             │   │
│   │                                                              │   │
│   │   ADK Agent --(MCP stdio)--> genai-toolbox --(API)--> BQ    │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└──────────────┬──────────────────┬────────────────────────────────────┘
               │                  │
               ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   SEARCH & RETRIEVAL LAYER                          │
│                                                                     │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │              Gemini Enterprise                              │    │
│   │         (Discovery Engine App)                              │    │
│   │       "grocery-workshop-engine"                             │    │
│   │                                                             │    │
│   │  ┌─────────────────┐  ┌──────────────────────────────┐     │    │
│   │  │   sop-store      │  │  brand-guidelines-store      │     │    │
│   │  │   (GCS PDFs)     │  │  (GCS PDFs)                  │     │    │
│   │  │                  │  │                               │     │    │
│   │  │  Closing procs   │  │  Colors, typography,         │     │    │
│   │  │  Opening procs   │  │  tone, logo usage            │     │    │
│   │  │  Safety checks   │  │                               │     │    │
│   │  └─────────────────┘  └──────────────────────────────┘     │    │
│   │                                                             │    │
│   │  Endpoints:                                                 │    │
│   │  - SearchService (direct search)                            │    │
│   │  - StreamAssist (conversational AI)                         │    │
│   └────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                  │
│                                                                     │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │              BigQuery Star Schema                           │    │
│   │           wortz-project-352116.ge_grocery_demo              │    │
│   │                                                             │    │
│   │  ┌──────────────────┐                                      │    │
│   │  │ fact_transactions │  12K+ rows                           │    │
│   │  │  transaction_id   │  transaction_ts, store_id,          │    │
│   │  │  employee_id      │  product_id, quantity,              │    │
│   │  │  total_amount     │  payment_method, customer_id        │    │
│   │  └────────┬─────────┘                                      │    │
│   │           │                                                 │    │
│   │     ┌─────┼─────────┬──────────────┬───────────────┐       │    │
│   │     ▼     ▼         ▼              ▼               │       │    │
│   │  dim_store  dim_product  dim_employee  dim_customer │       │    │
│   │  (3 rows)   (20 rows)    (15 rows)     (40 rows)   │       │    │
│   │                                                     │       │    │
│   │  Store Manager > Dept Manager > Cashier > Stock Clerk       │    │
│   │  Loyalty: Gold / Silver / Bronze                            │    │
│   └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │                  GCS Bucket                                 │    │
│   │     gs://wortz-project-352116-ge-workshop/                  │    │
│   │     SOP PDFs + Brand guideline PDFs                         │    │
│   └────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Presentation Layer

Two interfaces for interacting with the system:

### Frontend Web UI (`src/frontend/`)

A single-page branded web application with a Python proxy server.

| File | Purpose |
|------|---------|
| [`index.html`](../src/frontend/index.html) | Chat interface with ValueFresh Market branding |
| [`server.py`](../src/frontend/server.py) | HTTP proxy using Application Default Credentials |

**Design:**
- Green (#2e7d32) / gold (#f9a825) / white color scheme
- Two switchable backends: StreamAssist and Agent Engine
- Markdown rendering via marked.js with DOMPurify sanitization
- Session management for Discovery Engine conversations

**Proxy routes:**

| Frontend Route | Backend Target |
|----------------|----------------|
| `POST /api/stream-assist/sessions` | Discovery Engine `sessions` endpoint |
| `POST /api/stream-assist/query` | Discovery Engine `streamAssist` endpoint |
| `POST /api/agent-engine/query` | Agent Engine `streamQuery` endpoint |
| `GET /api/health` | Health check |

```bash
# Launch
python -m src.frontend
# Open http://localhost:8080
```

### StreamAssist Python Client (`src/client/stream_assist.py`)

A programmatic REST client for the Discovery Engine `streamAssist` endpoint.

- `StreamAssistClient.from_config()` — factory method reading from `config/settings.yaml`
- `create_session()` / `query()` — session lifecycle
- `StreamAssistResponse` dataclass — parsed response with text, thoughts, session info
- Tenacity retry logic for 429/5xx errors
- Used by `tests/test_acceptance.py` for acceptance testing

---

## Agent Layer

### ADK Multi-Agent Architecture (`src/agent/`)

The primary agent uses Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) with a multi-agent design.

![Agent Architecture](diagrams/02_agent_architecture.png)

```
┌────────────────────────────────────────────────────────┐
│                Root Agent                                │
│             "grocery_assistant"                           │
│          model: gemini-3.0-flash                         │
│                                                          │
│  Tools:                                                  │
│  ├── DiscoveryEngineSearchTool (FunctionTool subclass)   │
│  │    Searches: sop-store, brand-guidelines-store        │
│  │    Restricted via data_store_specs (excludes          │
│  │    workspace stores: Gmail, Calendar, Jira)           │
│  │                                                       │
│  Sub-agents (via transfer_to_agent):                     │
│  ├── analytics_agent                                     │
│  │    └── query_grocery_data (BigQuery FunctionTool)     │
│  │        Pattern-matched SQL generation                 │
│  │                                                       │
│  └── image_agent                                         │
│       └── generate_product_image (Imagen FunctionTool)   │
│           Vertex AI imagen-3.0-generate-002                   │
└────────────────────────────────────────────────────────┘
```

**Key design decision**: `DiscoveryEngineSearchTool` vs `VertexAiSearchTool`

`VertexAiSearchTool` adds a built-in Gemini retrieval tool that conflicts with the `transfer_to_agent` function tools injected by sub-agents. The ADK's `llm_agent.py` bypass check (`len(self.tools) > 1`) doesn't account for implicit transfer tools. `DiscoveryEngineSearchTool` is a `FunctionTool` subclass that wraps the SearchService REST API directly, avoiding this conflict entirely.

Implementation: [`src/agent/agent.py`](../src/agent/agent.py)

### Agent Files

| File | Purpose |
|------|---------|
| [`agent.py`](../src/agent/agent.py) | Root agent + sub-agents, `_load_config()` |
| [`tools/bq_tool.py`](../src/agent/tools/bq_tool.py) | BigQuery analytics FunctionTool |
| [`tools/image_gen_tool.py`](../src/agent/tools/image_gen_tool.py) | Imagen product image FunctionTool |
| [`tools/sop_tool.py`](../src/agent/tools/sop_tool.py) | SOP data store helper |
| [`prompts/system_prompts.py`](../src/agent/prompts/system_prompts.py) | Retailer-agnostic system instructions |

---

## Search & Retrieval Layer

### Gemini Enterprise (Discovery Engine)

The Discovery Engine app `grocery-workshop-engine` provides enterprise search and conversational AI:

**Engine configuration:**
- Solution type: `SOLUTION_TYPE_SEARCH`
- App type: `APP_TYPE_INTRANET`
- Search tier: `SEARCH_TIER_ENTERPRISE`
- Location: `global`

**Data stores:**

| Store ID | Source | Content |
|----------|--------|---------|
| `sop-store` | GCS PDFs | Closing/opening procedures, safety checklists |
| `brand-guidelines-store` | GCS PDFs | Colors, typography, tone of voice, logo usage |

**API endpoints used:**

| Endpoint | Used By | Purpose |
|----------|---------|---------|
| `SearchService.search()` | `DiscoveryEngineSearchTool`, tests | Direct document search |
| `streamAssist` | StreamAssist client, frontend | Conversational search with sessions |
| `sessions` | StreamAssist client, frontend | Session lifecycle management |

---

## Data Layer

### BigQuery Star Schema

Dataset: `wortz-project-352116.ge_grocery_demo`

```
                    ┌──────────────────┐
                    │ fact_transactions │
                    │   (12,000+ rows) │
                    └───────┬──────────┘
                            │
          ┌─────────┬───────┼───────┬──────────┐
          ▼         ▼       ▼       ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ dim_store│ │dim_product│ │dim_employ│ │dim_custom│
    │  3 rows  │ │  20 rows  │ │  15 rows │ │  40 rows │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**Relationships:**
- `fact_transactions.store_id` → `dim_store.store_id`
- `fact_transactions.product_id` → `dim_product.product_id`
- `fact_transactions.employee_id` → `dim_employee.employee_id`
- `fact_transactions.customer_id` → `dim_customer.customer_id`
- `dim_employee.store_id` → `dim_store.store_id`
- `dim_customer.home_store_id` → `dim_store.store_id`

**Schema files:**
- DDL: [`infra/bigquery/create_schema.sql`](../infra/bigquery/create_schema.sql)
- Seed data: [`infra/bigquery/seed_data.sql`](../infra/bigquery/seed_data.sql)

### Employee Role Hierarchy

```
Store Manager
  └── Department Manager
        ├── Cashier
        └── Stock Clerk
```

### Customer Loyalty Tiers

| Tier | Description |
|------|-------------|
| Gold | Top-tier loyalty members |
| Silver | Mid-tier loyalty members |
| Bronze | Entry-level loyalty members |

---

## MCP Integration

An alternative analytics approach using the [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox).

### Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────┐
│   ADK Agent      │     │  genai-toolbox   │     │ BigQuery │
│ mcp_grocery_     │────▶│  (subprocess)    │────▶│   API    │
│ analyst          │ MCP │  --prebuilt bq   │REST │          │
│                  │stdio│                  │     │          │
└──────────────────┘     └─────────────────┘     └──────────┘
```

**How it works:**
1. The ADK agent spawns the `genai-toolbox` binary as a subprocess
2. Communication happens via MCP over stdio (`StdioServerParameters`)
3. The toolbox runs in `--prebuilt bigquery` mode, exposing 9 tools
4. The LLM generates arbitrary SQL queries (not pattern-matched)

**Available MCP tools:**

| Tool | Purpose |
|------|---------|
| `execute_sql` | Run SQL queries |
| `list_table_ids` | List tables in a dataset |
| `get_table_info` | Get table schema and metadata |
| `get_dataset_info` | Get dataset metadata |
| `list_dataset_ids` | List datasets in project |
| `search_catalog` | Search for tables, views, models |
| `ask_data_insights` | AI-powered data analysis |
| `forecast` | Time series forecasting |
| `analyze_contribution` | Metric contribution analysis |

**vs. Main Agent's `bq_tool.py`:**

| Aspect | `bq_tool.py` (Main Agent) | MCP Agent |
|--------|---------------------------|-----------|
| SQL generation | Pattern-matched templates | LLM-generated arbitrary SQL |
| Tool count | 1 (query_grocery_data) | 9 (full BigQuery toolkit) |
| Schema awareness | Hardcoded in tool function | Embedded in agent instruction + `get_table_info` |
| Deployment | Agent Engine compatible | Requires `toolbox` binary |

**Key files:**
- [`src/mcp_agent/agent.py`](../src/mcp_agent/agent.py) — Agent definition
- [`src/mcp_agent/tools.yaml`](../src/mcp_agent/tools.yaml) — Toolbox configuration
- [`tests/test_mcp_agent.py`](../tests/test_mcp_agent.py) — 29 unit tests

---

## Request Processing Flow

The following diagram shows how a user query flows through the system from entry to grounded response.

![Data Flow](diagrams/03_data_flow.png)

---

## Deployment Architecture

### Agent Engine (Production)

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│ Client      │     │     Vertex AI Agent Engine                │
│ (REST API)  │────▶│     us-central1                           │
│             │     │                                           │
│ streamQuery │     │  ┌─────────────────────────────────────┐  │
│             │     │  │  ReasoningEngine                     │  │
│             │     │  │  ID: 3323818153208709120              │  │
│             │     │  │                                       │  │
│             │     │  │  ADK Agent (grocery_assistant)        │  │
│             │     │  │  ├── DiscoveryEngineSearchTool        │  │
│             │     │  │  ├── analytics_agent (BigQuery)       │  │
│             │     │  │  └── image_agent (Imagen)             │  │
│             │     │  │                                       │  │
│             │     │  │  OpenTelemetry: Enabled               │  │
│             │     │  └─────────────────────────────────────┘  │
│             │     │                                           │
└─────────────┘     └──────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            Discovery Engine   BigQuery        Vertex AI
            (Search)           (Analytics)     (Imagen)
```

**Resource:** `projects/679926387543/locations/us-central1/reasoningEngines/3323818153208709120`

**Deployment command:**
```bash
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent
```

---

## Configuration System

All configuration flows through `config/settings.yaml` with environment variable overrides for deployment.

```
┌────────────────────┐     ┌──────────────────────────────┐
│ config/             │     │ Environment Variables         │
│ settings.yaml       │     │ (Agent Engine deployment)     │
│                     │     │                               │
│ retailer.name       │◀───│ RETAILER_NAME                 │
│ project.id          │◀───│ PROJECT_ID                    │
│ project.engine_id   │◀───│ ENGINE_ID                     │
│ bigquery.project    │◀───│ BQ_PROJECT                    │
│ bigquery.dataset    │◀───│ BQ_DATASET                    │
└─────────┬──────────┘     └──────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────┐
│              _load_config()                          │
│  (src/agent/agent.py, src/mcp_agent/agent.py)       │
│                                                      │
│  1. Read settings.yaml                               │
│  2. Apply env var overrides                          │
│  3. Return merged config dict                        │
└──────────┬──────────────────────────────┬────────────┘
           │                              │
     ┌─────▼──────┐              ┌────────▼───────┐
     │ bq_tool.py │              │ system_prompts │
     │ image_gen  │              │ stream_assist  │
     │ sop_tool   │              │ mcp_agent      │
     └────────────┘              └────────────────┘
```

**No client names are hardcoded in source code.** Tests enforce this:
- `tests/test_bigquery.py` checks for forbidden names in BigQuery data
- `tests/test_agent.py` checks for forbidden names in system prompts
- `tests/test_mcp_agent.py` checks for forbidden names in MCP agent config

---

## Memory Bank

Memory Bank provides shared memory across agent sessions so the agent remembers user preferences, past interactions, and context across conversations.

### How It Works

```
┌──────────────┐     ┌──────────────────────────────────────┐
│ User (browser)│     │     Agent Engine                      │
│               │     │                                       │
│  localStorage │     │  ┌─────────────────────────────────┐  │
│  vf_user_id   │────▶│  │  ADK Agent                       │  │
│               │     │  │  ├── PreloadMemoryTool            │  │
│               │     │  │  │   (auto-loads memories per     │  │
│               │     │  │  │    user_id at each turn)       │  │
│               │     │  │  └── ...other tools               │  │
│               │     │  └─────────────┬───────────────────┘  │
│               │     │                │                       │
│               │     │  ┌─────────────▼───────────────────┐  │
│               │     │  │  VertexAiMemoryBankService       │  │
│               │     │  │  (scoped to agent_engine_id)     │  │
│               │     │  │                                   │  │
│               │     │  │  GenerateMemories: auto-extract   │  │
│               │     │  │  CreateMemory: agent-controlled   │  │
│               │     │  └─────────────────────────────────┘  │
│               │     │                                       │
└──────────────┘     └──────────────────────────────────────┘
```

**Key points:**
- `PreloadMemoryTool` is added to the root agent's tool list
- Memories are scoped per `user_id` — each browser gets a unique persistent ID via `localStorage`
- `VertexAiMemoryBankService` is configured at the Runner/deployment level, using the reasoning engine ID
- No separate resource provisioning needed — Memory Bank is a built-in feature of Agent Engine

**Configuration** (`config/settings.yaml`):
```yaml
memory:
  enabled: true
  location: "us-central1"   # Must match Agent Engine region
```

---

## Model Armor

Model Armor provides content safety screening on the Discovery Engine `grocery-workshop-engine` to filter prompts and responses for harmful content.

### Filters Enabled

| Filter | Purpose |
|--------|---------|
| RAI Harm Filter | Hate speech, violence, sexual content, dangerous content |
| PI & Jailbreak Filter | Prompt injection and jailbreak attempts |
| SDP Basic Filter | Sensitive Data Protection (PII detection) |
| Malicious URI Filter | Blocks malicious URLs in prompts/responses |

### Architecture

```
┌──────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  User    │────▶│  Model Armor         │────▶│ Discovery Engine │
│  Query   │     │  Template            │     │ grocery-workshop │
│          │     │  grocery-workshop-   │     │ -engine          │
│          │     │  armor               │     │                  │
│          │◀────│                      │◀────│  StreamAssist    │
│ Response │     │  Screens both        │     │  SearchService   │
│          │     │  input and output    │     │                  │
└──────────┘     └──────────────────────┘     └─────────────────┘
```

**Failure mode:** `FAIL_OPEN` — if Model Armor is unavailable, queries pass through to avoid blocking production traffic.

**Provisioning:** `bash infra/provision_model_armor.sh`

**Configuration** (`config/settings.yaml`):
```yaml
model_armor:
  enabled: true
  template_id: "grocery-workshop-armor"
  failure_mode: "FAIL_OPEN"
```

---

## Cross-References

| Document | Content |
|----------|---------|
| [README.md](../README.md) | Project overview, quick start, test matrix |
| [Setup Guide](setup.md) | Step-by-step provisioning instructions |
| [config/settings.yaml](../config/settings.yaml) | All retailer-specific configuration |
| [CLAUDE.md](../CLAUDE.md) | AI coding assistant guidance |
