# Setup Guide

Step-by-step instructions for setting up the Gemini Enterprise Grocery Workshop.

> **Prerequisite**: All retailer-specific configuration is in [`config/settings.yaml`](../config/settings.yaml). Update it before proceeding if you're customizing for a different client.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [BigQuery Star Schema](#2-bigquery-star-schema)
3. [Document Generation](#3-document-generation)
4. [Discovery Engine Provisioning](#4-discovery-engine-provisioning)
5. [ADK Agent (Local)](#5-adk-agent-local)
6. [Agent Engine Deployment](#6-agent-engine-deployment)
7. [Frontend UI](#7-frontend-ui)
8. [MCP BigQuery Agent](#8-mcp-bigquery-agent)
9. [Running Tests](#9-running-tests)

---

## 1. Environment Setup

### Prerequisites

- Python 3.10+
- Google Cloud SDK (`gcloud`) authenticated
- Access to the GCP project (default: `wortz-project-352116`)
- APIs enabled: Discovery Engine, Vertex AI, BigQuery, IAM

### Install dependencies

```bash
# Clone the repo
git clone https://github.com/jswortz/ge_grocery_store.git
cd ge_grocery_store

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login
gcloud config set project wortz-project-352116
```

### Verify setup

```bash
# Run unit tests (no GCP access needed)
python -m pytest tests/test_agent.py tests/test_stream_assist.py tests/test_mcp_agent.py -v
```

---

## 2. BigQuery Star Schema

The workshop uses a star schema in BigQuery with synthetic grocery retail data. See [Architecture: Data Layer](architecture.md#data-layer) for schema details.

### Create dataset and tables

```bash
# Create the dataset
bq mk --dataset wortz-project-352116:ge_grocery_demo

# Create tables
bq query --use_legacy_sql=false < infra/bigquery/create_schema.sql

# Seed with synthetic data (12K+ transactions)
bq query --use_legacy_sql=false < infra/bigquery/seed_data.sql
```

### Verify

```bash
python -m pytest tests/test_bigquery.py -v
```

**Key files:**
- [`infra/bigquery/create_schema.sql`](../infra/bigquery/create_schema.sql) — DDL for all 5 tables
- [`infra/bigquery/seed_data.sql`](../infra/bigquery/seed_data.sql) — 12K+ synthetic transactions

---

## 3. Document Generation

Generate the PDF documents that get uploaded to Discovery Engine data stores.

```bash
# SOP documents (closing/opening procedures, safety checklists)
python -m src.docs_gen.sop_generator

# Brand guidelines (colors, typography, tone of voice)
python -m src.docs_gen.brand_guidelines

# Optional: additional workshop materials
python -m src.docs_gen.strategy_report
python -m src.docs_gen.analyst_report
python -m src.docs_gen.marketing_assets
```

Generated PDFs are written to:
- `data/sops/` — Standard Operating Procedures
- `data/brand_guidelines/` — Brand guidelines
- `data/templates/` — Report templates

**Key files:**
- [`src/docs_gen/sop_generator.py`](../src/docs_gen/sop_generator.py)
- [`src/docs_gen/brand_guidelines.py`](../src/docs_gen/brand_guidelines.py)

---

## 4. Discovery Engine Provisioning

Set up the Gemini Enterprise (Discovery Engine) app with data stores.

### Create the engine

```bash
bash infra/provision_engine.sh
```

This creates a Discovery Engine app (`grocery-workshop-engine`) with:
- Search tier: Enterprise
- App type: Intranet (internal use)
- Location: global

### Create data stores and ingest documents

```bash
# Create and populate data stores
bash infra/provision_datastore.sh

# Upload PDFs to GCS and trigger import
bash infra/upload_assets.sh
```

Data stores created:
- `sop-store` — GCS-backed, contains SOP PDFs
- `brand-guidelines-store` — GCS-backed, contains brand guide PDFs

### Verify

```bash
python -m pytest tests/test_discovery_engine.py -v
```

**Key files:**
- [`infra/provision_engine.sh`](../infra/provision_engine.sh) — Engine creation
- [`infra/provision_datastore.sh`](../infra/provision_datastore.sh) — Data store setup
- [`infra/upload_assets.sh`](../infra/upload_assets.sh) — Asset upload

---

## 5. ADK Agent (Local)

Run the multi-agent ADK agent locally for development and testing.

```bash
cd src/agent && adk web
```

This starts the ADK web UI at `http://localhost:8000` with:
- Root agent (`grocery_assistant`) with Discovery Engine search
- Analytics sub-agent with BigQuery tools
- Image generation sub-agent with Imagen

See [Architecture: Agent Layer](architecture.md#agent-layer) for the multi-agent design.

**Key files:**
- [`src/agent/agent.py`](../src/agent/agent.py) — Agent definitions
- [`src/agent/tools/bq_tool.py`](../src/agent/tools/bq_tool.py) — BigQuery tool
- [`src/agent/tools/image_gen_tool.py`](../src/agent/tools/image_gen_tool.py) — Image generation tool
- [`src/agent/prompts/system_prompts.py`](../src/agent/prompts/system_prompts.py) — System prompts

---

## 6. Agent Engine Deployment

Deploy the ADK agent to Vertex AI Agent Engine for production use.

```bash
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent
```

The deployment uses environment variables from [`src/agent/.env`](../src/agent/.env):
- `RETAILER_NAME`, `PROJECT_ID`, `ENGINE_ID` — Config overrides
- `BQ_PROJECT`, `BQ_DATASET` — BigQuery coordinates
- `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true` — OpenTelemetry

### Query the deployed agent

```python
import json, requests, google.auth
from google.auth.transport.requests import Request

credentials, _ = google.auth.default()
credentials.refresh(Request())

url = ("https://us-central1-aiplatform.googleapis.com/v1/"
       "projects/679926387543/locations/us-central1/"
       "reasoningEngines/3323818153208709120:streamQuery")

resp = requests.post(url,
    headers={"Authorization": f"Bearer {credentials.token}",
             "Content-Type": "application/json"},
    json={"input": {"message": "What are the closing procedures?",
                     "user_id": "demo-user"}})

for line in resp.text.strip().split("\n"):
    event = json.loads(line)
    for part in event.get("content", {}).get("parts", []):
        if "text" in part:
            print(part["text"])
```

### Verify

```bash
python -m pytest tests/test_agent_engine.py -v
```

---

## 7. Frontend UI

A branded web interface for interacting with the deployed agents.

```bash
# From project root
python -m src.frontend

# Opens at http://localhost:8080
```

The frontend provides:
- **StreamAssist mode** — Direct Discovery Engine queries (SOPs, brand guidelines)
- **Agent Engine mode** — Full agent orchestration (analytics, image gen, search)
- Branded ValueFresh Market design with green/gold color scheme
- Markdown rendering for agent responses
- Session management for Discovery Engine conversations

The server proxies API calls using Application Default Credentials, so no tokens are needed in the browser.

See [Architecture: Presentation Layer](architecture.md#presentation-layer) for details.

**Key files:**
- [`src/frontend/index.html`](../src/frontend/index.html) — Single-page chat application
- [`src/frontend/server.py`](../src/frontend/server.py) — Python proxy server

---

## 8. MCP BigQuery Agent

An alternative analytics agent using the MCP Toolbox for Databases.

### Prerequisites

Download the `genai-toolbox` binary:

```bash
export VERSION=0.27.0
curl -L -o toolbox \
  https://storage.googleapis.com/genai-toolbox/v$VERSION/linux/amd64/toolbox
chmod +x toolbox
```

### Run locally

```bash
cd src/mcp_agent && adk web
```

This agent connects to BigQuery via MCP (Model Context Protocol) instead of the pattern-matched SQL approach in the main agent's `bq_tool.py`. It lets the LLM generate arbitrary SQL queries through 9 BigQuery tools exposed by the toolbox.

See [Architecture: MCP Integration](architecture.md#mcp-integration) for the design.

**Key files:**
- [`src/mcp_agent/agent.py`](../src/mcp_agent/agent.py) — MCP-based agent
- [`src/mcp_agent/tools.yaml`](../src/mcp_agent/tools.yaml) — Toolbox configuration

### Verify

```bash
python -m pytest tests/test_mcp_agent.py -v
```

---

## 9. Running Tests

### Unit tests (no GCP needed)

```bash
python -m pytest tests/test_agent.py tests/test_stream_assist.py tests/test_mcp_agent.py -v
```

### Integration tests (requires provisioned resources)

```bash
# All integration tests
python -m pytest tests/ -v

# Specific suites
python -m pytest tests/test_discovery_engine.py -v    # Discovery Engine
python -m pytest tests/test_agent_engine.py -v         # Agent Engine
python -m pytest tests/test_bigquery.py -v             # BigQuery
python -m pytest tests/test_acceptance.py -v           # Acceptance criteria
```

### Single test

```bash
python -m pytest tests/test_agent.py::TestBQTool::test_generate_sql_top_products -v
```

See [README: Testing](../README.md#testing) for the full test matrix.
