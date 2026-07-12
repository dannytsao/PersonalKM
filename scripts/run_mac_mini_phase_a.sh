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

# Source pipeline status reporter (quality feedback loop)
# Must be sourced BEFORE any exit to capture all exit paths.
# Use ~/.personalkm/ path — launchd cannot access ~/Documents/ (macOS TCC).
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
    # Append a skip entry to the local status log instead of vault/wiki/log.md
    # (which is blocked by macOS TCC when running under launchd).
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

# cd to repo root — may fail under launchd if ~/Documents/ is TCC-restricted.
# If cd fails, proceed without git check (status reports will be minimal).
cd "$REPO_ROOT" 2>/dev/null || {
    log "WARNING: Cannot access repo root at $REPO_ROOT (macOS TCC). Proceeding without git check."
    REPO_ACCESSIBLE=false
}

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

if [ "${REPO_ACCESSIBLE:-true}" = true ] && ( ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null ); then
    log "Repo has local uncommitted changes; skipping Phase A run."
    vault_log "Skipped" "Repo has local uncommitted changes"
    write_phase_status "A" 0 "skipped" "Vault repo has uncommitted changes"
    exit 0
fi

log "Starting PersonalKM Phase A (raw → wiki entities)."
if "$PYTHON_BIN" scripts/ingest_wiki.py; then
    log "Finished PersonalKM Phase A (success)."
    write_phase_status "A" 0 "success"
else
    local ec=$?
    log "Phase A Python script failed with exit code $ec."
    write_phase_status "A" "$ec" "failed" "Python runner failed with exit $ec"
    exit "$ec"
fi