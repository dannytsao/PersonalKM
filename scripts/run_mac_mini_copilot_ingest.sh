#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"
VAULT_ROOT="${PERSONALKM_VAULT_ROOT:-$HOME/Documents/PersonalKM/Personalkm-vault}"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/copilot-ingest.lock}"
PYTHON_BIN="/Users/dannytsao/.hermes/hermes-agent/venv/bin/python3"

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$LOCK_DIR")"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

# Same stale-lock recovery as run_mac_mini_phase_a.sh: a crash mid-run
# would otherwise leave the lock directory behind forever, silently
# skipping every future hourly launch with no recovery.
STALE_LOCK_MAX_AGE_SECONDS=10800
if [ -d "$LOCK_DIR" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt "$STALE_LOCK_MAX_AGE_SECONDS" ]; then
        log "Stale lock (${lock_age}s old) — removing and proceeding."
        rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR"
    fi
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Copilot ingest already running; skipping this launch."
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

if [ ! -x "$PYTHON_BIN" ]; then
    log "Python is not executable: $PYTHON_BIN"
    exit 1
fi

log "Starting Copilot conversation ingest (copilot/ -> raw/Tech/)."
if "$PYTHON_BIN" "$REPO_ROOT/scripts/ingest_copilot_conversations.py" --vault "$VAULT_ROOT" --apply; then
    log "Finished Copilot conversation ingest (success)."
else
    ec=$?
    log "Copilot conversation ingest failed with exit code $ec."
    exit "$ec"
fi
