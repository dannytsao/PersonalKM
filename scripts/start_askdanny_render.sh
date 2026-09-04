#!/bin/bash
# Render startup script for AskDanny chat bot.
#
# This script:
#   1. Clones the lifestyle vault (handles long filenames on Linux ext4)
#   2. Starts uvicorn
#
# Render start command:
#   bash scripts/start_askdanny_render.sh
#
# Required env vars on Render:
#   LIFESTYLE_VAULT_REPO_URL   Full clone URL with embedded PAT:
#                              https://x-access-token:PAT@github.com/dannytsao/Personalkm-lifestyle-vault.git
#   ASKDANNY_CHANNEL_SECRET    LINE Channel Secret
#   ASKDANNY_CHANNEL_ACCESS_TOKEN LINE Channel Access Token
set -euo pipefail

VAULT_DIR="/opt/render/project/.vaults"
LIFESTYLE_DIR="$VAULT_DIR/Personalkm-lifestyle-vault"
LIFESTYLE_REPO="${LIFESTYLE_VAULT_REPO_URL:?}"

mkdir -p "$VAULT_DIR"

if [[ -d "$LIFESTYLE_DIR/.git" ]]; then
  echo "⏩ Vault exists at $LIFESTYLE_DIR — pulling latest"
  cd "$LIFESTYLE_DIR"
  git pull --ff-only origin main 2>/dev/null || true
else
  echo "📦 Cloning lifestyle vault..."
  # Clone metadata only first, then checkout what we can.
  # Some files have filenames > 255 chars (OK on macOS ext4, not on Linux).
  # Those few files are skipped — the bot still works with all others.
  git clone --depth 1 "$LIFESTYLE_REPO" "$LIFESTYLE_DIR" 2>&1 || true
  if [[ -d "$LIFESTYLE_DIR/.git" ]]; then
    cd "$LIFESTYLE_DIR"
    echo "⚠️  Partial clone — checking out available files..."
    git checkout HEAD -- . 2>&1 | grep -v "File name too long" || true
  fi
fi

# Verify the wiki directory is accessible
if [[ ! -d "$LIFESTYLE_DIR/wiki" ]]; then
  echo "❌ wiki/ directory not found after clone"
  ls -la "$LIFESTYLE_DIR/" 2>/dev/null || true
  exit 1
fi

# Count checked-out files
WIKI_COUNT=$(find "$LIFESTYLE_DIR/wiki" -name "*.md" 2>/dev/null | wc -l)
echo "✅ $WIKI_COUNT wiki files available"

# Set env so line_bot.py picks it up
export ASKDANNY_LIFESTYLE_VAULT="$LIFESTYLE_DIR"

echo "🚀 Starting AskDanny uvicorn..."
exec python3 -m uvicorn personalkm.query.line_bot:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --log-level info