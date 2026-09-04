#!/bin/bash
# Render startup script for AskDanny chat bot.
#
# This script:
#   1. Clones the lifestyle vault (so line_bot.py can read it)
#   2. Starts uvicorn
#
# Render start command:
#   bash scripts/start_askdanny_render.sh
#
# Required env vars on Render:
#   VAULT_PAT                     GitHub PAT with `repo` scope
#   ASKDANNY_CHANNEL_SECRET       LINE Channel Secret
#   ASKDANNY_CHANNEL_ACCESS_TOKEN LINE Channel Access Token
#   MINIMAX_API_KEY               For query_answer stage
#
# Optional:
#   ASKDANNY_ALLOWED_USERS        Comma-sep LINE userId whitelist (empty=open)
set -euo pipefail

VAULT_DIR="/opt/render/project/.vaults"
LIFESTYLE_DIR="$VAULT_DIR/Personalkm-lifestyle-vault"

LIFESTYLE_REPO="https://x-access-token:${VAULT_PAT:?}@github.com/dannytsao/Personalkm-lifestyle-vault.git"

mkdir -p "$VAULT_DIR"

if [[ -d "$LIFESTYLE_DIR/.git" ]]; then
  echo "⏩ Vault exists at $LIFESTYLE_DIR — pulling latest"
  cd "$LIFESTYLE_DIR" && git pull --ff-only origin main 2>/dev/null || true
else
  echo "📦 Cloning lifestyle vault..."
  git clone --depth 1 "$LIFESTYLE_REPO" "$LIFESTYLE_DIR"
fi

# Set env so line_bot.py picks it up
export ASKDANNY_LIFESTYLE_VAULT="$LIFESTYLE_DIR"

echo "🚀 Starting AskDanny uvicorn..."
exec uv run uvicorn personalkm.query.line_bot:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --log-level info