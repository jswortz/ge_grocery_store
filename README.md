# Gemini Enterprise Grocery Workshop

A customer-facing workshop demonstrating **Gemini Enterprise** (Discovery Engine) capabilities, advanced reasoning, and platform extensibility for grocery retail. This repo is a reusable, retailer-agnostic resource — no client names are hardcoded anywhere.

## Architecture Overview

This workshop integrates three Google Cloud AI surfaces:

```
                    ┌──────────────────────────────────────────┐
                    │          Gemini Enterprise                │
                    │      (Discovery Engine App)               │
                    │                                          │
                    │  ┌─────────────┐  ┌───────────────────┐  │
                    │  │  SOP Store   │  │ Brand Guidelines  │  │
                    │  │  (GCS PDFs)  │  │   Store (GCS)     │  │
                    │  └──────┬──────┘  └────────┬──────────┘  │
                    │         │                  │              │
                    │         ▼                  ▼              │
                    │  ┌─────────────────────────────────┐     │
                    │  │   StreamAssist REST API          │     │
                    │  │   (Search + Conversational AI)   │     │
                    │  └─────────────────────────────────┘     │
                    └──────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ StreamAssist      │     │ ADK Agent            │     │ BigQuery Star    │
│ Client (Python)   │     │ (Agent Engine)       │     │ Schema           │
│                   │     │                      │     │                  │
│ src/client/       │     │ src/agent/           │     │ ge_grocery_demo  │
│ stream_assist.py  │     │ agent.py             │     │                  │
│                   │     │ ├─ Discovery Search  │     │ fact_transactions│
│ • Session mgmt    │     │ ├─ BQ Analytics      │     │ dim_store        │
│ • Retry logic     │     │ ├─ Image Generation  │     │ dim_product      │
│ • Response parse  │     │ └─ Sub-agents        │     │ dim_employee     │
└──────────────────┘     └─────────────────────┘     │ dim_customer     │
                                                      └──────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **StreamAssist Client** | [`src/client/stream_assist.py`](src/client/stream_assist.py) | REST client for Discovery Engine `streamAssist` endpoint |
| **ADK Agent** | [`src/agent/agent.py`](src/agent/agent.py) | Multi-agent orchestrator deployed to [Agent Engine](#agent-engine-deployment) |
| **BQ Analytics Tool** | [`src/agent/tools/bq_tool.py`](src/agent/tools/bq_tool.py) | Pattern-matched SQL against star schema |
| **Image Gen Tool** | [`src/agent/tools/image_gen_tool.py`](src/agent/tools/image_gen_tool.py) | Vertex AI Imagen for brand-compliant product images |
| **System Prompts** | [`src/agent/prompts/system_prompts.py`](src/agent/prompts/system_prompts.py) | Config-driven, retailer-agnostic agent instructions |
| **Document Generators** | [`src/docs_gen/`](src/docs_gen/) | ReportLab PDF generators for SOPs, brand guides, reports |
| **Infrastructure** | [`infra/`](infra/) | Shell scripts for Discovery Engine and BigQuery provisioning |

---

## Prerequisites

- Python 3.10+
- Google Cloud SDK (`gcloud`) authenticated with project access
- Access to `wortz-project-352116` (or update [`config/settings.yaml`](config/settings.yaml))
- APIs enabled: Discovery Engine, Vertex AI, BigQuery

---

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Run unit tests (no GCP credentials needed)
python -m pytest tests/test_agent.py tests/test_stream_assist.py -v

# 3. Set up BigQuery schema and seed data
bq mk --dataset wortz-project-352116:ge_grocery_demo
bq query --use_legacy_sql=false < infra/bigquery/create_schema.sql
bq query --use_legacy_sql=false < infra/bigquery/seed_data.sql

# 4. Generate workshop documents (SOPs, brand guidelines)
python -m src.docs_gen.sop_generator
python -m src.docs_gen.brand_guidelines

# 5. Provision Discovery Engine app and data stores
bash infra/provision_engine.sh
bash infra/provision_datastore.sh
bash infra/upload_assets.sh

# 6. Launch ADK agent locally
cd src/agent && adk web
```

See the [Setup Guide](docs/setup.md) for detailed step-by-step instructions.

---

## Configuration

All retailer-specific strings live in [`config/settings.yaml`](config/settings.yaml). No client names are hardcoded in source code — update the config to customize for any retail client.

Key config sections:

```yaml
retailer:
  name: "ValueFresh Market"        # Injected into all prompts and tools
project:
  id: "wortz-project-352116"
  engine_id: "grocery-workshop-engine"
  agent_engine_id: "3323818153208709120"  # Deployed ADK agent
bigquery:
  project: "wortz-project-352116"
  dataset: "ge_grocery_demo"
```

---

## ADK Agent Architecture

The agent uses a **multi-agent architecture** with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/):

```
┌─────────────────────────────────────────────────────────┐
│                    Root Agent                            │
│                 "grocery_assistant"                       │
│              (gemini-2.0-flash)                          │
│                                                          │
│  Tools:                                                  │
│  ├─ DiscoveryEngineSearchTool                            │
│  │   ├─ sop-store (closing/opening procedures)           │
│  │   └─ brand-guidelines-store (colors, tone, typography)│
│  │                                                       │
│  Sub-agents:                                             │
│  ├─ analytics_agent                                      │
│  │   └─ query_grocery_data (BigQuery FunctionTool)       │
│  └─ image_agent                                          │
│      └─ generate_product_image (Imagen FunctionTool)     │
└─────────────────────────────────────────────────────────┘
```

**Why `DiscoveryEngineSearchTool` instead of `VertexAiSearchTool`?**

