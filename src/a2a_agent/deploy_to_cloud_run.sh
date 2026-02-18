#!/usr/bin/env bash
# ============================================================
# deploy_to_cloud_run.sh
#
# Deploy the A2A grocery retail agent to Cloud Run.
#
# Usage:
#   bash src/a2a_agent/deploy_to_cloud_run.sh
# ============================================================
set -euo pipefail

PROJECT_ID="wortz-project-352116"
REGION="us-central1"
SERVICE_NAME="grocery-a2a-agent"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== Deploying A2A Agent to Cloud Run ==="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"
echo ""

# Build and deploy from source (uses Cloud Build + Buildpacks or Dockerfile)
cd "$(dirname "$0")/../.."

gcloud run deploy "$SERVICE_NAME" \
  --source=. \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=TRUE"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format='value(status.url)')

echo ""
echo "=== A2A Agent Deployed ==="
echo "Service URL: $SERVICE_URL"
echo "AgentCard:   ${SERVICE_URL}/.well-known/agent.json"
echo "A2A Endpoint: ${SERVICE_URL}/a2a"
