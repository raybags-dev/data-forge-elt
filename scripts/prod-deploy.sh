#!/usr/bin/env bash
# =============================================================================
# DataForge ELT — Production Deploy Script
# Pulls updated images from ghcr.io and restarts the stack on the VPS.
# Called by GitHub Actions deploy job. Can also be run manually on the server.
# =============================================================================
set -euo pipefail

APP_DIR=/opt/dataforge-elt
DATA_DIR=/mnt/portfolio-data/dataforge

GHCR_OWNER="${GHCR_OWNER:-raybags-dev}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

log() { echo "[$(date -u '+%H:%M:%S')] $*"; }

log "Starting DataForge ELT deploy (tag=$IMAGE_TAG)"

# Ensure data directories exist
mkdir -p "$DATA_DIR"/{datalake/{raw,bronze,silver,gold},warehouse,logs/screenshots,dbt-target}

cd "$APP_DIR"

# Login to ghcr.io if token provided
if [ -n "$GITHUB_TOKEN" ]; then
  echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GHCR_OWNER" --password-stdin
  log "Logged in to ghcr.io"
fi

# Pull latest images
log "Pulling images..."
docker compose -f docker-compose.prod.yml pull

# Restart with zero-downtime rolling update
log "Restarting services..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Prune old images
docker image prune -f

log "Deploy complete"
log "  API       → http://89.167.74.127:8002"
log "  Streamlit → http://89.167.74.127:8501"
log "  UI        → http://89.167.74.127:8503"