`VertexAiSearchTool` adds a built-in Gemini retrieval tool that cannot coexist with the `transfer_to_agent` function tools injected by sub-agents. `DiscoveryEngineSearchTool` is a `FunctionTool` subclass that wraps the Discovery Engine SearchService REST API as a regular function tool, avoiding this conflict. See [`src/agent/agent.py`](src/agent/agent.py) for the implementation.

---

## Agent Engine Deployment

The ADK agent is deployed to **Vertex AI Agent Engine** for production use:

```bash
# Deploy (from project root)
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent

# Current deployment
# Agent Engine ID: 3323818153208709120
# Resource: projects/679926387543/locations/us-central1/reasoningEngines/3323818153208709120
```

The deployment uses environment variables from [`src/agent/.env`](src/agent/.env) for config overrides (retailer name, project ID, engine ID, BigQuery coordinates) and OpenTelemetry instrumentation.

**Query the deployed agent:**

```python
import requests
import google.auth
from google.auth.transport.requests import Request

credentials, _ = google.auth.default()
credentials.refresh(Request())

url = "https://us-central1-aiplatform.googleapis.com/v1/projects/679926387543/locations/us-central1/reasoningEngines/3323818153208709120:streamQuery"
resp = requests.post(url,
    headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},
    json={"input": {"message": "What are the closing procedures?", "user_id": "demo-user"}})

for line in resp.text.strip().split("\n"):
    import json
    event = json.loads(line)
    for part in event.get("content", {}).get("parts", []):
        if "text" in part:
            print(part["text"])
```

---

## BigQuery Star Schema

Dataset `ge_grocery_demo` contains a retail analytics star schema:

| Table | Rows | Key Columns |
|-------|------|-------------|
| `fact_transactions` | 12,000+ | transaction_id, store_id, product_id, quantity, total_amount |
| `dim_store` | 3 | store_name, city, state, square_feet |
| `dim_product` | 20 | product_name, category, brand, image_uri, description |
| `dim_employee` | 15 | first_name, last_name, role (4-level hierarchy) |
| `dim_customer` | 40 | loyalty_tier (Gold/Silver/Bronze), points_balance |

Schema DDL: [`infra/bigquery/create_schema.sql`](infra/bigquery/create_schema.sql)
Seed data: [`infra/bigquery/seed_data.sql`](infra/bigquery/seed_data.sql)

---

## Testing

The test suite validates all layers — from unit tests (no GCP needed) to end-to-end integration tests against live services.

```bash
# Unit tests only (fast, no credentials needed)
python -m pytest tests/test_agent.py tests/test_stream_assist.py -v

# All integration tests (requires gcloud auth + provisioned resources)
python -m pytest tests/ -v

# Specific test suites
python -m pytest tests/test_discovery_engine.py -v    # Discovery Engine search
python -m pytest tests/test_agent_engine.py -v         # Deployed Agent Engine
python -m pytest tests/test_bigquery.py -v             # BigQuery schema/data
python -m pytest tests/test_acceptance.py -v           # Acceptance criteria

# Single test
python -m pytest tests/test_agent.py::TestBQTool::test_generate_sql_top_products -v
```

### Test Structure

| File | Type | What it tests |
|------|------|---------------|
| [`test_agent.py`](tests/test_agent.py) | Unit | System prompts, SQL generation, tool configs |
| [`test_stream_assist.py`](tests/test_stream_assist.py) | Unit + Integration | StreamAssist client, response parsing, error handling |
| [`test_discovery_engine.py`](tests/test_discovery_engine.py) | Integration | Discovery Engine SearchService directly (SOP + brand stores) |
| [`test_agent_engine.py`](tests/test_agent_engine.py) | Integration | Deployed ADK agent via Agent Engine REST API |
| [`test_bigquery.py`](tests/test_bigquery.py) | Integration | Schema existence, data quality, forbidden name checks |
| [`test_acceptance.py`](tests/test_acceptance.py) | Integration | 3 acceptance criteria via StreamAssist (greeting, SOP, brand) |

**Current status: 53/53 tests passing**

---

## Repository Structure

```
ge_grocery_store/
├── config/
│   └── settings.yaml              # All retailer-specific config (see Configuration)
├── infra/
│   ├── provision_engine.sh        # Create Discovery Engine app
│   ├── provision_datastore.sh     # Create + populate data stores
│   ├── upload_assets.sh           # Upload PDFs to GCS
│   └── bigquery/
│       ├── create_schema.sql      # Star schema DDL
│       └── seed_data.sql          # 12K+ synthetic transactions
├── src/
│   ├── client/
│   │   └── stream_assist.py       # StreamAssist REST API client
│   ├── agent/
│   │   ├── agent.py               # Root agent + sub-agents (ADK)
│   │   ├── .env                   # Agent Engine deployment env vars
│   │   ├── requirements.txt       # Agent Engine dependencies
│   │   ├── tools/
│   │   │   ├── bq_tool.py         # BigQuery analytics FunctionTool
│   │   │   ├── image_gen_tool.py  # Imagen product image FunctionTool
│   │   │   └── sop_tool.py        # SOP data store helper
│   │   └── prompts/
│   │       └── system_prompts.py  # Retailer-agnostic instructions
│   └── docs_gen/
│       ├── sop_generator.py       # Frontline SOP PDF generator
│       ├── brand_guidelines.py    # Brand guide PDF generator
│       ├── strategy_report.py     # Q4 strategy report generator
│       ├── analyst_report.py      # Industry analysis generator
│       └── marketing_assets.py    # Marketing layout generator
├── data/
│   ├── brand_guidelines/          # Generated brand guide PDFs
│   ├── sops/                      # Generated SOP PDFs
│   └── templates/                 # Report template PDFs
├── tests/                         # 53 tests (see Testing)
├── pyproject.toml                 # Python project config
└── README.md                      # This file
```
