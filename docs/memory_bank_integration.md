# Vertex AI Memory Bank Integration

This document explains how Vertex AI Memory Bank is integrated into the grocery retail assistant agents to provide user-scoped memory persistence across sessions.

## Overview

**Vertex AI Memory Bank** is a managed service that automatically:
- Extracts salient memories from agent-user conversations
- Stores memories scoped by `user_id`
- Recalls relevant memories when a new session starts
- Shares memories across different agents for the same user

## Architecture

### Memory Service Configuration

All three agent subsystems use Memory Bank:

1. **Main ADK Agent** (`src/agent/`)
   - Root `grocery_assistant` with analytics and image sub-agents
   - Memory service configured in `src/agent/app.py`
   - Uses agent_engine_id: `3323818153208709120`

2. **MCP Agent** (`src/mcp_agent/`)
   - BigQuery analytics agent using MCP Toolbox
   - Memory service configured in `src/mcp_agent/app.py`
   - Uses agent_engine_id: `8287066417547706368`

3. **Simulator Agent** (`src/simulator_agent/`)
   - Shopper simulation orchestrator
   - Memory service configured in `src/simulator_agent/app.py`
   - Uses agent_engine_id: `2103624129168015360`

### Memory Sharing

All agents use the **same project and location** (`wortz-project-352116`, `us-central1`), enabling memory sharing across agents for the same `user_id`:

- User asks main agent: "I work at the Downtown Market store"
  → Memory Bank stores: `user.preferred_store = "Downtown Market"`

- Later, user asks MCP agent: "Show me sales for my store"
  → Memory Bank recalls: `user.preferred_store = "Downtown Market"`
  → MCP agent queries data for Downtown Market specifically

## Implementation Details

### App.py Pattern

Each agent directory has an `app.py` that:

1. Loads config from `config/settings.yaml`
2. Creates memory service based on `config["memory"]["enabled"]`
3. Instantiates `VertexAiMemoryBankService` for production
4. Falls back to `InMemoryMemoryService` for local dev
5. Creates `App` instance with the agent and memory service

Example from `src/agent/app.py`:

```python
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService, InMemoryMemoryService

def _create_memory_service():
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

app = App(agent=create_agent(), memory_service=_create_memory_service())
```

### Memory Tool

The main agent includes `PreloadMemoryTool` in `src/agent/agent.py`:

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
root_tools.append(PreloadMemoryTool())
```

This tool:
- Automatically executes for each LLM request
- Queries Memory Bank for relevant memories for the current user
- Injects memories into the agent's context
- Is never called directly by the model

### System Prompt

The main agent's system prompt (`src/agent/prompts/system_prompts.py`) includes memory guidance:

```
5. **Memory & Personalization** — You have access to a memory bank that persists across
   sessions. When memories are loaded at the start of a conversation, use them to personalize
   responses. Note user preferences discovered during conversation (e.g., preferred store,
   role, frequently asked topics) so they can be recalled in future sessions.
```

## Configuration

### Config File (`config/settings.yaml`)

```yaml
memory:
  enabled: true
  location: "us-central1"   # Must match Agent Engine region
```

### Environment Variables

For Agent Engine deployment, memory configuration can be overridden:

```bash
export MEMORY_ENABLED=true
export MEMORY_LOCATION=us-central1
```

## User ID Handling

Memory Bank requires a consistent `user_id` to scope memories to individual users.

### Local Development

When running `adk web` locally, sessions automatically get a session ID. For user-scoped memory across multiple local sessions:

```python
from google.adk import Session

# Create session with explicit user_id
session = Session(user_id="john.doe@example.com")
```

### Production (Agent Engine)

When deployed to Agent Engine, the `user_id` comes from:
1. Request metadata (if provided by frontend)
2. Authenticated user email (if using IAP/OAuth)
3. Session ID (if no user auth available)

The frontend proxy (`src/frontend/server.py`) should be updated to pass user identifiers in requests to Agent Engine.

## Testing

### Unit Tests

Tests verify memory service configuration:

```bash
# Test memory service creation
python -m pytest tests/test_agent.py::TestMemoryBank -v

# Test MCP agent memory integration
python -m pytest tests/test_mcp_agent.py::TestMemoryBankIntegration -v
```

### Integration Tests

To test memory recall across sessions:

1. Start agent locally:
   ```bash
   cd src/agent && adk web
   ```

2. First conversation:
   ```
   User: I'm a store manager at Downtown Market
   Agent: [uses PreloadMemoryTool to store this preference]
   ```

3. New session, same user:
   ```
   User: What were my sales this week?
   Agent: Based on your role as store manager at Downtown Market... [recalls memory]
   ```

## Deployment

Memory Bank is automatically available when deploying to Agent Engine:

```bash
cd src && adk deploy agent_engine \
  --project=wortz-project-352116 \
  --region=us-central1 \
  --staging_bucket=gs://wortz-project-352116-ge-workshop \
  --display_name="Grocery Retail Assistant" \
  --trace_to_cloud \
  agent
```

### Prerequisites

1. **API Enabled**: `aiplatform.googleapis.com` (already enabled for Agent Engine)
2. **IAM Permissions**: Agent Engine service account already has required permissions
3. **No additional setup**: Memory Bank is part of Agent Engine infrastructure

## Memory Lifecycle

### Storage

Memories are **automatically extracted** by Memory Bank from conversation turns. The agent doesn't need to explicitly call a "store memory" function. The LLM's responses naturally inform what gets stored.

### Recall

Memories are **automatically injected** into the agent's context at the start of each session via `PreloadMemoryTool`. The agent sees them as part of the system context.

### Scoping

- **Per user**: Memories are scoped by `user_id`
- **Cross-agent**: Same user can access memories across all agents (main, MCP, simulator)
- **Cross-session**: Memories persist indefinitely across sessions

### Privacy

- Memories are stored in Vertex AI Memory Bank (Google Cloud managed service)
- Data residency follows the configured `location` (us-central1)
- Access controlled by IAM policies on the project
- Memories are scoped per user — no cross-user leakage

## Troubleshooting

### Memory Not Recalled

**Symptom**: Agent doesn't remember information from previous sessions

**Checks**:
1. Verify `config["memory"]["enabled"]` is `true`
2. Check that `PreloadMemoryTool` is in the agent's tools list
3. Ensure `user_id` is consistent across sessions
4. Verify Memory Bank API is accessible (check ADK logs)

### Fallback to InMemoryMemoryService

**Symptom**: Warning log: "Falling back to InMemoryMemoryService"

**Causes**:
- Running locally without GCP credentials
- Memory Bank API not enabled (should be enabled with Agent Engine)
- IAM permissions issue (unlikely if Agent Engine works)

**Expected**: This is normal for local development. Use `gcloud auth application-default login` if you want to test Memory Bank locally.

### Memory Leakage Across Users

**Symptom**: User sees memories from another user

**Cause**: `user_id` not set or inconsistent

**Fix**: Ensure sessions are created with explicit `user_id` parameter

## References

- [Vertex AI Memory Bank Overview](https://cloud.google.com/agent-builder/agent-engine/memory-bank/overview)
- [ADK Memory Integration](https://google.github.io/adk-docs/sessions/memory/#vertex-ai-memory-bank)
- [Agent Engine Documentation](https://cloud.google.com/agent-engine/docs)
