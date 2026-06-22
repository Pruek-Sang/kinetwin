#!/usr/bin/env bash
# =============================================================================
# deploy_kinetwin.sh — deploy ONE KineTwin Cloud Run service  [SCAFFOLD-style]
# =============================================================================
# Isolated from SCAFFOLD: only ever touches services/images named kinetwin-*.
#
# Usage:
#   bash src/deploy/cloudrun/deploy_kinetwin.sh backend
#   bash src/deploy/cloudrun/deploy_kinetwin.sh frontend <BACKEND_URL>
# =============================================================================
set -euo pipefail

REGION="${KT_REGION:-asia-southeast1}"
PROJECT="${KT_PROJECT:-gen-lang-client-0658701327}"
REPO="${KT_REPO:-kinetwin}"
SVC="$1"
shift || true

case "${SVC}" in
  backend)
    PORT=8000
    IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/backend:latest"
    SERVICE="kinetwin-backend"
    ;;
  frontend)
    BACKEND_URL="${1:?frontend needs BACKEND_URL}"
    PORT=80
    IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/frontend:latest"
    SERVICE="kinetwin-frontend"
    echo "Building frontend with VITE_API_URL=${BACKEND_URL} ..."
    docker build -f src/frontend/Dockerfile --build-arg "VITE_API_URL=${BACKEND_URL}" \
      -t "${IMAGE}" src/frontend
    docker push "${IMAGE}"
    ;;
  *) echo "FAIL: service must be backend|frontend"; exit 1 ;;
esac

if [ "${SVC}" = "backend" ]; then
  docker build -f Dockerfile.backend -t "${IMAGE}" .
  docker push "${IMAGE}"
fi

echo "Deploying ${SERVICE} to Cloud Run ..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --port "${PORT}" \
  --memory "1Gi" \
  --allow-unauthenticated \
  --no-traffic-unassigned || \
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" --region "${REGION}" --project "${PROJECT}" \
  --port "${PORT}" --allow-unauthenticated

gcloud run services describe "${SERVICE}" \
  --region "${REGION}" --project "${PROJECT}" \
  --format 'value(status.url)'
