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

# Sparse paths: the ONLY files line_bot.py reads.  The vault contains 70+
# LINE-generated filenames longer than 255 BYTES (fine on macOS APFS, illegal
# on Linux ext4) — any full checkout/pull that includes them fails wholesale,
# which is how the deployed vault silently froze at a 2-day-old commit
# (2026-09-29 incident).  A sparse checkout never materializes those names,
# so clone AND later pulls stay healthy.
SPARSE_PATHS="'/wiki/_registry/**' '/wiki/concepts/city-subject-store.md' '/wiki/concepts/tianmu-food.md'"

if [[ -d "$LIFESTYLE_DIR/.git" ]]; then
  echo "⏩ Vault exists at $LIFESTYLE_DIR — pulling latest"
  cd "$LIFESTYLE_DIR"
  # Self-heal: ensure sparse config even if an older full checkout created this clone
  git config core.sparseCheckout true
  eval "git sparse-checkout set --no-cone $SPARSE_PATHS"
  git pull --ff-only origin main || echo "❌ vault pull failed at boot (runtime auto-pull will retry)"
else
  echo "📦 Cloning lifestyle vault (sparse)..."
  git clone --depth 1 --no-checkout "$LIFESTYLE_REPO" "$LIFESTYLE_DIR"
  cd "$LIFESTYLE_DIR"
  eval "git sparse-checkout set --no-cone $SPARSE_PATHS"
  # NOTE: must be `git checkout main` (no `-- .`) — the pathspec form ignores
  # sparse rules and materializes every file, reintroducing the long-name crash.
  git checkout main
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