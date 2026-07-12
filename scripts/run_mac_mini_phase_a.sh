#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Load LLM API keys (gitignored, outside repo).
SECRETS_FILE="${PERSONALKM_SECRETS:-$HOME/.personalkm/worker.secrets}"
if [ -f "$SECRETS_FILE" ]; then
    # shellcheck source=/dev/null
    . "$SECRETS_FILE"
fi

REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"
VAULT_ROOT="${PERSONALKM_VAULT_ROOT:-$HOME/Documents/PersonalKM/Personalkm-vault}"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
# Fixed path — does NOT depend on TMPDIR (launchd unsets ALL env vars including TMPDIR)
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/phase-a.lock}"
PYTHON_BIN="/Users/dannytsao/.hermes/hermes-agent/venv/bin/python3"

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$LOCK_DIR")"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

vault_log() {
    # Append a skip entry to vault/wiki/log.md
    local entry="\n## [$(date '+%Y-%m-%d %H:%M:%S')] phase-a | $1\n- $2\n"
    local log_path="$VAULT_ROOT/wiki/log.md"
    if [ -f "$log_path" ]; then
        printf "%b" "$entry" >> "$log_path" 2>/dev/null || true
    fi
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase A already running; skipping this launch."
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

cd "$REPO_ROOT"

if ! command -v git >/dev/null 2>&1; then
    log "git is not available on PATH."
    exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
    log "Python is not executable: $PYTHON_BIN"
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    log "Repo has local uncommitted changes; skipping Phase A run."
    vault_log "Skipped" "Repo has local uncommitted changes"
    exit 0
fi

log "Starting PersonalKM Phase A (raw → wiki entities)."
"$PYTHON_BIN" scripts/ingest_wiki.py
log "Finished PersonalKM Phase A."