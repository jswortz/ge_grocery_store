#!/usr/bin/env bash
# ============================================================
# Register ADK and A2A Agents on Discovery Engine (Gemini Enterprise)
# ============================================================
# Registers the deployed agents as agents on the Discovery Engine
# so they appear in the Gemini Enterprise agent gallery/selector.
#
# Prerequisites:
#   - Agents must be deployed to Agent Engine first
#   - A2A agent must be deployed to Cloud Run first
#   - gcloud CLI authenticated
#
# Usage:
#   bash infra/register_agents.sh
#
# Reference:
#   ADK: https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-adk-agent
#   A2A: https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

# Read config
PROJECT_ID=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['id'])")
PROJECT_NUMBER=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['number'])")
ENGINE_ID=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['engine_id'])")
AGENT_ENGINE_ID=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['agent_engine_id'])")
A2A_CLOUD_RUN_URL=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['a2a_cloud_run_url'])")

TOKEN=$(gcloud auth print-access-token)
BASE_URL="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${ENGINE_ID}/assistants/default_assistant/agents"

echo "=== Registering Agents on Discovery Engine ==="
echo "Project: ${PROJECT_ID}"
echo "Engine:  ${ENGINE_ID}"
echo ""

# ---- Step 1: Register ADK Agent (Agent Engine) ----
echo "--- Registering ADK Agent (Agent Engine) ---"
echo "Reasoning Engine: ${AGENT_ENGINE_ID}"

ADK_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Grocery Retail Agent",
    "description": "Full-featured AI assistant for ValueFresh Market. Powered by Gemini 3 Pro on Agent Engine with BigQuery analytics, SOP search, brand guidelines, image generation, shopper simulation, and cross-session memory.",
    "adkAgentDefinition": {
      "provisionedReasoningEngine": {
        "reasoningEngine": "projects/'"${PROJECT_NUMBER}"'/locations/us-central1/reasoningEngines/'"${AGENT_ENGINE_ID}"'"
      }
    },
    "state": "ENABLED",
    "sharingConfig": {
      "scope": "ALL_USERS"
    }
  }')

ADK_AGENT_ID=$(echo "${ADK_RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','').split('/')[-1])" 2>/dev/null || echo "FAILED")
echo "ADK Agent registered: ${ADK_AGENT_ID}"

# ---- Step 2: Register A2A Agent (Cloud Run) ----
echo ""
echo "--- Registering A2A Agent (Cloud Run) ---"
echo "Cloud Run URL: ${A2A_CLOUD_RUN_URL}"

# Fetch the AgentCard from Cloud Run
AGENT_CARD=$(curl -s "${A2A_CLOUD_RUN_URL}/.well-known/agent.json")

# Build the payload with the AgentCard
python3 -c "
import json

agent_card = json.loads('''${AGENT_CARD}''')
agent_card['url'] = '${A2A_CLOUD_RUN_URL}'

payload = {
    'displayName': 'Grocery A2A Agent',
    'description': 'A2A protocol agent for inter-agent communication. Provides grocery retail operations including SOP search, brand guidelines, BigQuery analytics, and image generation via Cloud Run.',
    'a2aAgentDefinition': {
        'jsonAgentCard': json.dumps(agent_card)
    },
    'state': 'ENABLED',
    'sharingConfig': {
        'scope': 'ALL_USERS'
    }
}

with open('/tmp/a2a_agent_reg.json', 'w') as f:
    json.dump(payload, f)
"

A2A_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d @/tmp/a2a_agent_reg.json)

A2A_AGENT_ID=$(echo "${A2A_RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name','').split('/')[-1])" 2>/dev/null || echo "FAILED")
echo "A2A Agent registered: ${A2A_AGENT_ID}"

# ---- Step 3: List all registered agents ----
echo ""
echo "=== All Registered Agents ==="
curl -s -X GET "${BASE_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for agent in d.get('agents', []):
    name = agent.get('name', '').split('/')[-1]
    display = agent.get('displayName', '?')
    state = agent.get('state', '?')
    if 'adkAgentDefinition' in agent:
        atype = 'ADK'
    elif 'a2aAgentDefinition' in agent:
        atype = 'A2A'
    elif 'managedAgentDefinition' in agent:
        atype = 'Managed'
    else:
        atype = 'Other'
    print(f'  {name}: {display} [{atype}] ({state})')
"

echo ""
echo "=== Registration Complete ==="
echo ""
echo "Update config/settings.yaml with:"
echo "  agent_id: \"${ADK_AGENT_ID}\""
echo "  a2a_agent_id: \"${A2A_AGENT_ID}\""
