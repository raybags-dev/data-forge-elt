#!/usr/bin/env bash
set -euo pipefail
# Deploy DataForge ELT to GitHub
# Usage: ./scripts/deploy.sh "commit message" [branch]

COMMIT_MSG=${1:-"chore: update DataForge ELT"}
BRANCH=${2:-main}

# Configure git identity from environment
GIT_USER=${GIT_USER:-raybags-dev}
GIT_EMAIL=${GIT_EMAIL:-baguma.github@gmail.com}

git config user.name "$GIT_USER"
git config user.email "$GIT_EMAIL"

git add -A
git commit -m "$COMMIT_MSG"
git push origin "$BRANCH"

echo "Deployed to $BRANCH: $COMMIT_MSG"
