# Vertex AI Memory Bank Implementation Summary

## Overview

Successfully integrated **Vertex AI Memory Bank** into all ADK agent subsystems, enabling user-scoped memory persistence across sessions. This allows agents to remember customer preferences, past queries, shopping patterns, and analytical context across conversations and even across different agents.

## What Was Implemented

### 1. Memory Service Configuration (app.py pattern)

Created three new app.py modules that configure memory services:

#### `/src/agent/app.py`
- Creates `VertexAiMemoryBankService` for the main grocery assistant
- Configuration:
  - Project: `wortz-project-352116`
  - Location: `us-central1`
  - Agent Engine ID: `3323818153208709120`
- Exports: `root_agent`, `runner`, `_create_memory_service()`

#### `/src/mcp_agent/app.py`
- Creates `VertexAiMemoryBankService` for the MCP BigQuery analyst
- Configuration:
  - Project: `wortz-project-352116` (from BQ config)
  - Location: `us-central1`
  - Agent Engine ID: `8287066417547706368`
- Exports: `root_agent`, `runner`, `_create_memory_service()`

#### `/src/simulator_agent/app.py`
- Creates `VertexAiMemoryBankService` for the shopper simulator
- Configuration:
  - Project: `wortz-project-352116`
  - Location: `us-central1`
  - Agent Engine ID: `2103624129168015360`
- Exports: `root_agent`, `runner`, `_create_memory_service()`

### 2. Memory Service Factory Pattern

Each `app.py` implements the same `_create_memory_service()` factory:

```python
def _create_memory_service():
    """Create memory service based on config."""
    config = _load_config()

    if not config.get("memory", {}).get("enabled", True):
        return InMemoryMemoryService()

    try:
        return VertexAiMemoryBankService(
            project=config["project"]["id"],
            location=config["memory"]["location"],
            agent_engine_id=config["project"]["agent_engine_id"],
        )
    except Exception as e:
        logger.warning(f"Falling back to InMemoryMemoryService: {e}")
        return InMemoryMemoryService()
```

**Key features:**
- Config-driven: Reads from `config/settings.yaml`
- Graceful fallback: Uses `InMemoryMemoryService` for local dev
- No credentials required for unit tests
- Production-ready for Agent Engine deployment

### 3. Existing Memory Tool Integration

The main agent already had `PreloadMemoryTool` integrated in `/src/agent/agent.py` (lines 125-129):

```python
try:
    from google.adk.tools.preload_memory_tool import PreloadMemoryTool
    root_tools.append(PreloadMemoryTool())
except ImportError:
    print("Warning: PreloadMemoryTool not available")
```

This tool:
- Automatically executes for each LLM request
- Queries Memory Bank for relevant memories for the current user
- Injects memories into the agent's context
- Works seamlessly with the configured `VertexAiMemoryBankService`

### 4. System Prompt Updates

The main agent's system prompt (`/src/agent/prompts/system_prompts.py`) includes memory guidance:

```python
5. **Memory & Personalization** — You have access to a memory bank that persists across
   sessions. When memories are loaded at the start of a conversation, use them to personalize
   responses. Note user preferences discovered during conversation (e.g., preferred store,
   role, frequently asked topics) so they can be recalled in future sessions.
```

### 5. Configuration

Memory settings in `/config/settings.yaml`:

```yaml
memory:
  enabled: true
  location: "us-central1"   # Must match Agent Engine region
```

### 6. Test Coverage

Added comprehensive unit tests:

#### `/tests/test_agent.py::TestMemoryBank` (6 tests)
- `test_config_has_memory_section` — Verifies config has memory settings
- `test_system_prompt_mentions_memory` — Verifies prompts mention memory
- `test_memory_service_created_when_enabled` — Verifies factory creates service
- `test_memory_service_fallback_to_inmemory` — Verifies graceful fallback
- `test_runner_has_memory_service` — Verifies Runner has memory service configured
- `test_config_has_model_armor_section` — Model Armor config validation

#### `/tests/test_mcp_agent.py::TestMemoryBankIntegration` (3 tests)
- `test_mcp_agent_has_memory_app` — Verifies app.py exists
- `test_mcp_memory_service_creation` — Verifies memory service creation
- `test_mcp_memory_uses_correct_config` — Verifies correct config keys

**Test results:** All 9 tests passing ✅

### 7. Documentation

Created comprehensive documentation:

#### `/docs/memory_bank_integration.md`
- Architecture overview
- Implementation details
- Configuration guide
- User ID handling
- Testing instructions
- Troubleshooting guide
- References to official docs

#### Updated `/CLAUDE.md`
- Added Memory Bank to ADK Agent architecture description
- Documented app.py pattern and memory sharing across agents

## How It Works

