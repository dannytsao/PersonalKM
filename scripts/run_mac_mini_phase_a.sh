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
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/phase-a.lock}"
PYTHON_BIN="/Users/dannytsao/.hermes/hermes-agent/venv/bin/python3"

# Source pipeline status reporter (quality feedback loop)
# Uses ~/.personalkm/ path — launchd may not have TCC access to ~/Documents/.
STATUS_SCRIPT="${PERSONALKM_STATUS_SCRIPT:-$HOME/.personalkm/scripts/pipeline_status.sh}"
if [ -f "$STATUS_SCRIPT" ]; then
    # shellcheck source=/dev/null
    . "$STATUS_SCRIPT"
fi

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$LOCK_DIR")"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

vault_log() {
    # Append to local status log (vault/wiki/log.md may be TCC-restricted)
    local entry="[$(date '+%Y-%m-%d %H:%M:%S')] phase-a | $1 | $2"
    local local_log="$PIPELINE_STATUS_DIR/action_log.jsonl"
    mkdir -p "$(dirname "$local_log")"
    printf "%s\n" "$entry" >> "$local_log" 2>/dev/null || true
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase A already running; skipping this launch."
    write_phase_status "A" 0 "skipped" "Already running (lock file exists)"
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

if ! command -v git >/dev/null 2>&1; then
    log "git is not available on PATH."
    write_phase_status "A" 1 "failed" "git not on PATH"
    exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
    log "Python is not executable: $PYTHON_BIN"
    write_phase_status "A" 1 "failed" "Python not executable: $PYTHON_BIN"
    exit 1
fi

# Use git -C instead of cd — macOS TCC may block directory access under launchd.
# NOTE: This check has been disabled (2026-07-15) because macOS TCC blocks
# access to ~/Documents/ under launchd, causing git -C to always fail.
# Phase A is designed to be idempotent — running it on a clean repo is a no-op.
# The git check was causing false-positive skips for days.
# Instead, let the Python script fail gracefully if the repo is inaccessible.
log "Phase A: skipping git dirty check (TCC-safe mode)."

log "Starting PersonalKM Phase A (raw → wiki entities)."
if "$PYTHON_BIN" "$REPO_ROOT/scripts/ingest_wiki.py"; then
    log "Finished PersonalKM Phase A (success)."
    write_phase_status "A" 0 "success"
else
    local ec=$?
    log "Phase A Python script failed with exit code $ec."
    write_phase_status "A" "$ec" "failed" "Python runner failed with exit $ec"
    exit "$ec"
fi