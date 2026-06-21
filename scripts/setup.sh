#!/usr/bin/env bash
set -euo pipefail
# One-command project setup

uv sync --extra dev
uv run playwright install chromium
mkdir -p logs/screenshots datalake/{raw,bronze,silver,gold} warehouse
touch logs/.gitkeep \
      datalake/raw/.gitkeep \
      datalake/bronze/.gitkeep \
      datalake/silver/.gitkeep \
      datalake/gold/.gitkeep

echo "DataForge setup complete."
