# Traffic Simulator for Gemini Enterprise

Comprehensive synthetic traffic generator for the grocery retail Gemini Enterprise demo. Validates all deployed endpoints, populates telemetry, and detects integration deficiencies.

## Quick Start

```bash
# Run the full simulation
python -m src.simulator_agent.traffic_simulator

# The report will be automatically generated at:
# ./traffic_simulation_report.md
```

## What It Does

The simulator executes 5 phases of traffic generation:

### Phase 1: StreamAssist (Discovery Engine)
- Creates 17+ diverse sessions
- Sends SOP queries, brand guideline questions, conversational greetings, and multi-turn dialogs
- Tests context maintenance across follow-ups
- Rate-limited to ~1 query/second

### Phase 2: Agent Engine (ADK)
- Queries the main grocery assistant agent
- Tests analytics sub-agent, image generation, Discovery search
- Validates multi-agent routing

### Phase 3: MCP Agent (BigQuery)
- Sends natural language analytics queries
- Tests SQL generation, schema introspection, forecasting
- Validates MCP Toolbox integration

### Phase 4: A2A Agent (Cloud Run)
- Validates AgentCard endpoint
- Tests task execution protocol
- Checks skill discovery

### Phase 5: BigQuery Direct Validation
- Validates star schema integrity
- Checks row counts for all tables
- Verifies referential integrity
- Detects orphaned records and null foreign keys

## Configuration

The simulator reads all settings from `config/settings.yaml`:

```yaml
project:
  id: "wortz-project-352116"
  engine_id: "grocery-workshop-engine"
  agent_engine_id: "3323818153208709120"
  mcp_agent_engine_id: "8287066417547706368"
  a2a_cloud_run_url: "https://grocery-a2a-agent-in2bk2mdwa-uc.a.run.app"

bigquery:
  project: "wortz-project-352116"
  dataset: "ge_grocery_demo"
```

**No hardcoded retailer names.** All queries dynamically use `config["retailer"]["name"]`.

## Self-Healing Features

The simulator automatically:

1. **Retries transient errors** (429, 5xx) with exponential backoff
2. **Creates new sessions** if session errors occur
3. **Logs all failures** with detailed error messages
4. **Tracks self-healing actions** in the report
5. **Validates fixes** by re-running affected queries

**Note:** API contract mismatches (400 errors) are not retryable and will be reported as blocking issues.

## Output

### Console Output
Real-time logging of all queries:
```
[Phase 1: StreamAssist] Query: What is the procedure for opening the store?... | Success: True | Latency: 9226ms
```

### Markdown Report
Comprehensive report saved to `traffic_simulation_report.md`:
- Executive summary with key metrics
- Per-phase results with success rates and latencies
- Deficiency table with severity, component, and remediation
- Self-healing actions taken
- Telemetry confirmation
- Recommendations prioritized by urgency

## Expected Results (Healthy System)

| Phase | Sessions | Queries | Success Rate | Avg Latency |
|-------|----------|---------|--------------|-------------|
| StreamAssist | 17 | 20 | 100% | ~4s |
| Agent Engine | 0 | 13 | 100% | ~3s |
| MCP Agent | 0 | 9 | 100% | ~5s |
| A2A Agent | 0 | 3 | 100% | <2s |
| BigQuery | 0 | 8 | 100% | ~1s |

**Total:** 53 queries, <5 minutes duration

## Query Examples

### SOP Queries
- "What is the procedure for opening the store?"
- "How do I handle a customer complaint?"
- "What are the food safety guidelines for the deli department?"

### Brand Guidelines
- "What are our brand colors?"
- "How should the logo be displayed on signage?"
- "What font should be used for promotional materials?"

### Analytics
- "What are the top 5 selling products?"
- "Show me sales by store"
- "Which employees had the most transactions last month?"

### Multi-turn
1. "What is the store opening procedure?"
2. "What time should I arrive?"  *(follow-up in same session)*

## Authentication

Requires Google Cloud authentication with permissions for:
- `aiplatform.googleapis.com` (Agent Engine)
- `discoveryengine.googleapis.com` (StreamAssist)
- `bigquery.googleapis.com` (BigQuery validation)
- `run.googleapis.com` (A2A Cloud Run)

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project wortz-project-352116
```

## Known Limitations

1. **Agent Engine API Contract:** Current deployments use session-based methods and don't expose a direct `query()` method. The simulator detects this and reports it as a blocking issue.

2. **A2A Task Execution:** The Cloud Run service may only have the AgentCard endpoint implemented. The simulator tests `/execute` and reports if it's missing.

3. **Rate Limiting:** The simulator adds 0.8-2.0s delays between queries to avoid overwhelming endpoints. This makes the full run take ~3 minutes.

4. **Conversational Greetings:** StreamAssist may return empty responses for simple greetings like "Hello". This is expected behavior for task-oriented agents.

## Troubleshooting

### Authentication Errors (403)
```
AgentAuthorizationError: Agent requires OAuth authorization
```
**Solution:** Agent needs OAuth configuration. Check Agent Engine settings.

### Rate Limit Errors (429)
The simulator automatically retries with exponential backoff (up to 10 attempts).

### API Contract Errors (400)
```
Default method `query` not found
```
**Solution:** Agent Engine deployment needs a `query()` method wrapper. See report recommendations.

### Empty Responses
Check if the agent is configured correctly:
```bash
gcloud ai reasoning-engines describe <REASONING_ENGINE_ID> \
  --region=us-central1 \
  --project=wortz-project-352116
```

## Advanced Usage

### Custom Query Sets

Edit `traffic_simulator.py` to add custom queries:

```python
queries = {
    "Custom Category": [
        "Your custom query here",
        "Another custom query",
    ],
}
```

### Targeting Specific Phases

Comment out phases you don't want to run:

```python
def run(self):
    self.phase1_stream_assist_diversity()
    # self.phase2_agent_engine_adk()  # Skip this phase
    self.phase3_mcp_agent()
    # ... etc
```

### Adjusting Rate Limits

Change sleep times between queries:

```python
time.sleep(0.5)  # Faster (be careful of rate limits)
time.sleep(3.0)  # Slower (safer for production)
```

## Integration Testing

To use this as a recurring integration test:

```bash
# Add to CI/CD pipeline
python -m src.simulator_agent.traffic_simulator

# Check exit code
if [ $? -eq 0 ]; then
  echo "Simulation completed successfully"
else
  echo "Simulation failed - check logs"
  exit 1
fi
```

The simulator exits with code 0 on completion (even if issues are found). Parse the report markdown to detect deficiencies in CI/CD.

## Files

- `traffic_simulator.py` - Main simulator script
- `README.md` - This file
- `../traffic_simulation_report.md` - Generated report (in project root)

## Dependencies

```
google-auth
google-cloud-bigquery
requests
pyyaml
tenacity
```

All dependencies are in `pyproject.toml`.

## Contact

For issues or questions about the traffic simulator, refer to the main project documentation at `docs/architecture.md`.
