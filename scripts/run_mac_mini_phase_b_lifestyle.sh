#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

SECRETS_FILE="${PERSONALKM_SECRETS:-$HOME/.personalkm/worker.secrets}"
if [ -f "$SECRETS_FILE" ]; then
    . "$SECRETS_FILE"
fi

REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"
VAULT_ROOT="${PERSONALKM_VAULT_ROOT:-$HOME/Documents/PersonalKM/Personalkm-lifestyle-vault}"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/phase-b-lifestyle.lock}"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python3"

# Source pipeline status reporter (quality feedback loop) — mirrors tech wrapper
STATUS_SCRIPT="${PERSONALKM_STATUS_SCRIPT:-$HOME/.personalkm/scripts/pipeline_status.sh}"
if [ -f "$STATUS_SCRIPT" ]; then
    . "$STATUS_SCRIPT"
fi

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$LOCK_DIR")"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

vault_log() {
    # Append a Phase B entry to vault/wiki/log.md.
    # launchd's bash has no TCC grant for ~/Documents — direct appends fail
    # with "Operation not permitted". Child processes of the venv Python
    # inherit its TCC grant, so route the write through it (same trick
    # sync_vault uses for git).
    local log_path="$VAULT_ROOT/wiki/log.md"
    [ -f "$log_path" ] || return 0
    "$PYTHON_BIN" -c 'import pathlib, sys
p, stamp, status, message = sys.argv[1:5]
pathlib.Path(p).open("a", encoding="utf-8").write(f"\n## [{stamp}] phase-b (lifestyle) | {status}\n- {message}\n")' \
        "$log_path" "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2" 2>/dev/null || true
}

STALE_LOCK_MAX_AGE_SECONDS=10800
if [ -d "$LOCK_DIR" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt "$STALE_LOCK_MAX_AGE_SECONDS" ]; then
        log "Stale lock — removing."
        rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR"
    fi
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase B (lifestyle) already running; skipping."
    vault_log "Skipped" "Already running (lock file exists)"
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

# TCC-safe git (2026-11-11): launchd-spawned bash cannot exec git against
# ~/Documents paths (getcwd EPERM -> "Operation not permitted"), but children
# of the venv Python inherit its TCC grant (proven by gps_backfill_sync.py
# and post_link_ollama.py). Route all wrapper git through the venv Python.
vgit() {
    "$PYTHON_BIN" -c 'import subprocess, sys; sys.exit(subprocess.call(["git"] + sys.argv[1:]))' "$@"
}

sync_vault() {
    local vault="$1"
    log "Pre-run vault sync: stash → pull --rebase → stash pop"
    local stashed=0
    if [ -n "$(vgit -C "$vault" status --porcelain 2>/dev/null || true)" ]; then
        if vgit -C "$vault" stash push -u -m "phase-b-lifestyle-pre-sync" >/dev/null 2>&1; then
            stashed=1
            log "Stashed uncommitted changes."
        fi
    else
        log "Working tree clean — no stash needed."
    fi
    if ! vgit -C "$vault" pull --rebase origin main 2>&1; then
        log "Warning: pull --rebase failed — restoring stashed changes and continuing."
        if [ "$stashed" -eq 1 ]; then
            vgit -C "$vault" stash pop 2>/dev/null || true
        fi
        return 1
    fi
    if [ "$stashed" -eq 1 ]; then
        vgit -C "$vault" stash pop 2>/dev/null || true
        log "Restored stashed changes."
    fi
    log "Vault sync: success."
    return 0
}

log "Phase B (lifestyle): starting (wikilinks)."
cd "$REPO_ROOT"
sync_vault "$VAULT_ROOT" || log "Proceeding despite sync failure."
vault_log "Running" "Wikilink post-link started"
if "$PYTHON_BIN" scripts/post_link_ollama.py --wiki "$VAULT_ROOT"; then
    log "Phase B (lifestyle): success."
    vault_log "Success" "Wikilink post-link completed"
    if command -v write_phase_status >/dev/null 2>&1; then
        write_phase_status "B" 0 "success" "lifestyle"
    fi
else
    ec=$?
    log "Phase B (lifestyle): failed with exit code $ec."
    vault_log "Failed" "Python runner exited with code $ec"
    if command -v write_phase_status >/dev/null 2>&1; then
        write_phase_status "B" "$ec" "failed" "Python runner failed with exit $ec (lifestyle)"
    fi
    exit "$ec"
fi