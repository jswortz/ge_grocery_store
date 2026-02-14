# Gemini Enterprise Workshop Guide

A hands-on walkthrough of Gemini Enterprise capabilities for grocery retail, demonstrating how Google Cloud AI surfaces work together to solve real operational challenges.

---

## What This Workshop Demonstrates

This workshop showcases **six Gemini Enterprise capabilities** through a realistic grocery retail scenario:

| Capability | What It Does | Business Value |
|-----------|-------------|----------------|
| **Discovery Engine** | Enterprise search over SOPs and brand docs | Instant access to operational knowledge |
| **Agent Engine** | Multi-agent AI orchestration | Complex task automation across systems |
| **Memory Bank** | Cross-session user memory | Personalized experiences without re-explaining context |
| **Model Armor** | Content safety screening | Protects against harmful content, PII leaks, prompt injection |
| **A2A Protocol** | Agent-to-agent communication | Composable AI services across teams |
| **ADK Evaluation** | Agent testing and simulation | Confidence in AI quality before production |

---

## Workshop Flow

### Act 1: Knowledge Retrieval (Discovery Engine)

**Scenario:** A store associate needs to look up closing procedures.

**What happens:**
1. User asks: *"What are the closing procedures for frontline associates?"*
2. Discovery Engine searches the SOP data store (GCS-backed PDFs)
3. StreamAssist returns a grounded answer with citations

**Key feature:** Grounded responses with document citations — not hallucinated content.

**Try it:**
```bash
python -m src.frontend    # Open http://localhost:8080
# Use StreamAssist tab, ask about closing procedures
```

### Act 2: Multi-Agent Orchestration (Agent Engine)

**Scenario:** A manager wants sales analytics and brand-compliant marketing materials.

**What happens:**
1. User asks: *"What are the top 5 products by revenue?"*
2. Root agent routes to `analytics_agent` via `transfer_to_agent`
3. Analytics agent generates SQL, queries BigQuery, returns results
4. User asks: *"Generate a product image for Nano Banana Pro"*
5. Root agent routes to `image_agent`
6. Image agent creates brand-compliant imagery via Imagen

**Key feature:** Intelligent routing between specialized agents — each with its own tools.

**Try it:**
```bash
# Switch to Agent Engine tab in the frontend
# Ask analytics and image generation questions
```

### Act 3: Memory & Personalization (Memory Bank)

**Scenario:** A returning user expects the agent to remember their preferences.

**What happens:**
1. User (with persistent `user_id` from browser) mentions they work at Downtown Market
2. Memory Bank stores this preference
3. In a new session, the agent recalls: *"Based on your preference for the Downtown Market..."*

**Key feature:** Cross-session memory without explicit user login — just a browser-persistent ID.

### Act 4: Content Safety (Model Armor)

**Scenario:** Demonstrating protection against adversarial inputs.

**What happens:**
1. A harmful query is submitted via StreamAssist
2. Model Armor screens the prompt before it reaches Discovery Engine
3. The query is filtered; the user receives a safe response

**Filters active:**
- Hate speech / violence / sexual content (RAI)
- Prompt injection / jailbreak attempts
- PII detection (Sensitive Data Protection)
- Malicious URL blocking

**Key feature:** Applied at the Discovery Engine level — no code changes needed.

### Act 5: Agent-to-Agent Communication (A2A)

**Scenario:** An external agent discovers and invokes the grocery agent.

**What happens:**
1. External agent fetches `/.well-known/agent.json` (AgentCard)
2. Discovers capabilities: SOP lookup, analytics, image gen, brand guidelines
3. Sends a task via the `/a2a` endpoint
4. Receives structured results

**Key feature:** Composable AI services — any agent can discover and use this one.

### Act 6: Simulation & Evaluation

**Scenario:** Testing merchandising strategies before deploying in stores.

**What happens:**
1. Simulator creates concurrent shopper agents (different personas)
2. Each walks store aisles, encounters endcap displays
3. Orchestrator aggregates results: conversion rates, revenue impact, ROI
4. Compare baseline vs promotional scenarios

**Key feature:** AI-powered A/B testing of physical store layouts.

---

## Architecture at a Glance

![System Architecture](diagrams/01_system_architecture.png)

See the [full architecture documentation](architecture.md) for detailed diagrams of each layer.

---

## ROI Arguments for Gemini Enterprise

### 1. Operational Efficiency
- **SOPs accessible in seconds** — Associates no longer dig through paper binders
- **Self-service analytics** — Managers query sales data without SQL knowledge
- **Automated brand compliance** — Marketing content checked against guidelines automatically

### 2. Risk Reduction
- **Model Armor** prevents PII leaks, prompt injection, and harmful content at the API level
- **Grounded responses** with citations reduce hallucination risk
- **Evaluation framework** validates agent quality before production deployment

### 3. Scalability
- **Agent Engine** provides managed deployment with auto-scaling and telemetry
- **A2A protocol** enables composable agent services across departments
- **Memory Bank** personalizes experiences at scale without per-user infrastructure

### 4. Speed to Value
- **Config-driven design** — Switch retailers by changing one YAML file
- **Pre-built tools** — Discovery Engine search, BigQuery MCP, Imagen generation
- **ADK framework** — Multi-agent architecture out of the box

---

## Deployed Resources

| Resource | Type | ID |
|----------|------|-----|
| Discovery Engine | Search App | `grocery-workshop-engine` (global) |
| Agent Engine | Reasoning Engine | `3323818153208709120` (us-central1) |
| Model Armor | Template | `grocery-workshop-armor` (us-central1) |
| BigQuery | Dataset | `wortz-project-352116.ge_grocery_demo` |
| GCS | Bucket | `gs://wortz-project-352116-ge-workshop` |

---

## Test Coverage

| Suite | Tests | Type | What It Validates |
|-------|-------|------|-------------------|
| `test_agent.py` | 15 | Unit | System prompts, SQL gen, tool configs, memory, model armor |
| `test_stream_assist.py` | 14 | Unit | StreamAssist client, parsing, error handling |
| `test_mcp_agent.py` | 29 | Unit | MCP agent config, schema, instructions |
| `test_discovery_engine.py` | 4 | Integration | Discovery Engine search against live stores |
| `test_agent_engine.py` | 5 | Integration | Deployed agent via Agent Engine REST API |
| `test_bigquery.py` | 10 | Integration | BigQuery schema, data quality |
| `test_acceptance.py` | 8 | Integration | End-to-end acceptance criteria |

**GitHub Actions** runs unit tests on every push/PR across Python 3.10-3.12 with coverage reporting.
