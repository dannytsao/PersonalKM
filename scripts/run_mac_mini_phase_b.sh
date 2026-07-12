#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Load LLM API keys (gitignored, outside repo). Without this, Phase B
# Ollama API call will fail.
SECRETS_FILE="${PERSONALKM_SECRETS:-$HOME/.personalkm/worker.secrets}"
if [ -f "$SECRETS_FILE" ]; then
    # shellcheck source=/dev/null
    . "$SECRETS_FILE"
fi

REPO_ROOT="${PERSONALKM_REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"
LOG_DIR="${PERSONALKM_WORKER_LOG_DIR:-$HOME/Library/Logs/PersonalKM}"
LOCK_DIR="${PERSONALKM_LOCK_DIR:-$HOME/Library/Application Support/PersonalKM/phase-b.lock}"
PYTHON_BIN="/Users/dannytsao/.hermes/hermes-agent/venv/bin/python3"

mkdir -p "$LOG_DIR"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$*"
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase B already running; skipping this launch."
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

# Check Ollama is running before starting Phase B
if ! curl -s --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    log "Ollama not reachable at 127.0.0.1:11434 — skipping Phase B."
    log "Start Ollama with: ollama serve"
    exit 0
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    log "Repo has local uncommitted changes; skipping Phase B run."
    exit 0
fi

log "Starting PersonalKM Phase B (Ollama wikilink post-link)."
"$PYTHON_BIN" scripts/post_link_ollama.py
log "Finished PersonalKM Phase B."