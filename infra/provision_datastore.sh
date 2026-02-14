#!/usr/bin/env bash
# ============================================================
# Provision Data Stores for Discovery Engine
# ============================================================
# Creates two data stores:
#   1. Brand Guidelines - for marketing content grounding
#   2. SOPs - for frontline associate procedure retrieval
#
# Prerequisites:
#   - Discovery Engine provisioned (see provision_engine.sh)
#   - PDFs generated (see src/docs_gen/)
#   - GCS bucket created for document storage
#
# Usage:
#   bash infra/provision_datastore.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

# Load config
PROJECT_ID=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['id'])")
LOCATION="global"
GCS_BUCKET=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['gcs']['bucket'])")

TOKEN=$(gcloud auth print-access-token)

if [ "${LOCATION}" = "global" ]; then
  API_ENDPOINT="https://discoveryengine.googleapis.com"
else
  API_ENDPOINT="https://${LOCATION}-discoveryengine.googleapis.com"
fi

BASE_URL="${API_ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection"

echo "=== Setting up GCS bucket ==="
gsutil mb -p "${PROJECT_ID}" -l US "gs://${GCS_BUCKET}" 2>/dev/null || echo "Bucket already exists"

echo "=== Uploading brand guidelines ==="
gsutil -m cp "${PROJECT_ROOT}/data/brand_guidelines/"*.pdf "gs://${GCS_BUCKET}/brand_guidelines/"

echo "=== Uploading SOPs ==="
gsutil -m cp "${PROJECT_ROOT}/data/sops/"*.pdf "gs://${GCS_BUCKET}/sops/"

echo "=== Uploading strategy documents ==="
gsutil -m cp "${PROJECT_ROOT}/data/templates/"*.pdf "gs://${GCS_BUCKET}/strategy_docs/"

# Create Brand Guidelines Data Store
echo ""
echo "=== Creating Brand Guidelines Data Store ==="
BRAND_DS_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}/dataStores?dataStoreId=brand-guidelines-store" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Brand Guidelines",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"]
  }')

echo "Brand DS response:"
echo "${BRAND_DS_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${BRAND_DS_RESPONSE}"

# Import brand guidelines documents
echo "Importing brand guidelines documents..."
curl -s -X POST \
  "${BASE_URL}/dataStores/brand-guidelines-store/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${GCS_BUCKET}"'/brand_guidelines/*"]
    },
    "reconciliationMode": "FULL"
  }' | python3 -m json.tool 2>/dev/null || true

# Create SOP Data Store
echo ""
echo "=== Creating SOP Data Store ==="
SOP_DS_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}/dataStores?dataStoreId=sop-store" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Standard Operating Procedures",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"]
  }')

echo "SOP DS response:"
echo "${SOP_DS_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${SOP_DS_RESPONSE}"

# Import SOP documents
echo "Importing SOP documents..."
curl -s -X POST \
  "${BASE_URL}/dataStores/sop-store/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${GCS_BUCKET}"'/sops/*"]
    },
    "reconciliationMode": "FULL"
  }' | python3 -m json.tool 2>/dev/null || true

echo ""
echo "=== Data Stores Provisioned ==="
echo "Brand Guidelines Store ID: brand-guidelines-store"
echo "SOP Store ID: sop-store"
echo ""
echo "Next steps:"
echo "  1. Wait for document import operations to complete"
echo "  2. Attach data stores to the engine in the GCP console"
echo "  3. Update config/settings.yaml with any additional IDs"