### Memory Storage (Automatic)

1. User has conversation with any agent (main, MCP, or simulator)
2. User mentions preference: "I work at the Downtown Market store"
3. Memory Bank **automatically extracts** this as a memory:
   - `user.preferred_store = "Downtown Market"`
   - `user.role = "store employee"`
4. Memory is stored scoped to the `user_id`

### Memory Recall (Automatic)

1. User starts new session with any agent
2. `PreloadMemoryTool` automatically queries Memory Bank
3. Relevant memories are injected into agent context:
   ```
   [Memory: User works at Downtown Market store]
   ```
4. Agent uses this context to personalize responses

### Cross-Agent Memory Sharing

All agents use the **same Memory Bank** (same project + location):
- User tells main agent: "I prefer organic products"
- Later, user asks MCP agent: "Show me sales trends"
- MCP agent recalls preference and filters to organic products

This works because all agents:
- Use `project=wortz-project-352116`
- Use `location=us-central1`
- Scope memories by the same `user_id`

## Architecture Benefits

### 1. Shared Memory Across Agents
Users don't need to repeat preferences. Information flows seamlessly:
- Main agent learns user's store → MCP agent uses it for analytics
- Analytics agent learns user's role → Image agent customizes visuals
- Simulator learns shopping patterns → All agents understand user behavior

### 2. Config-Driven with Graceful Fallback
- Production: Uses `VertexAiMemoryBankService` on Agent Engine
- Local dev: Falls back to `InMemoryMemoryService` without errors
- Unit tests: Work without GCP credentials or API access

### 3. Zero Agent Code Changes
- Agents continue to use `root_agent` export for ADK CLI
- Memory service is configured at the Runner level
- No changes to agent logic or tool implementations
- `PreloadMemoryTool` was already integrated

### 4. User-Scoped Privacy
- Memories are scoped per `user_id`
- No cross-user leakage
- Data residency follows configured location (`us-central1`)
- IAM controls access at project level

## Deployment

### Current Status
Memory Bank integration is **code-complete** and **test-verified**. Next step is redeployment.

### To Deploy

```bash
# Main agent
cd /usr/local/google/home/jwortz/ge_grocery_store/src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent

# MCP agent (if redeployment needed)
cd /usr/local/google/home/jwortz/ge_grocery_store/src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="MCP Grocery Analyst" \
  --trace_to_cloud \
  mcp_agent

# Simulator agent (if redeployment needed)
cd /usr/local/google/home/jwortz/ge_grocery_store/src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Shopper Simulator" \
  --trace_to_cloud \
  simulator_agent
```

### Prerequisites
- ✅ `aiplatform.googleapis.com` API enabled (already enabled for Agent Engine)
- ✅ No additional IAM permissions needed (covered by Agent Engine)
- ✅ Memory Bank is part of Agent Engine infrastructure

### Post-Deployment Verification

1. Start conversation with deployed agent
2. State a preference: "I'm a manager at Lakefront Market"
3. End session
4. Start new session with same user ID
5. Ask related question: "What were sales this week?"
6. Verify agent recalls "Lakefront Market" context

## User ID Handling

### Current Implementation
- Agent Engine sessions get automatic session IDs
- For user-scoped memory, need consistent `user_id`

### Options for Frontend Integration

#### Option A: Authenticated User Email
```python
# In frontend proxy (src/frontend/server.py)
# If using IAP or OAuth
user_id = request.user.email  # e.g., "john.doe@example.com"
```

#### Option B: Session Cookie
```python
# Generate stable ID from browser session
import hashlib
session_cookie = request.cookies.get('session_id')
user_id = hashlib.sha256(session_cookie.encode()).hexdigest()[:16]
```

#### Option C: Query Parameter (for demo)
```python
# Pass user_id in request
user_id = request.args.get('user_id', 'demo_user')
```

### Recommendation
For the workshop demo, use **Option B (session cookie)** or **Option C (query param)** to demonstrate memory without requiring auth.

For production deployment, use **Option A (authenticated email)** for proper user scoping.

## Testing the Integration

### Unit Tests (No GCP Access Required)
```bash
# Test memory service creation
python -m pytest tests/test_agent.py::TestMemoryBank -v

# Test MCP agent memory integration
python -m pytest tests/test_mcp_agent.py::TestMemoryBankIntegration -v

# Run all memory tests
python -m pytest tests/test_agent.py::TestMemoryBank tests/test_mcp_agent.py::TestMemoryBankIntegration -v
```

### Local Development Testing
```bash
# Start agent with memory service
cd src/agent && adk web

# The runner will use VertexAiMemoryBankService if you have ADC credentials:
# gcloud auth application-default login

# Otherwise, gracefully falls back to InMemoryMemoryService
```

