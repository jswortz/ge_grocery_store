# Agent Evaluation Guide

Best practices and configuration for evaluating all deployed agents using the ADK evaluation framework.

---

## Table of Contents

1. [Overview](#overview)
2. [Evaluation Criteria](#evaluation-criteria)
3. [Agent-Specific Evaluations](#agent-specific-evaluations)
4. [Running Evaluations](#running-evaluations)
5. [Best Practices](#best-practices)
6. [User Simulation](#user-simulation)

---

## Overview

Each deployed agent has an evaluation suite in the `evals/` directory:

```
evals/
├── grocery_assistant/     # Root ADK agent (SOP, brand, analytics, images)
│   ├── eval_config.json
│   └── scenarios.json
├── mcp_analyst/           # MCP BigQuery agent
│   ├── eval_config.json
│   └── scenarios.json
├── simulator/             # Shopper simulation agent
│   ├── eval_config.json
│   └── scenarios.json
└── a2a_agent/             # A2A-enabled agent
    └── eval_config.json
```

Evaluations use the ADK evaluation framework (v1.18.0+) with user simulation for multi-turn conversations.

---

## Evaluation Criteria

### Available Criteria

| Criterion | When to Use | Our Agents |
|-----------|------------|------------|
| `tool_trajectory_avg_score` | Verify agents call the right tools in the right order | grocery_assistant, mcp_analyst |
| `response_match_score` | ROUGE-1 lexical comparison against reference | Quick regression checks |
| `final_response_match_v2` | LLM-judged semantic equivalence | All agents |
| `rubric_based_final_response_quality_v1` | Custom quality rubrics (tone, completeness) | simulator |
| `rubric_based_tool_use_quality_v1` | Evaluate tool usage quality | mcp_analyst |
| `hallucinations_v1` | Detect unsupported claims | All agents |
| `safety_v1` | Content safety screening | All agents |

### Choosing Criteria

- **Deterministic workflows** (SOP lookup): Use `tool_trajectory_avg_score` with `EXACT` match
- **Open-ended analytics**: Use `final_response_match_v2` with lower threshold (0.6)
- **Creative outputs** (image gen, simulation): Use `rubric_based_final_response_quality_v1`
- **Always include**: `hallucinations_v1` and `safety_v1` as baseline safety checks

---

## Agent-Specific Evaluations

### Grocery Assistant (Root Agent)

Tests the multi-agent orchestration — SOP retrieval, brand guidelines, analytics delegation, and image generation.

**Key scenarios:**
- SOP closing procedures (tests DiscoveryEngineSearchTool)
- Brand color guidelines (tests search + retrieval)
- Top products by revenue (tests transfer_to_agent to analytics)
- Product image generation (tests transfer_to_agent to image)
- Greeting and capabilities (tests general response quality)

**Tool trajectory match type:** `IN_ORDER` — verifies the agent calls search tools before analytics tools when appropriate.

### MCP BigQuery Analyst

Tests arbitrary SQL generation and schema exploration.

**Key scenarios:**
- Schema exploration (list_table_ids, get_table_info)
- Revenue analysis (execute_sql with JOINs)
- Customer segmentation (execute_sql with GROUP BY)
- Product performance (execute_sql with calculated fields)

**Tool trajectory match type:** `ANY_ORDER` — MCP tools can be called in any sequence.

### Shopper Simulator

Tests realistic shopping behavior and merchandising analysis.

**Rubric-based evaluation:**
- Realistic shopping path through aisles
- Cart stays within budget
- Endcap interactions are reported
- Aggregate metrics are calculated
- Recommendations are actionable

---

## Running Evaluations

### Prerequisites

```bash
pip install -e ".[dev]"
# ADK v1.18.0+ required for user simulation
```

### Run all evaluations

```bash
# Grocery assistant
adk eval src/agent --config_file_path evals/grocery_assistant/eval_config.json grocery_assistant_eval

# MCP analyst
adk eval src/mcp_agent --config_file_path evals/mcp_analyst/eval_config.json mcp_analyst_eval

# Simulator
adk eval src/simulator_agent --config_file_path evals/simulator/eval_config.json simulator_eval
```

### Create and populate EvalSets

```bash
# Create eval set
adk eval_set create src/agent grocery_assistant_eval

# Add scenarios
adk eval_set add_eval_case src/agent grocery_assistant_eval \
  --scenarios_file evals/grocery_assistant/scenarios.json
```

---

## Best Practices

### 1. Layer your evaluations

Run in order of speed and cost:
1. **Unit tests** (fast, no API calls): `python -m pytest tests/test_agent.py -v`
2. **Tool trajectory** (verify tool routing): Check agents call correct tools
3. **Response quality** (LLM-judged): Semantic evaluation of outputs
4. **Safety & hallucination**: Baseline safety checks
5. **User simulation** (multi-turn): Full conversation evaluation

### 2. Set appropriate thresholds

| Agent | Metric | Recommended Threshold |
|-------|--------|----------------------|
| grocery_assistant | `final_response_match_v2` | 0.7 |
| grocery_assistant | `tool_trajectory_avg_score` | 0.9 |
| mcp_analyst | `final_response_match_v2` | 0.6 (open-ended SQL) |
| simulator | rubric scores | 0.7 per rubric |

### 3. Use user simulation for multi-turn

Configure `user_simulator_config` with:
- `max_allowed_invocations`: 8-15 turns depending on complexity
- `model`: Use `gemini-3.0-flash` for speed, or a thinking model for complex scenarios
- Write `conversation_plan` that tests follow-up questions and edge cases

### 4. Test across scenarios

- Run the same eval with different merchandising scenarios (baseline vs seasonal)
- Test with different shopper personas
- Test edge cases: empty queries, ambiguous questions, out-of-scope requests

### 5. Monitor in production

- Use Agent Engine telemetry (OpenTelemetry) for production monitoring
- Track tool call patterns and response latencies
- Set up alerts for safety violations or high hallucination rates

---

## User Simulation

User simulation dynamically generates follow-up queries based on a `conversation_plan`, testing multi-turn agent behavior without hardcoded scripts.

### Scenario Format

```json
{
  "starting_prompt": "What are the closing procedures?",
  "conversation_plan": "After receiving the SOP, ask about safety checks. Then ask who signs off on the checklist."
}
```

### Configuration

```json
{
  "user_simulator_config": {
    "model": "gemini-3.0-flash",
    "max_allowed_invocations": 10
  }
}
```

The simulator model reads the `conversation_plan` and generates natural follow-up questions, simulating a real user interacting with the agent over multiple turns.
