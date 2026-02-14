#!/usr/bin/env bash
# ============================================================
# provision_model_armor.sh
#
# Creates a Model Armor template and enables it on the
# Discovery Engine grocery-workshop-engine assistant.
#
# Prerequisites:
#   - gcloud auth login
#   - Model Armor API enabled on the project
#
# Usage:
#   bash infra/provision_model_armor.sh
# ============================================================
set -euo pipefail

# --- Config (read from settings.yaml via yq, with fallbacks) ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config/settings.yaml"

if command -v yq &> /dev/null && [ -f "$CONFIG_FILE" ]; then
  PROJECT_ID=$(yq -r '.project.id' "$CONFIG_FILE")
  ENGINE_ID=$(yq -r '.project.engine_id' "$CONFIG_FILE")
  TEMPLATE_ID=$(yq -r '.model_armor.template_id' "$CONFIG_FILE")
else
  PROJECT_ID="${PROJECT_ID:-wortz-project-352116}"
  ENGINE_ID="${ENGINE_ID:-grocery-workshop-engine}"
  TEMPLATE_ID="${TEMPLATE_ID:-grocery-workshop-armor}"
fi

LOCATION="us-central1"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "=== Model Armor Provisioning ==="
echo "Project:    $PROJECT_ID ($PROJECT_NUMBER)"
echo "Location:   $LOCATION"
echo "Template:   $TEMPLATE_ID"
echo "Engine:     $ENGINE_ID"
echo ""

# --- Step 1: Create Model Armor template --------------------------
echo ">>> Creating Model Armor template: $TEMPLATE_ID ..."

curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://modelarmor.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/templates?templateId=${TEMPLATE_ID}" \
  -d '{
    "filterConfig": {
      "raiSettings": {
        "raiFilterType": "RAI_FILTER_TYPE_HARM",
        "confidence": "MEDIUM_AND_ABOVE"
      },
      "piAndJailbreakFilterSettings": {
        "filterEnforcement": "ENABLED",
        "confidence": "MEDIUM_AND_ABOVE"
      },
      "sdpSettings": {
        "basicConfig": {
          "filterEnforcement": "ENABLED"
        }
      },
      "maliciousUriFilterSettings": {
        "filterEnforcement": "ENABLED"
      }
    }
  }' | python3 -m json.tool

echo ""
echo ">>> Template created."

# --- Step 2: Enable Model Armor on Discovery Engine assistant ------
echo ">>> Enabling Model Armor on engine: $ENGINE_ID ..."

TEMPLATE_PATH="projects/${PROJECT_NUMBER}/locations/${LOCATION}/templates/${TEMPLATE_ID}"

curl -s -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/${ENGINE_ID}/assistants/default_assistant?update_mask=customerPolicy" \
  -d "{
    \"customerPolicy\": {
      \"modelArmorConfig\": {
        \"userPromptTemplate\": \"${TEMPLATE_PATH}\",
        \"responseTemplate\": \"${TEMPLATE_PATH}\",
        \"failureMode\": \"FAIL_OPEN\"
      }
    }
  }" | python3 -m json.tool

echo ""
echo "=== Model Armor provisioning complete ==="
echo ""
echo "Template: ${TEMPLATE_PATH}"
echo "Applied to: ${ENGINE_ID}/assistants/default_assistant"
echo ""
echo "Test with a harmful query via StreamAssist to verify filtering."
