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

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Phase B already running; skipping this launch."
    write_phase_status "B" 0 "skipped" "Already running (lock file exists)"
    exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

if ! command -v git >/dev/null 2>&1; then
    log "git is not available on PATH."
    write_phase_status "B" 1 "failed" "git not on PATH"
    exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
    log "Python is not executable: $PYTHON_BIN"
    write_phase_status "B" 1 "failed" "Python not executable: $PYTHON_BIN"
    exit 1
fi

# Check Ollama is running before starting Phase B
if ! curl -s --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    log "Ollama not reachable at 127.0.0.1:11434 — skipping Phase B."
    log "Start Ollama with: ollama serve"
    write_phase_status "B" 0 "skipped" "Ollama not reachable at 127.0.0.1:11434"
    exit 0
fi

# Use git -C instead of cd — macOS TCC may block directory access under launchd.
if ! git -C "$REPO_ROOT" diff --quiet 2>/dev/null || ! git -C "$REPO_ROOT" diff --cached --quiet 2>/dev/null; then
    log "Repo has local uncommitted changes; skipping Phase B run."
    write_phase_status "B" 0 "skipped" "Vault repo has uncommitted changes"
    exit 0
fi

log "Starting PersonalKM Phase B (Ollama wikilink post-link)."
if "$PYTHON_BIN" "$REPO_ROOT/scripts/post_link_ollama.py"; then
    log "Finished PersonalKM Phase B (success)."
    write_phase_status "B" 0 "success"
else
    local ec=$?
    log "Phase B Python script failed with exit code $ec."
    write_phase_status "B" "$ec" "failed" "Python runner failed with exit $ec"
    exit "$ec"
fi