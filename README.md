# Gemini Enterprise Grocery Workshop

A customer-facing workshop demonstrating **Gemini Enterprise** (powered by the Discovery Engine API) capabilities, advanced reasoning, and platform extensibility for grocery retail. Built on Google Cloud's agent platform with ADK, Agent Engine, Memory Bank, Model Armor, and A2A protocol. This repo is a reusable, retailer-agnostic resource — no client names are hardcoded anywhere.

**Documentation:**
- [Workshop Guide](docs/workshop_guide.md) — Hands-on walkthrough for potential Gemini Enterprise buyers
- [Workshop Slides](docs/slides/) — Customer-facing presentation deck
- [Setup Guide](docs/setup.md) — Step-by-step provisioning instructions
- [Architecture](docs/architecture.md) — System design, data flow, component details, and [diagrams](docs/diagrams/)
- [Evaluation Guide](docs/evaluation_guide.md) — Agent evaluation best practices and configuration

---

## Architecture Overview

This workshop integrates Google Cloud AI surfaces across multiple layers. See [docs/architecture.md](docs/architecture.md) for detailed diagrams.

![System Architecture](docs/diagrams/01_system_architecture.png)

| | |
|---|---|
| ![Frontend Chat](docs/img/22_frontend_adk_top_products.png) | ![Simulator](docs/img/24_frontend_simulator_personas.png) |
| *ADK agent: top products chart* | *Simulator: 12 shopper personas* |
| ![A2UI Products](docs/img/34_frontend_a2ui_products.png) | ![A2UI Stores](docs/img/36_frontend_a2ui_stores.png) |
| *A2UI: rich product cards* | *A2UI: store comparison dashboard* |
| ![Agent Engine](docs/img/10_gcp_agent_engine_list.png) | ![Cloud Trace](docs/img/12_gcp_cloud_trace_flow.png) |
| *Agent Engine: deployed agents* | *Cloud Trace: agent call flow* |

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Frontend Web UI** | [`src/frontend/`](src/frontend/) | Branded chat interface with StreamAssist + Agent Engine backends |
| **StreamAssist Client** | [`src/client/stream_assist.py`](src/client/stream_assist.py) | REST client for Discovery Engine `streamAssist` endpoint |
| **ADK Agent** | [`src/agent/agent.py`](src/agent/agent.py) | Multi-agent orchestrator deployed to [Agent Engine](#agent-engine-deployment) |
| **MCP Agent** | [`src/mcp_agent/agent.py`](src/mcp_agent/agent.py) | BigQuery analytics via [MCP Toolbox](#mcp-bigquery-agent) |
| **BQ Analytics Tool** | [`src/agent/tools/bq_tool.py`](src/agent/tools/bq_tool.py) | Pattern-matched SQL against star schema |
| **Image Gen Tool** | [`src/agent/tools/image_gen_tool.py`](src/agent/tools/image_gen_tool.py) | Vertex AI Imagen for brand-compliant product images |
| **System Prompts** | [`src/agent/prompts/system_prompts.py`](src/agent/prompts/system_prompts.py) | Config-driven, retailer-agnostic agent instructions |
| **Document Generators** | [`src/docs_gen/`](src/docs_gen/) | ReportLab PDF generators for SOPs, brand guides, reports |
| **Memory Bank** | Agent Engine built-in | Cross-session memory via `PreloadMemoryTool` (per-user preferences) |
| **Model Armor** | Discovery Engine config | Content safety screening (hate speech, PII, prompt injection) |
| **A2A Agent** | [`src/a2a_agent/`](src/a2a_agent/) | A2A-enabled agent deployed to Cloud Run |
| **Shopper Simulator** | [`src/simulator_agent/`](src/simulator_agent/) | World-model shopper simulation for endcap merchandising A/B testing |
| **Evaluations** | [`evals/`](evals/) | ADK evaluation suites with user simulation for all agents |
| **Infrastructure** | [`infra/`](infra/) | Shell scripts for Discovery Engine, BigQuery, and Model Armor provisioning |

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
python -m pytest tests/test_agent.py tests/test_stream_assist.py tests/test_mcp_agent.py tests/test_a2a_agent.py "tests/test_model_armor.py::TestModelArmorConfig" -v

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

# 7. Launch the frontend UI
python -m src.frontend    # http://localhost:8080
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
  agent_engine_id: "5752190188465946624"  # Deployed ADK agent
bigquery:
  project: "wortz-project-352116"
  dataset: "ge_grocery_demo"
```

---

## Frontend UI

A branded web interface for interacting with the deployed agents. See [Architecture: Presentation Layer](docs/architecture.md#presentation-layer).

```bash
python -m src.frontend    # http://localhost:8080
```

> **SSH port forwarding:** The Voice Ops tab uses a WebSocket server on port 8081. If you're accessing the frontend over SSH, forward both ports:
> ```bash
> ssh -L 8080:localhost:8080 -L 8081:localhost:8081 <remote-host>
> ```

Features:
- **Three tabs**: StreamAssist, Agent Engine & A2A, Voice Ops
- **Agent selector**: Dropdown to route StreamAssist queries to different registered agents
- **Voice input**: Gemini Live (Puck) via WebSocket with browser TTS fallback
- **Model Armor safety demo**: Interactive buttons demonstrating content safety filters
- **Memory Bank**: Cross-session memory with per-user tooltip showing memory count
- **Cloud Trace integration**: Deeplinks and latency/tool-count metrics for Agent Engine
- ValueFresh Market branding (green/gold/white color scheme)
- Markdown rendering with inline image support for Gemini 3 Pro Image output
- Server-side proxy with Application Default Credentials (no tokens in browser)

The proxy server routes requests:
- `POST /api/stream-assist/sessions` → Discovery Engine sessions
- `POST /api/stream-assist/query` → Discovery Engine `streamAssist` (supports `assistant_id` routing)
- `GET /api/stream-assist/agents` → Discovery Engine `assistants` (list available agents)
- `POST /api/agent-engine/query` → Agent Engine `streamQuery`
- `POST /api/agent-engine/stream` → Agent Engine SSE streaming
- `GET /api/images/*` → GCS image proxy for generated product images
- `GET /api/memory/status` → Memory Bank memory count

### A2UI Rich Visual Output

The agent supports **A2UI (Agent-to-User Interface)** — an open protocol that lets agents emit declarative UI components rendered as interactive cards, dashboards, and layouts directly in the chat. When the LLM returns A2UI JSON alongside natural language, the frontend renders rich visual surfaces with interactive form controls.

Components used: `Card`, `Text`, `Row`, `Column`, `Tabs`, `List`, `Icon`, `Divider`, `Button`, `MultipleChoice`, `Slider`, `CheckBox`, `TextField`, `BarChart`, `LineChart`, `PieChart` — composed into product displays, tier breakdowns, store dashboards, simulation controls, and A/B test results.

**Welcome Screen — Config-Driven Sample Buttons with A2UI Badges**

![Welcome Screen](docs/img/46_a2ui_welcome_screen.png)
*Dynamic sample buttons route to specific agents. Gold `A2UI` pill badges indicate queries that produce rich visual output. Each button auto-selects the correct backend (StreamAssist vs Agent Engine) and target agent.*

**Top Products — Bar Chart + Product Cards (MCP Analyst)**

| Chart View | Product Cards |
|:---:|:---:|
| ![Top Products Chart](docs/img/51_a2ui_top_products_chart.png) | ![Product Cards](docs/img/51_a2ui_top_products_cards.png) |
| *A2UI `BarChart` rendered via Chart.js showing top 5 products by quantity sold* | *Product `Card` grid with revenue, units, and margin badges* |

**Store Performance Dashboard (ADK Agent)**

![Store Performance](docs/img/47_a2ui_store_performance_top.png)
*Three store locations compared side-by-side in `Card` components. Each card shows daily revenue, transactions, average basket, and key characteristics. Color-coded badges highlight store type (Urban, Family, Premium).*

**Customer Lifetime Value by Loyalty Tier (MCP Analyst)**

| Tier Cards | Strategic Insights |
|:---:|:---:|
| ![CLTV Tiers](docs/img/48_a2ui_cltv_loyalty.png) | ![CLTV Insights](docs/img/48_a2ui_cltv_insights.png) |
| *Gold/Silver/Bronze loyalty tiers with CLV, visit frequency, and retention rates* | *Tier-specific optimization recommendations with conversion strategies* |

**Endcap A/B Comparison (Shopper Simulator)**

| Strategy Cards | Key Highlights & Recommendations |
|:---:|:---:|
| ![Endcap A/B](docs/img/49_a2ui_endcap_ab.png) | ![Endcap Insights](docs/img/49_a2ui_endcap_insights.png) |
| *Baseline vs Back-to-School strategies with conversion rates and revenue lift* | *Winner analysis with top-selling products and optimization recommendations* |

**Shopper Traffic Simulation (Simulator)**

| Simulation Results | Persona Breakdown |
|:---:|:---:|
| ![Shopper Sim](docs/img/50_a2ui_shopper_sim.png) | ![Shopper Personas](docs/img/50_a2ui_shopper_sim_bottom.png) |
| *5 simulated shoppers with Baseline vs Seasonal Produce Push comparison* | *Per-persona purchase behavior and endcap conversion analysis* |

**Interactive Simulation Control Center (A2UI Forms)**

A2UI form controls (`MultipleChoice`, `Slider`, `Button`) render as interactive elements. Users select stores, strategies, and shopper counts, then click "Run Simulation" — the button collects all form values and sends them as a structured prompt to the agent.

| KPI Dashboard + Tabs | Daily Side-by-Side Comparison |
|:---:|:---:|
| ![A2UI KPIs](docs/img/43_a2ui_simulator_ab_kpis.png) | ![Daily Comparison](docs/img/44_a2ui_simulator_daily_comparison.png) |
| *4 KPI cards (revenue, lift, conversion, ROI) with 4-tab layout* | *Baseline vs Back-to-School side-by-side for each day of the week* |

![A2UI Verdict](docs/img/45_a2ui_simulator_verdict.png)
*Trend chart with Unicode bar visualization and winner verdict card showing +44.7% revenue lift, 82.9% conversion, and projected annual incremental revenue across all stores.*

### Gemini Enterprise (Discovery Engine) — StreamAssist Backend

The StreamAssist tab uses the **Gemini Enterprise (Discovery Engine API)** backend for grounded search over SOPs, brand guidelines, and workspace data stores.

| SOP Search — Closing Procedures | Brand Guidelines — Typography |
|:---:|:---:|
| ![StreamAssist SOP](docs/img/52_ge_streamassist_sop.png) | ![StreamAssist Brand](docs/img/53_ge_streamassist_brand.png) |
| *Store closing procedures retrieved from SOP data store with structured steps* | *Brand color palette and typography table from brand guidelines data store* |

### E2E Playwright Screenshots

Automated high-resolution (3840x2160) captures from the Playwright E2E test suite, validating live agent responses across all backends.

| ADK Agent — KPI Dashboard | Simulator — A/B Endcap Comparison |
|:---:|:---:|
| ![ADK KPI Dashboard](docs/img/37_e2e_adk_kpi_dashboard.png) | ![Simulator A/B](docs/img/38_e2e_simulator_ab_comparison.png) |
| *Top products by revenue with A2UI cards and insights* | *Side-by-side endcap strategy comparison with Tabs* |

| MCP Agent — BigQuery Analytics | A2A Agent — Cross-Agent Response |
|:---:|:---:|
| ![MCP Analytics](docs/img/39_e2e_mcp_analytics.png) | ![A2A Response](docs/img/41_e2e_a2a_response.png) |
| *Revenue by store via MCP Toolbox for Databases* | *A2A protocol agent on Cloud Run* |

| StreamAssist — SOP Response | Full UI Overview |
|:---:|:---:|
| ![StreamAssist SOP](docs/img/40_e2e_streamassist_sop.png) | ![UI Overview](docs/img/42_e2e_ui_overview.png) |
| *Store closing procedures via Discovery Engine* | *Welcome screen with agent selector and branded UI* |

---

## ADK Agent Architecture

The agent uses a **multi-agent architecture** with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) running on the **Gemini 3 model family**. See [Architecture: Agent Layer](docs/architecture.md#agent-layer) for full details.

![Agent Architecture](docs/diagrams/02_agent_architecture.png)

### Gemini 3 Model Regime

| Model | Role | Used By |
|-------|------|---------|
| `gemini-2.5-pro` | Orchestration, complex reasoning | Root agent, MCP agent, Simulator |
| `gemini-2.5-flash` | Fast sub-agent tasks | analytics_agent, image_agent |
| `gemini-2.0-flash` | Native image generation | image_gen_tool |

### Agent Capabilities

The root `grocery_assistant` agent (Gemini 3 Pro) orchestrates:
- **Document search** — SOPs and brand guidelines via `DiscoveryEngineSearchTool`
- **Analytics** — BigQuery queries via `analytics_agent` sub-agent (Gemini 3 Flash)
- **Image generation** — Brand-compliant product images via `image_agent` sub-agent (Gemini 3 Flash)
- **Shopper simulation** — Endcap merchandising A/B testing via `delegate_to_simulator` → Simulator Agent Engine
- **Memory** — Cross-session user preferences via `PreloadMemoryTool` → Memory Bank

**Why `DiscoveryEngineSearchTool` instead of `VertexAiSearchTool`?**

`VertexAiSearchTool` adds a built-in Gemini retrieval tool that cannot coexist with the `transfer_to_agent` function tools injected by sub-agents. `DiscoveryEngineSearchTool` is a `FunctionTool` subclass that wraps the Discovery Engine SearchService REST API as a regular function tool, avoiding this conflict. See [`src/agent/agent.py`](src/agent/agent.py) for the implementation.

---

## MCP BigQuery Agent

An alternative analytics agent using the [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox). See [Architecture: MCP Integration](docs/architecture.md#mcp-integration).

![MCP Integration](docs/diagrams/05_mcp_integration.png)

Unlike the main agent's `bq_tool.py` (pattern-matched SQL), the MCP agent lets the LLM generate arbitrary SQL through 9 BigQuery tools (`execute_sql`, `list_table_ids`, `get_table_info`, `forecast`, etc.).

```bash
# Download the toolbox binary
export VERSION=0.27.0
curl -L -o toolbox \
  https://storage.googleapis.com/genai-toolbox/v$VERSION/linux/amd64/toolbox
chmod +x toolbox

# Run locally
cd src/mcp_agent && adk web
```

Key files:
- [`src/mcp_agent/agent.py`](src/mcp_agent/agent.py) — Agent with `McpToolset` + `StdioServerParameters`
- [`src/mcp_agent/tools.yaml`](src/mcp_agent/tools.yaml) — Toolbox configuration
- [`tests/test_mcp_agent.py`](tests/test_mcp_agent.py) — 34 unit tests

---

## Memory Bank

Memory Bank enables cross-session memory so the agent remembers user preferences and past interactions. See [Architecture: Memory Bank](docs/architecture.md#memory-bank).

- `PreloadMemoryTool` automatically loads relevant memories at the start of each turn
- Memories are scoped per `user_id` — each browser gets a unique persistent ID via `localStorage`
- No separate provisioning needed — Memory Bank is built into Agent Engine

## Model Armor

Model Armor screens prompts and responses for harmful content on the Discovery Engine. See [Architecture: Model Armor](docs/architecture.md#model-armor).

Filters: RAI harm, prompt injection/jailbreak, PII (SDP), malicious URIs.

```bash
# Provision Model Armor template and enable on engine
bash infra/provision_model_armor.sh
```

---

## A2A Agent (Cloud Run)

An A2A-enabled version of the grocery agent for inter-agent communication and Cloud Run deployment. See [`src/a2a_agent/`](src/a2a_agent/) for implementation details.

```bash
# Local development
python -m src.a2a_agent

# Deploy to Cloud Run
bash src/a2a_agent/deploy_to_cloud_run.sh
```

The agent exposes:
- `GET /.well-known/agent.json` — AgentCard with capabilities
- `POST /a2a` — A2A task execution endpoint

Key files:
- [`src/a2a_agent/agent.py`](src/a2a_agent/agent.py) — Agent definition + AgentCard
- [`src/a2a_agent/server.py`](src/a2a_agent/server.py) — A2A server (uvicorn)
- [`src/a2a_agent/Dockerfile`](src/a2a_agent/Dockerfile) — Cloud Run container
- [`src/a2a_agent/deploy_to_cloud_run.sh`](src/a2a_agent/deploy_to_cloud_run.sh) — Deployment script

---

## Shopper Simulator

A world-model simulation agent that simulates shoppers walking store aisles and building carts. Evaluates endcap merchandising placement strategies. Accessible from the main agent via the `delegate_to_simulator` tool.

![Simulator Architecture](docs/diagrams/09_simulator_architecture.png)

```bash
# Local development
cd src/simulator_agent && adk web

# Deploy to Agent Engine
python -m src.simulator_agent.deploy_to_agent_engine
```

**Features:**
- 12 shopper personas (budget family, health enthusiast, quick-stop, weekend cook, elderly regular, etc.)
- 3 store layouts (Downtown, Westside, Lakefront Market)
- 4 merchandising scenarios (baseline, seasonal produce, snack impulse, health wellness)
- Concurrent sub-agent simulation with persona-specific decision making
- Aggregate metrics: endcap conversion rate, incremental revenue, ROI
- Integrated with main agent — ask "Simulate 5 shoppers at Downtown Market" in the frontend

Key files:
- [`src/simulator_agent/agent.py`](src/simulator_agent/agent.py) — Orchestrator + shopper agents
- [`src/simulator_agent/scenarios/`](src/simulator_agent/scenarios/) — User simulation scenarios
- [`evals/simulator/`](evals/simulator/) — Evaluation config

---

## Agent Engine Deployment

Four agents are deployed across **Vertex AI Agent Engine** and **Cloud Run**:

| Agent | Platform | Resource ID | Purpose |
|-------|----------|-------------|---------|
| Grocery Retail Assistant | Agent Engine | `5752190188465946624` | Main multi-agent orchestrator |
| MCP Grocery Analyst | Agent Engine | `6529624074140778496` | BigQuery analytics via MCP Toolbox |
| Shopper Simulator | Agent Engine | `6121485357910327296` | Endcap merchandising A/B simulation |
| A2A Agent | Cloud Run | `grocery-a2a-agent` | A2A protocol inter-agent communication |

All Agent Engine deployments have OpenTelemetry tracing enabled for Cloud Trace observability.

```bash
# Deploy main agent (from project root)
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent

# Deploy MCP agent
python -m src.mcp_agent.deploy_to_agent_engine

# Deploy Simulator agent
python -m src.simulator_agent.deploy_to_agent_engine

# Deploy A2A agent to Cloud Run
bash src/a2a_agent/deploy_to_cloud_run.sh
```

The deployment uses environment variables from [`src/agent/.env`](src/agent/.env) for config overrides (retailer name, project ID, engine ID, BigQuery coordinates) and OpenTelemetry instrumentation.

**Query the deployed agent:**

```python
import json, requests, google.auth
from google.auth.transport.requests import Request

credentials, _ = google.auth.default()
credentials.refresh(Request())

url = ("https://us-central1-aiplatform.googleapis.com/v1/"
       "projects/679926387543/locations/us-central1/"
       "reasoningEngines/5752190188465946624:streamQuery")

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

---

## BigQuery Star Schema

Dataset `ge_grocery_demo` contains a retail analytics star schema. See [Architecture: Data Layer](docs/architecture.md#data-layer) for schema diagrams.

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
python -m pytest tests/test_agent.py tests/test_stream_assist.py tests/test_mcp_agent.py tests/test_a2a_agent.py "tests/test_model_armor.py::TestModelArmorConfig" -v

# All integration tests (requires gcloud auth + provisioned resources)
python -m pytest tests/ -v

# Specific test suites
python -m pytest tests/test_discovery_engine.py -v    # Discovery Engine search
python -m pytest tests/test_agent_engine.py -v         # Deployed Agent Engine
python -m pytest tests/test_bigquery.py -v             # BigQuery schema/data
python -m pytest tests/test_acceptance.py -v           # Acceptance criteria
python -m pytest tests/test_mcp_agent.py -v            # MCP agent unit tests

# Single test
python -m pytest tests/test_agent.py::TestBQTool::test_generate_sql_top_products -v
```

### Test Structure

| File | Type | Tests | What it tests |
|------|------|-------|---------------|
| [`test_agent.py`](tests/test_agent.py) | Unit | 53 | System prompts, SQL gen, tool configs, memory, voice, frontend, agent refactor, simulator scenario validation |
| [`test_stream_assist.py`](tests/test_stream_assist.py) | Unit + Integration | 14 + 1 | StreamAssist client, parsing, error handling, infra scripts |
| [`test_mcp_agent.py`](tests/test_mcp_agent.py) | Unit | 34 | MCP agent config, schema, instructions, toolbox path resolution |
| [`test_a2a_agent.py`](tests/test_a2a_agent.py) | Unit | 41 | A2A agent config, AgentCard, skills, Cloud Run files, model location, deployment config, simulator GE registration, report generator |
| [`test_frontend.py`](tests/test_frontend.py) | Unit | 52 | Compare-tab removal, Imagen labels, data-source toggle, agent selector, routing, voice, architecture panel, model card, thinking display, simulator labels, report endpoint |
| [`test_frontend_e2e.py`](tests/test_frontend_e2e.py) | Unit | 75 | Tabs, agent selector, data stores, voice ops, streaming, multi-turn, deployment scripts, E2E page load, API endpoints |
| [`test_evals.py`](tests/test_evals.py) | Unit | 40 | Eval config and scenario JSON structure for all eval directories |
| [`test_model_armor.py`](tests/test_model_armor.py) | Unit + Integration | 10 + 5 | Model Armor config, API schema, live template and assistant |
| [`test_discovery_engine.py`](tests/test_discovery_engine.py) | Integration | 4 | Discovery Engine SearchService against SOP and brand data stores |
| [`test_agent_engine.py`](tests/test_agent_engine.py) | Integration | 10 | Deployed ADK, MCP, Simulator, and A2A agents via Agent Engine REST API |
| [`test_bigquery.py`](tests/test_bigquery.py) | Integration | 12 | Schema existence, data quality, forbidden name checks |
| [`test_memory_bank.py`](tests/test_memory_bank.py) | Integration | 9 | Memory Bank service, user-scoped memory persistence |
| [`test_acceptance.py`](tests/test_acceptance.py) | Integration | 6 | Acceptance criteria via StreamAssist (greeting, SOP, brand) |
| [`test_e2e_streamassist.py`](tests/test_e2e_streamassist.py) | E2E | 9 | StreamAssist page load, data stores, SOP/brand queries, multi-turn, screenshots |
| [`test_e2e_adk.py`](tests/test_e2e_adk.py) | E2E | 10 | ADK Agent Engine selection, A2UI rendering (cards, rows), multi-turn, latency/trace metadata |
| [`test_e2e_simulator.py`](tests/test_e2e_simulator.py) | E2E | 8 | Simulator agent selection, A/B comparison tabs, retail term validation, multi-turn |
| [`test_e2e_a2a.py`](tests/test_e2e_a2a.py) | E2E | 7 | A2A Cloud Run agent selection, SOP/analytics queries, multi-turn |
| [`test_e2e_mcp.py`](tests/test_e2e_mcp.py) | E2E | 7 | MCP BigQuery agent schema/revenue queries, A2UI cards, forbidden name check |
| [`test_e2e_screenshots.py`](tests/test_e2e_screenshots.py) | E2E | 8 | Curated high-res (3840x2160) screenshot capture across all agents |

**Current status: 300 unit + 78 integration + 49 E2E = 427 total tests**

```bash
# Run all E2E tests (requires frontend: python -m src.frontend)
python -m pytest tests/test_e2e_*.py -v -m e2e

# Screenshot capture only
python -m pytest tests/test_e2e_screenshots.py -v -m e2e

# Single agent E2E
python -m pytest tests/test_e2e_adk.py -v -m e2e
```

---

## Repository Structure

```
ge_grocery_store/
├── config/
│   └── settings.yaml              # All retailer-specific config
├── docs/
│   ├── setup.md                   # Step-by-step setup guide
│   └── architecture.md            # System architecture documentation
├── infra/
│   ├── provision_engine.sh        # Create Discovery Engine app
│   ├── provision_datastore.sh     # Create + populate data stores
│   ├── provision_model_armor.sh   # Create Model Armor template + enable on engine
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
│   │   │   ├── image_gen_tool.py  # Gemini 3 Pro Image product image FunctionTool
│   │   │   └── a2a_tool.py        # Simulator delegation via Agent Engine streamQuery
│   │   └── prompts/
│   │       └── system_prompts.py  # Retailer-agnostic instructions
│   ├── mcp_agent/
│   │   ├── agent.py               # MCP-based BigQuery agent
│   │   ├── deploy_to_agent_engine.py  # Agent Engine deployment
│   │   ├── tools.yaml             # MCP Toolbox configuration
│   │   ├── .env                   # MCP agent env vars
│   │   └── requirements.txt       # MCP agent dependencies
│   ├── a2a_agent/
│   │   ├── agent.py               # A2A-enabled grocery agent
│   │   ├── server.py              # A2A server (uvicorn)
│   │   ├── Dockerfile             # Cloud Run container
│   │   ├── deploy_to_cloud_run.sh # Cloud Run deployment
│   │   └── requirements.txt       # A2A agent dependencies
│   ├── simulator_agent/
│   │   ├── agent.py               # Shopper simulator orchestrator
│   │   └── scenarios/             # User simulation scenarios
│   ├── frontend/
│   │   ├── index.html             # Branded chat UI (3 modes, agent selector, safety demo)
│   │   ├── server.py              # Python proxy server (StreamAssist + Agent Engine)
│   │   ├── voice_server.py        # WebSocket voice server (Gemini Live / ADK bidi streaming)
│   │   ├── __init__.py
│   │   └── __main__.py            # python -m src.frontend
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
├── evals/                         # ADK evaluation suites
│   ├── grocery_assistant/         # Root agent evals
│   ├── mcp_analyst/               # MCP agent evals
│   └── simulator/                 # Simulator evals
├── tests/                         # 378 tests (see Testing)
├── .github/workflows/
│   └── unit-tests.yml             # GitHub Actions CI
├── pyproject.toml                 # Python project config
└── README.md                      # This file
```
