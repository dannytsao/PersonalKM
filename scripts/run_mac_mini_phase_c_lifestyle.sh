#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
SECRETS_FILE="${PERSONALKM_SECRETS:-$HOME/.personalkm/worker.secrets}"
[ -f "$SECRETS_FILE" ] && . "$SECRETS_FILE"
REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"
VAULT_ROOT="$HOME/Documents/PersonalKM/Personalkm-lifestyle-vault"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
LOCK_DIR="$HOME/Library/Application Support/PersonalKM/phase-c-lifestyle.lock"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python3"

STATUS_SCRIPT="${PERSONALKM_STATUS_SCRIPT:-$HOME/.personalkm/scripts/pipeline_status.sh}"
if [ -f "$STATUS_SCRIPT" ]; then
    # shellcheck source=/dev/null
    . "$STATUS_SCRIPT"
fi

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_DIR")"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"; }

STALE_LOCK_MAX_AGE_SECONDS=10800
if [ -d "$LOCK_DIR" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt "$STALE_LOCK_MAX_AGE_SECONDS" ]; then
        log "Stale lock — removing."
        rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR"
    fi
fi
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase C (lifestyle) already running; skipping."
    write_phase_status "C" 0 "skipped" "Already running (lock file exists) (lifestyle)" 2>/dev/null || true
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

log "Phase C (lifestyle): starting distillation."
cd "$REPO_ROOT"
if "$PYTHON_BIN" scripts/distill_cron.py --vault "$VAULT_ROOT" --limit 5; then
    log "Phase C (lifestyle): success."
    write_phase_status "C" 0 "success" "lifestyle" 2>/dev/null || true
else
    ec=$?
    log "Phase C (lifestyle): failed with exit code $ec."
    write_phase_status "C" "$ec" "failed" "Python runner failed with exit $ec (lifestyle)" 2>/dev/null || true
    exit "$ec"
fi
