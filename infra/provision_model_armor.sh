#!/usr/bin/env bash
# ============================================================
# provision_model_armor.sh
#
# Creates a Model Armor template and enables it on the
# Discovery Engine grocery-workshop-engine assistant.
#
# Prerequisites:
#   - gcloud auth login
#   - Model Armor API enabled:
#       gcloud services enable modelarmor.googleapis.com --project=PROJECT_ID
#   - IAM role roles/modelarmor.admin granted to your user
#   - Org policy allows us-central1 resource location
#     (constraints/gcp.resourceLocations must include us-central1)
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

# Model Armor uses 'us' multi-region to match the global Discovery Engine location.
# The regional endpoint (e.g., us-central1) cannot be applied to global assistants.
ARMOR_LOCATION="us"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "=== Model Armor Provisioning ==="
echo "Project:    $PROJECT_ID ($PROJECT_NUMBER)"
echo "Location:   $ARMOR_LOCATION"
echo "Template:   $TEMPLATE_ID"
echo "Engine:     $ENGINE_ID"
echo ""

# --- Step 0: Verify API is enabled --------------------------------
echo ">>> Checking Model Armor API is enabled..."
gcloud services list --enabled --project="$PROJECT_ID" --filter="name:modelarmor" --format="value(name)" | grep -q modelarmor || {
  echo "ERROR: Model Armor API not enabled. Run:"
  echo "  gcloud services enable modelarmor.googleapis.com --project=$PROJECT_ID"
  exit 1
}
echo "    Model Armor API is enabled."

# --- Step 1: Create Model Armor template --------------------------
echo ""
echo ">>> Creating Model Armor template: $TEMPLATE_ID ..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://modelarmor.${ARMOR_LOCATION}.rep.googleapis.com/v1/projects/${PROJECT_NUMBER}/locations/${ARMOR_LOCATION}/templates?templateId=${TEMPLATE_ID}" \
  -d '{
    "filterConfig": {
      "raiSettings": {
        "raiFilters": [
          {"filterType": "HATE_SPEECH", "confidenceLevel": "MEDIUM_AND_ABOVE"},
          {"filterType": "SEXUALLY_EXPLICIT", "confidenceLevel": "MEDIUM_AND_ABOVE"},
          {"filterType": "HARASSMENT", "confidenceLevel": "MEDIUM_AND_ABOVE"},
          {"filterType": "DANGEROUS", "confidenceLevel": "MEDIUM_AND_ABOVE"}
        ]
      },
      "piAndJailbreakFilterSettings": {
        "filterEnforcement": "ENABLED",
        "confidenceLevel": "MEDIUM_AND_ABOVE"
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
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
  echo "$BODY" | python3 -m json.tool
  echo ">>> Template created successfully."
elif echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('error',{}).get('code')==409 else 1)" 2>/dev/null; then
  echo "    Template already exists (409 CONFLICT). Continuing..."
else
  echo "ERROR creating template (HTTP $HTTP_CODE):"
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
  echo ""
  echo "Common issues:"
  echo "  - Org policy blocks us-central1: Update constraints/gcp.resourceLocations"
  echo "  - Missing IAM role: Grant roles/modelarmor.admin to your user"
  exit 1
fi

# --- Step 2: Enable Model Armor on Discovery Engine assistant ------
echo ""
echo ">>> Enabling Model Armor on engine: $ENGINE_ID ..."

TEMPLATE_PATH="projects/${PROJECT_NUMBER}/locations/${ARMOR_LOCATION}/templates/${TEMPLATE_ID}"

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
echo "Verify with:"
echo "  python -m pytest tests/test_model_armor.py -v"
