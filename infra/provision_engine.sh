#!/usr/bin/env bash
# ============================================================
# Provision Discovery Engine (Gemini Enterprise) — Full Setup
# ============================================================
# Creates data stores, uploads documents, then creates the engine.
# The Discovery Engine API requires data stores to exist before
# creating an engine that references them.
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - Discovery Engine API enabled (discoveryengine.googleapis.com)
#   - Sufficient IAM permissions (roles/discoveryengine.admin)
#   - PDFs generated (run src/docs_gen/ generators first)
#
# Usage:
#   bash infra/provision_engine.sh
#
# After running, update config/settings.yaml with the output engine_id.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
PROJECT_ID=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['id'])")
GCS_BUCKET=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['gcs']['bucket'])")
LOCATION="global"
ENGINE_ID="grocery-workshop-engine"

echo "=== Provisioning Gemini Enterprise Instance ==="
echo "Project: ${PROJECT_ID}"
echo "Location: ${LOCATION}"
echo "Engine ID: ${ENGINE_ID}"
echo ""

# Ensure API is enabled
echo "Enabling Discovery Engine API..."
gcloud services enable discoveryengine.googleapis.com --project="${PROJECT_ID}" 2>/dev/null || true

TOKEN=$(gcloud auth print-access-token)

if [ "${LOCATION}" = "global" ]; then
  API_ENDPOINT="https://discoveryengine.googleapis.com"
else
  API_ENDPOINT="https://${LOCATION}-discoveryengine.googleapis.com"
fi

BASE_URL="${API_ENDPOINT}/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection"

# ---- Step 1: Create GCS bucket and upload documents ----
echo ""
echo "=== Step 1: Upload Documents to GCS ==="
gsutil mb -p "${PROJECT_ID}" -l US "gs://${GCS_BUCKET}" 2>/dev/null || echo "Bucket already exists"

echo "Uploading brand guidelines..."
gsutil -m cp "${PROJECT_ROOT}/data/brand_guidelines/"*.pdf "gs://${GCS_BUCKET}/brand_guidelines/" 2>&1

echo "Uploading SOPs..."
gsutil -m cp "${PROJECT_ROOT}/data/sops/"*.pdf "gs://${GCS_BUCKET}/sops/" 2>&1

echo "Uploading strategy documents..."
gsutil -m cp "${PROJECT_ROOT}/data/templates/"*.pdf "gs://${GCS_BUCKET}/strategy_docs/" 2>&1

# ---- Step 2: Create Data Stores ----
echo ""
echo "=== Step 2: Create Data Stores ==="

echo "Creating Brand Guidelines data store..."
curl -s -X POST \
  "${BASE_URL}/dataStores?dataStoreId=brand-guidelines-store" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Brand Guidelines",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"]
  }' | python3 -m json.tool 2>/dev/null || true

echo "Creating SOP data store..."
curl -s -X POST \
  "${BASE_URL}/dataStores?dataStoreId=sop-store" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Standard Operating Procedures",
    "industryVertical": "GENERIC",
    "contentConfig": "CONTENT_REQUIRED",
    "solutionTypes": ["SOLUTION_TYPE_CHAT"]
  }' | python3 -m json.tool 2>/dev/null || true

# Wait for data stores to be ready
echo "Waiting 10 seconds for data stores to initialize..."
sleep 10

# ---- Step 3: Create JSONL metadata and import documents ----
echo ""
echo "=== Step 3: Import Documents ==="

# Discovery Engine requires JSONL metadata files pointing to PDFs
echo "Creating metadata files..."

# Brand guidelines metadata
python3 -c "
import json, subprocess
uris = subprocess.check_output(['gsutil', 'ls', 'gs://${GCS_BUCKET}/brand_guidelines/'], text=True).strip().split('\n')
for i, uri in enumerate(uris):
    if uri.endswith('.pdf'):
        doc = {'id': f'brand-{i+1}', 'content': {'mimeType': 'application/pdf', 'uri': uri}, 'structData': {'title': uri.split('/')[-1].replace('.pdf',''), 'category': 'brand'}}
        print(json.dumps(doc))
" > /tmp/brand_metadata.jsonl
gsutil cp /tmp/brand_metadata.jsonl "gs://${GCS_BUCKET}/metadata/brand_metadata.jsonl"

# SOP metadata
python3 -c "
import json, subprocess
uris = subprocess.check_output(['gsutil', 'ls', 'gs://${GCS_BUCKET}/sops/'], text=True).strip().split('\n')
for i, uri in enumerate(uris):
    if uri.endswith('.pdf'):
        doc = {'id': f'sop-{i+1}', 'content': {'mimeType': 'application/pdf', 'uri': uri}, 'structData': {'title': uri.split('/')[-1].replace('.pdf',''), 'category': 'sop'}}
        print(json.dumps(doc))
" > /tmp/sop_metadata.jsonl
gsutil cp /tmp/sop_metadata.jsonl "gs://${GCS_BUCKET}/metadata/sop_metadata.jsonl"

echo "Importing brand guidelines..."
curl -s -X POST \
  "${BASE_URL}/dataStores/brand-guidelines-store/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${GCS_BUCKET}"'/metadata/brand_metadata.jsonl"],
      "dataSchema": "document"
    },
    "reconciliationMode": "FULL"
  }' | python3 -m json.tool 2>/dev/null || true

echo "Importing SOPs..."
curl -s -X POST \
  "${BASE_URL}/dataStores/sop-store/branches/default_branch/documents:import" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "gcsSource": {
      "inputUris": ["gs://'"${GCS_BUCKET}"'/metadata/sop_metadata.jsonl"],
      "dataSchema": "document"
    },
    "reconciliationMode": "FULL"
  }' | python3 -m json.tool 2>/dev/null || true

echo "Waiting 90 seconds for document import and indexing..."
sleep 90

# ---- Step 4: Create the Engine referencing data stores ----
echo ""
echo "=== Step 4: Create Discovery Engine ==="

ENGINE_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}/engines?engineId=${ENGINE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "'"${ENGINE_ID}"'",
    "solutionType": "SOLUTION_TYPE_SEARCH",
    "dataStoreIds": ["brand-guidelines-store", "sop-store"],
    "searchEngineConfig": {
      "searchTier": "SEARCH_TIER_ENTERPRISE",
      "searchAddOns": ["SEARCH_ADD_ON_LLM"]
    },
    "industryVertical": "GENERIC",
    "appType": "APP_TYPE_INTRANET"
  }')

echo "Engine response:"
echo "${ENGINE_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${ENGINE_RESPONSE}"

# ---- Step 5: Create the default assistant for streamAssist ----
echo ""
echo "=== Step 5: Create Default Assistant ==="

ASSISTANT_RESPONSE=$(curl -s -X POST \
  "${BASE_URL}/engines/${ENGINE_ID}/assistants?assistantId=default_assistant" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{
    "displayName": "Default Assistant"
  }')

echo "Assistant response:"
echo "${ASSISTANT_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${ASSISTANT_RESPONSE}"

echo ""
echo "=== Provisioning Complete ==="
echo "Engine ID: ${ENGINE_ID}"
echo ""
echo "Next steps:"
echo "  1. Wait for document imports to complete (check GCP console)"
echo "  2. Update config/settings.yaml:"
echo "     engine_id: ${ENGINE_ID}"
