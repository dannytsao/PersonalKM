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
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/phase-a-lifestyle.lock}"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python3"

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
    # Append a Phase A entry to vault/wiki/log.md.
    # launchd's bash has no TCC grant for ~/Documents — direct appends fail
    # with "Operation not permitted". Child processes of the venv Python
    # inherit its TCC grant, so route the write through it (same trick
    # the wrapper already uses for git).
    local log_path="$VAULT_ROOT/wiki/log.md"
    [ -f "$log_path" ] || return 0
    "$PYTHON_BIN" -c 'import pathlib, sys
p, stamp, status, message = sys.argv[1:5]
pathlib.Path(p).open("a", encoding="utf-8").write(f"\n## [{stamp}] phase-a (lifestyle) | {status}\n- {message}\n")' \
        "$log_path" "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2" 2>/dev/null || true
}

STALE_LOCK_MAX_AGE_SECONDS=10800
if [ -d "$LOCK_DIR" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt "$STALE_LOCK_MAX_AGE_SECONDS" ]; then
        log "Stale lock (${lock_age}s old) — removing and proceeding."
        rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR"
    fi
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase A (lifestyle) already running; skipping this launch."
    vault_log "Skipped" "Already running (lock file exists)"
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

if ! command -v git >/dev/null 2>&1; then
    log "git is not available on PATH."
    exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
    log "Python is not executable: $PYTHON_BIN"
    exit 1
fi

# TCC-safe git (2026-11-11): launchd-spawned bash cannot exec git against
# ~/Documents paths (getcwd EPERM -> "Operation not permitted"), but children
# of the venv Python inherit its TCC grant (proven by gps_backfill_sync.py
# and post_link_ollama.py). Route all wrapper git through the venv Python.
vgit() {
    "$PYTHON_BIN" -c 'import subprocess, sys; sys.exit(subprocess.call(["git"] + sys.argv[1:]))' "$@"
}

sync_vault() {
    local vault="$1"
    log "Pre-run vault sync: stash → push → pull --rebase → stash pop"
    local stashed=0
    if vgit -C "$vault" stash >/dev/null 2>&1; then
        stashed=1
        log "Stashed uncommitted changes."
    else
        log "No changes to stash (or stash failed) — continuing."
    fi
    # Push any local commits from a previous run before pulling.
    # Without this, local ingest commits stay unpushed and the next
    # pull --rebase can conflict with remote capture-bot commits.
    vgit -C "$vault" push origin main 2>&1 || log "Warning: push failed (may be up-to-date or diverged)."
    # Fetch remote changes, then merge (not rebase — rebase fails when both
    # sides append to wiki/log.md, which happens every run).
    vgit -C "$vault" fetch origin main 2>&1 || log "Warning: fetch failed."
    if ! vgit -C "$vault" merge origin/main --no-edit 2>&1; then
        log "Warning: merge failed — restoring stashed changes and continuing."
        vgit -C "$vault" merge --abort 2>/dev/null || true
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

log "Phase A (lifestyle): starting (raw → wiki entities)."
cd "$REPO_ROOT"
sync_vault "$VAULT_ROOT" || log "Proceeding despite sync failure."
if "$PYTHON_BIN" scripts/ingest_wiki.py --vault "$VAULT_ROOT"; then
    log "Phase A (lifestyle): success."
    # Post-ingest push: ingest_wiki.py commits+pushes wiki/ changes internally,
    # but raw → Archive moves and resolved/ files may remain uncommitted.
    # Push everything so the next run's sync_vault doesn't conflict.
    # 2026-11-11: bash-spawned git is TCC-blocked under launchd (silent
    # "Operation not permitted", killing this script via set -e since
    # ~2026-09-26, leaving wiki/log.md + knowledge-graph.md uncommitted).
    # Python-spawned git works in the same launchd context (Phase C pushes
    # daily), so run the post-ingest sync through the venv Python.
    "$PYTHON_BIN" - "$VAULT_ROOT" <<'PYEOF' || log "Warning: post-ingest git sync failed."
import subprocess, sys
vault = sys.argv[1]
def git(*args):
    r = subprocess.run(["git", "-C", vault, *args], capture_output=True, text=True)
    if r.returncode not in (0, 1) and r.stderr.strip():
        print("[post-ingest] git %s: %s" % (args[0], r.stderr.strip()[:300]))
    return r
git("add", "--all")
if git("diff", "--cached", "--quiet").returncode != 0:
    git("commit", "-m", "🤖 Auto: post-ingest sync (raw → Archive moves)")
git("push", "origin", "main")
PYEOF
    vault_log "Success" "Resolver + Ingest completed"
    write_phase_status "A" 0 "success"
else
    ec=$?
    log "Phase A (lifestyle): failed with exit code $ec."
    vault_log "Failed" "Python runner exited with code $ec"
    write_phase_status "A" "$ec" "failed" "Python runner exited with code $ec"
    exit "$ec"
fi