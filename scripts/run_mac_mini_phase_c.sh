#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Load LLM API keys (gitignored, outside repo). The entity_distillation
# stage uses cloud-first (DeepSeek), so DEEPSEEK_API_KEY is critical.
SECRETS_FILE="${PERSONALKM_SECRETS:-$HOME/.personalkm/worker.secrets}"
if [ -f "$SECRETS_FILE" ]; then
    # shellcheck source=/dev/null
    . "$SECRETS_FILE"
fi

REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/phase-c.lock}"
PYTHON_BIN="/Users/dannytsao/.hermes/hermes-agent/venv/bin/python3"
VAULT_ROOT="${PERSONALKM_VAULT_ROOT:-$HOME/Documents/PersonalKM/Personalkm-vault}"

# Source pipeline status reporter (quality feedback loop)
STATUS_SCRIPT="${PERSONALKM_STATUS_SCRIPT:-$HOME/.personalkm/scripts/pipeline_status.sh}"
if [ -f "$STATUS_SCRIPT" ]; then
    # shellcheck source=/dev/null
    . "$STATUS_SCRIPT"
fi

mkdir -p "$LOG_DIR"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

# Stale lock recovery: `trap ... EXIT` below does not fire on a hard power
# loss or kill -9, so a crash mid-run can leave the lock directory behind
# forever, silently skipping every future launch with no recovery.
# Distillation is slow (LLM per page), so generous margin.
STALE_LOCK_MAX_AGE_SECONDS=10800
if [ -d "$LOCK_DIR" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt "$STALE_LOCK_MAX_AGE_SECONDS" ]; then
        log "Stale lock (${lock_age}s old) — removing and proceeding."
        rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR"
    fi
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase C already running; skipping this launch."
    write_phase_status "C" 0 "skipped" "Already running (lock file exists)" 2>/dev/null || true
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

if [ ! -x "$PYTHON_BIN" ]; then
    log "Python is not executable: $PYTHON_BIN"
    write_phase_status "C" 1 "failed" "Python not executable: $PYTHON_BIN" 2>/dev/null || true
    exit 1
fi

# TCC-safe: use git -C instead of cd. No dirty check (same as Phase A/B).
log "Phase C: starting Entity Distillation Loop."

if "$PYTHON_BIN" "$REPO_ROOT/scripts/distill_cron.py" --vault "$VAULT_ROOT" --limit 5; then
    log "Finished PersonalKM Phase C (success)."
    write_phase_status "C" 0 "success" 2>/dev/null || true
else
    ec=$?
    log "Phase C Python script failed with exit code $ec."
    write_phase_status "C" "$ec" "failed" "Python runner failed with exit $ec" 2>/dev/null || true
    exit "$ec"
fi
