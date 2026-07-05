#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/.personalkm/personalkm-vault}"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
LOCK_DIR="${TMPDIR:-/tmp}/personalkm-omnichannel-worker.lock"
PYTHON_BIN="${PERSONALKM_PYTHON:-/usr/bin/python3}"

mkdir -p "$LOG_DIR"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  log "Worker already running; skipping this launch."
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

if ! "$PYTHON_BIN" -c "import httpx" >/dev/null 2>&1; then
  log "Python dependency check failed: httpx is not importable with $PYTHON_BIN"
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  log "Repo has local uncommitted changes; skipping worker run."
  exit 0
fi

log "Starting PersonalKM omnichannel worker."
"$PYTHON_BIN" -m tools.omnichannel_md.worker --process-one
log "Finished PersonalKM omnichannel worker."
