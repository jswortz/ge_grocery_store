#!/usr/bin/env bash
# ============================================================
# Upload Generated Assets to GCS and Google Drive
# ============================================================
# Uploads all generated PDFs to GCS for Discovery Engine ingestion,
# and optionally to Google Drive for workshop distribution.
#
# Prerequisites:
#   - PDFs generated (run the generators in src/docs_gen/)
#   - GCS bucket created (see provision_datastore.sh)
#
# Usage:
#   bash infra/upload_assets.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

# Load config
PROJECT_ID=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['project']['id'])")
GCS_BUCKET=$(python3 -c "import yaml; c=yaml.safe_load(open('${PROJECT_ROOT}/config/settings.yaml')); print(c['gcs']['bucket'])")

echo "=== Uploading Assets to GCS ==="
echo "Project: ${PROJECT_ID}"
echo "Bucket: gs://${GCS_BUCKET}"
echo ""

# Create bucket if it doesn't exist
gsutil mb -p "${PROJECT_ID}" -l US "gs://${GCS_BUCKET}" 2>/dev/null || echo "Bucket already exists"

# Upload brand guidelines
echo "Uploading brand guidelines..."
gsutil -m cp "${PROJECT_ROOT}/data/brand_guidelines/"*.pdf "gs://${GCS_BUCKET}/brand_guidelines/"

# Upload SOPs
echo "Uploading SOPs..."
gsutil -m cp "${PROJECT_ROOT}/data/sops/"*.pdf "gs://${GCS_BUCKET}/sops/"

# Upload strategy documents
echo "Uploading strategy documents..."
gsutil -m cp "${PROJECT_ROOT}/data/templates/"*.pdf "gs://${GCS_BUCKET}/strategy_docs/"

echo ""
echo "=== Upload Summary ==="
echo "Brand guidelines:"
gsutil ls "gs://${GCS_BUCKET}/brand_guidelines/" 2>/dev/null || echo "  (none)"
echo "SOPs:"
gsutil ls "gs://${GCS_BUCKET}/sops/" 2>/dev/null || echo "  (none)"
echo "Strategy docs:"
gsutil ls "gs://${GCS_BUCKET}/strategy_docs/" 2>/dev/null || echo "  (none)"

echo ""
echo "=== Google Drive Upload (Optional) ==="
echo "To upload to Google Drive, use:"
echo "  gdrive upload --parent <FOLDER_ID> data/brand_guidelines/*.pdf"
echo "  gdrive upload --parent <FOLDER_ID> data/sops/*.pdf"
echo "  gdrive upload --parent <FOLDER_ID> data/templates/*.pdf"
echo ""
echo "Then update config/settings.yaml with the folder ID."