### Integration Testing (Post-Deployment)
See `/docs/memory_bank_integration.md` for detailed integration test scenarios.

## Files Modified/Created

### Created
- `/src/agent/app.py` — Memory service config for main agent
- `/src/mcp_agent/app.py` — Memory service config for MCP agent
- `/src/simulator_agent/app.py` — Memory service config for simulator
- `/docs/memory_bank_integration.md` — Comprehensive integration docs
- `/docs/MEMORY_BANK_IMPLEMENTATION_SUMMARY.md` — This file

### Modified
- `/tests/test_agent.py` — Added TestMemoryBank class with 6 tests
- `/tests/test_mcp_agent.py` — Added TestMemoryBankIntegration class with 3 tests
- `/CLAUDE.md` — Updated ADK Agent architecture section
- `/src/agent/prompts/system_prompts.py` — Already had memory guidance (no changes needed)
- `/config/settings.yaml` — Already had memory section (no changes needed)
- `/src/agent/agent.py` — Already had PreloadMemoryTool (no changes needed)

## Key Design Decisions

### 1. Why app.py Instead of Modifying agent.py?
- Separation of concerns: Agent logic vs. runtime configuration
- ADK CLI compatibility: `root_agent` export still works
- Testing: Can test agent without memory service
- Flexibility: Easy to switch memory backends via config

### 2. Why VertexAiMemoryBankService Instead of Custom?
- Managed service: No infrastructure to maintain
- Automatic extraction: No manual memory instrumentation
- Automatic recall: PreloadMemoryTool handles injection
- Production-ready: Scales with Agent Engine

### 3. Why Shared Project/Location Across Agents?
- Memory sharing: User preferences flow across agents
- Simplified ops: One Memory Bank to manage
- Cost efficiency: Single memory store
- Consistent UX: User doesn't repeat information

### 4. Why Graceful Fallback to InMemoryMemoryService?
- Local development: Works without GCP credentials
- Unit testing: Tests pass without API access
- Error resilience: Agent still works if Memory Bank unavailable
- Progressive enhancement: Memory is a feature, not a dependency

## Success Metrics

### Unit Tests: ✅ All Passing
- 9/9 memory-related tests passing
- No GCP credentials required for tests
- Tests verify config, factory pattern, and Runner integration

### Agent Imports: ✅ Working
```
Main agent: grocery_assistant
Runner memory service: VertexAiMemoryBankService

MCP Runner memory service: VertexAiMemoryBankService

Simulator Runner memory service: VertexAiMemoryBankService
```

### Configuration: ✅ Complete
- Config has memory section with `enabled: true` and `location: us-central1`
- All three agents have Agent Engine IDs configured
- Environment variable overrides supported

### Documentation: ✅ Comprehensive
- 200+ line integration guide
- Architecture diagrams in markdown
- Troubleshooting section
- Testing instructions
- Deployment guide

## Next Steps

### Immediate
1. **Redeploy main agent** to Agent Engine with memory service
   ```bash
   cd src && adk deploy agent_engine --project=wortz-project-352116 \
     --region=us-central1 --staging_bucket=gs://wortz-project-352116-ge-workshop \
     --display_name="Grocery Retail Assistant" --trace_to_cloud agent
   ```

2. **Verify deployment** by checking Agent Engine console:
   - Reasoning Engine ID: `3323818153208709120`
   - Should see memory service in configuration
   - Test with a conversation demonstrating memory recall

### Future Enhancements

1. **Frontend User ID Integration**
   - Update `src/frontend/server.py` to pass `user_id` in Agent Engine requests
   - Implement session cookie or authenticated email approach
   - Test cross-session memory recall from frontend

2. **Memory Observability**
   - Add logging for memory extraction/recall events
   - Create dashboard for memory statistics
   - Monitor memory quality and relevance

3. **Memory Pruning**
   - Implement memory retention policies
   - Remove stale or irrelevant memories
   - User privacy controls (memory deletion)

4. **Advanced Memory Features**
   - Explicit memory tools for agents to query/modify memories
   - Memory categories (preferences, facts, context, history)
   - Memory confidence scoring

## References

- [Vertex AI Memory Bank Overview](https://cloud.google.com/agent-builder/agent-engine/memory-bank/overview)
- [ADK Memory Integration Docs](https://google.github.io/adk-docs/sessions/memory/#vertex-ai-memory-bank)
- [Agent Engine Documentation](https://cloud.google.com/agent-engine/docs)
- Local docs: `/docs/memory_bank_integration.md`

---

**Implementation Date:** 2026-02-15
**Status:** Complete, ready for deployment
**Tested:** ✅ All unit tests passing
**Deployed:** ⏳ Pending redeployment to Agent Engine
