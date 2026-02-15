# Vertex AI Memory Bank - Quick Start Guide

## For Developers

### What Is It?

Memory Bank automatically remembers user preferences, context, and history across sessions. Users don't need to repeat themselves.

**Example:**
```
Session 1:
User: "I work at the Downtown Market store"
Agent: "Got it, you work at Downtown Market"

Session 2 (later):
User: "Show me this week's sales"
Agent: "Here are sales for Downtown Market..." [automatically recalls store]
```

## How It Works

### 1. Memory Storage (Automatic)
- Agent conversations are analyzed by Memory Bank
- Salient facts extracted (user's store, role, preferences)
- Stored scoped to `user_id`

### 2. Memory Recall (Automatic)
- `PreloadMemoryTool` runs at start of each session
- Queries Memory Bank for relevant memories
- Injects them into agent context

### 3. Cross-Agent Sharing
All agents (main, MCP, simulator) share the same Memory Bank:
- Tell main agent your preference → MCP agent remembers it
- No need to repeat information across agents

## Configuration

### Enable/Disable Memory

Edit `/config/settings.yaml`:

```yaml
memory:
  enabled: true          # Set to false to disable
  location: "us-central1"  # Must match Agent Engine region
```

### Environment Variable Override

```bash
export MEMORY_ENABLED=false  # Disable for testing
export MEMORY_LOCATION=us-central1
```

## Testing Locally

### With GCP Credentials (Memory Bank)

```bash
# Authenticate
gcloud auth application-default login

# Run agent
cd src/agent && adk web
```

Agent will use `VertexAiMemoryBankService` and persist memories to Vertex AI.

### Without Credentials (In-Memory)

```bash
# Run agent
cd src/agent && adk web
```

Agent falls back to `InMemoryMemoryService`:
- Memories stored in process memory
- Lost when agent restarts
- Good for development/testing

## Deployment

### Deploy with Memory Bank

```bash
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent
```

Memory Bank is automatically available on Agent Engine (no extra config needed).

## User ID Best Practices

### For Production
Use authenticated email:
```python
user_id = authenticated_user.email  # e.g., "john.doe@retailer.com"
```

### For Demo/Workshop
Use session cookie or query param:
```python
user_id = request.args.get('user_id', 'demo_user')
```

### Important
- **Same user ID = same memories**
- Different user ID = isolated memories
- Use consistent IDs across sessions for memory recall

## Code Structure

```
src/
├── agent/
│   ├── agent.py          # Agent definition (has PreloadMemoryTool)
│   └── app.py            # Memory service config ← NEW
├── mcp_agent/
│   ├── agent.py          # MCP agent definition
│   └── app.py            # Memory service config ← NEW
└── simulator_agent/
    ├── agent.py          # Simulator definition
    └── app.py            # Memory service config ← NEW
```

### Key Functions

#### Create Memory Service
```python
from src.agent.app import _create_memory_service

service = _create_memory_service()
# Returns VertexAiMemoryBankService or InMemoryMemoryService
```

#### Create Runner with Memory
```python
from src.agent.app import create_runner

runner = create_runner()
# Runner has memory_service configured
```

## Troubleshooting

### Memory Not Recalling

**Check:**
1. `config["memory"]["enabled"]` is `true`
2. `user_id` is consistent across sessions
3. Agent has `PreloadMemoryTool` in tools list
4. Memory Bank API is accessible (check logs)

### Fallback to InMemoryMemoryService

**Normal when:**
- Running locally without ADC credentials
- Memory Bank API temporarily unavailable
- Testing with `memory.enabled = false`

**Fix for production:**
```bash
gcloud auth application-default login
```

### Cross-User Memory Leakage

**Cause:** Inconsistent or missing `user_id`

**Fix:** Always set explicit `user_id` on session creation:
```python
session = Session(user_id="user@example.com")
```

## Testing

### Unit Tests
```bash
# Test memory service creation
pytest tests/test_agent.py::TestMemoryBank -v

# Test all memory integration
pytest tests/test_agent.py::TestMemoryBank tests/test_mcp_agent.py::TestMemoryBankIntegration -v
```

### Integration Test (Manual)

1. Start agent: `cd src/agent && adk web`
2. First session:
   ```
   User: "I'm a manager at Lakefront Market"
   Agent: [acknowledges]
   ```
3. End session
4. New session (same user_id):
   ```
   User: "What are my sales?"
   Agent: "Here are sales for Lakefront Market..." [recalls context]
   ```

## API Reference

### VertexAiMemoryBankService

```python
from google.adk.memory import VertexAiMemoryBankService

service = VertexAiMemoryBankService(
    project="wortz-project-352116",
    location="us-central1",
    agent_engine_id="3323818153208709120",  # Optional
)
```

### InMemoryMemoryService

```python
from google.adk.memory import InMemoryMemoryService

service = InMemoryMemoryService()
# Stores memories in process memory (ephemeral)
```

### PreloadMemoryTool

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

tool = PreloadMemoryTool()
# Automatically recalls memories at start of each LLM request
```

## Common Patterns

### Config-Based Toggle

```python
def _create_memory_service():
    from .agent import _load_config
    config = _load_config()

    if not config.get("memory", {}).get("enabled", True):
        return InMemoryMemoryService()

    try:
        return VertexAiMemoryBankService(
            project=config["project"]["id"],
            location=config["memory"]["location"],
        )
    except Exception as e:
        logger.warning(f"Falling back to InMemory: {e}")
        return InMemoryMemoryService()
```

### Runner with Memory

```python
from google.adk import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    agent=my_agent,
    app_name="my_app",
    session_service=InMemorySessionService(),
    memory_service=_create_memory_service(),
)
```

## FAQ

### Q: Do I need to redeploy agents?
**A:** Yes, for memory to work in production. Run `adk deploy agent_engine` for each agent.

### Q: Will memory slow down responses?
**A:** Minimal impact. PreloadMemoryTool runs concurrently with agent initialization.

### Q: Can users delete their memories?
**A:** Not currently exposed in the agent. Would need to implement via Memory Bank API.

### Q: How long are memories stored?
**A:** Indefinitely, until explicitly deleted or pruned via Memory Bank management.

### Q: Can I see what memories are stored?
**A:** Not directly in the agent. Use Memory Bank API or Cloud Console for inspection.

### Q: Does memory work with streaming responses?
**A:** Yes, memories are loaded before streaming starts.

### Q: What if Memory Bank is down?
**A:** Agent falls back to `InMemoryMemoryService` and continues working (without persistence).

## Learn More

- Full integration guide: `/docs/memory_bank_integration.md`
- Implementation summary: `/docs/MEMORY_BANK_IMPLEMENTATION_SUMMARY.md`
- [Vertex AI Memory Bank Docs](https://cloud.google.com/agent-builder/agent-engine/memory-bank/overview)
- [ADK Memory Docs](https://google.github.io/adk-docs/sessions/memory/)

---

**Quick Links:**
- Test memory: `pytest tests/test_agent.py::TestMemoryBank -v`
- Deploy agent: `cd src && adk deploy agent_engine ...`
- Check logs: Agent Engine console → Reasoning Engines → View logs
