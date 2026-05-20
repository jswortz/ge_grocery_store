#!/usr/bin/env bash
# ============================================================
# deploy_to_cloud_run.sh
#
# Deploy the simulator A2A agent to Cloud Run.
#
# Usage:
#   bash src/simulator_agent/deploy_to_cloud_run.sh
# ============================================================
set -euo pipefail

PROJECT_ID="wortz-project-352116"
REGION="us-central1"
SERVICE_NAME="simulator-a2a-agent"

echo "=== Deploying Simulator A2A Agent to Cloud Run ==="
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Service:  $SERVICE_NAME"
echo ""

cd "$(dirname "$0")/../.."

# Cloud Run --source uses the root Dockerfile; swap temporarily
cp Dockerfile Dockerfile.bak
cp src/simulator_agent/Dockerfile Dockerfile

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
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_VERTEXAI=TRUE"

# Restore original Dockerfile
cp Dockerfile.bak Dockerfile
rm Dockerfile.bak

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format='value(status.url)')

echo ""
echo "=== Simulator A2A Agent Deployed ==="
echo "Service URL: $SERVICE_URL"
echo "AgentCard:   ${SERVICE_URL}/.well-known/agent.json"
