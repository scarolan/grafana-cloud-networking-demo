#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Deploy network-generator + Alloy to Cloud Run (24/7 metrics pump)
# =============================================================================
# Prerequisites: gcloud auth login, .env file in repo root
# Usage: ./cloud-run/deploy.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PROJECT="${GCP_PROJECT:-solutions-engineering-248511}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="network-metrics-generator"
AR_REPO="network-demo"
AR_HOST="${REGION}-docker.pkg.dev"
AR_PATH="${AR_HOST}/${PROJECT}/${AR_REPO}"

# Load .env
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in credentials."
  exit 1
fi
set -a
source "$REPO_ROOT/.env"
set +a

echo "==> Project: ${PROJECT} | Region: ${REGION}"
echo "==> Service: ${SERVICE_NAME}"
echo ""

# Enable required APIs
echo "==> Enabling APIs..."
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT" --quiet

# Create Artifact Registry repo if needed
echo "==> Ensuring Artifact Registry repo '${AR_REPO}' exists..."
gcloud artifacts repositories describe "$AR_REPO" \
  --project="$PROJECT" --location="$REGION" 2>/dev/null \
  || gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT" \
    --quiet

# Build images with Cloud Build
echo "==> Building network-generator with Cloud Build..."
gcloud builds submit "$REPO_ROOT/network-generator/" \
  --tag="${AR_PATH}/network-generator:latest" \
  --project="$PROJECT" --region="$REGION" --quiet

echo "==> Building alloy sidecar with Cloud Build..."
gcloud builds submit "$SCRIPT_DIR/" \
  --tag="${AR_PATH}/alloy-sidecar:latest" \
  --project="$PROJECT" --region="$REGION" --quiet

# Deploy multi-container Cloud Run service
echo "==> Deploying to Cloud Run..."

cat > /tmp/cloud-run-service.yaml <<YAML
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ${SERVICE_NAME}
  labels:
    owner: sean-carolan
    contact: scar-at-grafana-com
    team: solutions-engineering
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/startup-cpu-boost: "true"
        run.googleapis.com/container-dependencies: '{"alloy-sidecar":["network-generator"]}'
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "1"
    spec:
      containerConcurrency: 80
      containers:
        - image: ${AR_PATH}/network-generator:latest
          name: network-generator
          ports:
            - containerPort: 8080
          resources:
            limits:
              cpu: "1"
              memory: 512Mi
          env:
            - name: GRAFANA_LOGS_URL
              value: "${GRAFANA_LOGS_URL}"
            - name: GRAFANA_LOGS_USERNAME
              value: "${GRAFANA_LOGS_USERNAME}"
            - name: GRAFANA_CLOUD_TOKEN
              value: "${GRAFANA_CLOUD_TOKEN}"
          startupProbe:
            httpGet:
              path: /metrics
              port: 8080
            initialDelaySeconds: 2
            periodSeconds: 10
            failureThreshold: 20
            timeoutSeconds: 5
        - image: ${AR_PATH}/alloy-sidecar:latest
          name: alloy-sidecar
          env:
            - name: GRAFANA_METRICS_URL
              value: "${GRAFANA_METRICS_URL}"
            - name: GRAFANA_METRICS_USERNAME
              value: "${GRAFANA_METRICS_USERNAME}"
            - name: GRAFANA_CLOUD_TOKEN
              value: "${GRAFANA_CLOUD_TOKEN}"
          resources:
            limits:
              cpu: "0.5"
              memory: 256Mi
YAML

gcloud run services replace /tmp/cloud-run-service.yaml \
  --project="$PROJECT" \
  --region="$REGION" \
  --quiet

rm -f /tmp/cloud-run-service.yaml

# Allow unauthenticated access (so Cloud Run health checks work)
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet

URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" --project="$PROJECT" \
  --format='value(status.url)')

echo ""
echo "==> Deployed! Service URL: ${URL}"
echo "==> Metrics endpoint: ${URL}/metrics"
echo "==> Metrics are being pushed to Grafana Cloud every 15s."
echo "==> Logs are being pushed directly to Loki every 5s."
echo ""
echo "To tear down: gcloud run services delete ${SERVICE_NAME} --region=${REGION} --project=${PROJECT}"
