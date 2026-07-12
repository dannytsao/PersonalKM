#!/usr/bin/env bash
# ============================================================================
# Pipeline Quality Feedback Loop — Local Status Reporter (bash)
# ============================================================================
# Source this from shell scripts. Writes ~/.personalkm/status/ on EVERY exit
# path, even when the pipeline skips.
#
# Usage:
#   source ~/.personalkm/scripts/pipeline_status.sh
#   write_phase_status "A" 0 "success"
#   write_phase_status "B" 1 "failed" "Ollama not reachable"
#   write_phase_status "A" 0 "skipped" "Vault repo has uncommitted changes"
#
# For detailed view:
#   python3 -m personalkm.pipeline_status check
# ============================================================================

PIPELINE_STATUS_DIR="${PERSONALKM_STATUS_DIR:-$HOME/.personalkm/status}"
PIPELINE_STATUS_FILE="$PIPELINE_STATUS_DIR/pipeline.json"

# Ensure status directory exists (ALWAYS — even if script fails later)
mkdir -p "$PIPELINE_STATUS_DIR"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_summarize() {
    local phase="${1:-A}"
    local status="${2:-unknown}"
    local exit_code="${3:-0}"
    local detail="${4:-}"

    local icon
    case "$status" in
        success) icon="✅" ;;
        partial) icon="⚠️" ;;
        skipped) icon="⏭️" ;;
        failed|error) icon="❌" ;;
        *) icon="❓" ;;
    esac

    echo "$icon Phase $phase: $status (exit=$exit_code)${detail:+ | $detail}"
}

# ---------------------------------------------------------------------------
# Main entry point — write status JSON
# ---------------------------------------------------------------------------
write_phase_status() {
    local phase="${1:-A}"
    local exit_code="${2:-0}"
    local status="${3:-unknown}"
    local detail="${4:-}"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local summary
    summary=$(_summarize "$phase" "$status" "$exit_code" "$detail")

    # Log to system log
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "$summary"

    # Write per-phase status file
    local phase_key="phase_$(echo "$phase" | tr 'A-Z' 'a-z')"
    local per_phase_file="$PIPELINE_STATUS_DIR/${phase_key}.json"
    printf '{"last_run":"%s","exit_code":%s,"status":"%s","detail":"%s"}\n' \
        "$timestamp" "$exit_code" "$status" "$detail" > "$per_phase_file"

    # Append to plain text log (always works, no dependencies)
    printf "%s\t%s\t%s\n" "$timestamp" "$phase" "$summary" >> "$PIPELINE_STATUS_DIR/status.log" 2>/dev/null || true

    # Merge into pipeline.json via Python (best-effort, silent on failure)
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json, os
from pathlib import Path

status_dir = Path(os.path.expanduser('$PIPELINE_STATUS_DIR'))
pipeline_file = status_dir / 'pipeline.json'

# Load existing
current = {}
if pipeline_file.exists():
    try:
        current = json.loads(pipeline_file.read_text())
    except: pass

# Read per-phase file
pf = status_dir / '${phase_key}.json'
if pf.exists():
    try:
        current['${phase_key}'] = json.loads(pf.read_text())
    except: pass

# Vault state (basic)
vault_dir = Path(os.path.expanduser('$VAULT_ROOT')) if '$VAULT_ROOT' else None
dirty = False
raw_count = 0
if vault_dir:
    try:
        import subprocess
        r = subprocess.run(['git','status','--porcelain'], cwd=vault_dir, capture_output=True, text=True, timeout=5)
        dirty = bool(r.stdout.strip())
        raw_count = len(list(vault_dir.glob('raw/**/*.md'))) if vault_dir.exists() else 0
    except: pass

current['vault'] = {'dirty': dirty, 'raw_unprocessed': raw_count}
current['last_updated'] = '$timestamp'
current['summary'] = '$(echo "$summary" | sed "s/'//g; s/\"/\\\\\"/g")'

pipeline_file.write_text(json.dumps(current, indent=2, ensure_ascii=False))
" 2>/dev/null || true
    fi
}

# ---------------------------------------------------------------------------
# Quick check helper (for interactive use)
# ---------------------------------------------------------------------------
pipeline_status() {
    if [ -f "$PIPELINE_STATUS_FILE" ]; then
        python3 -m json.tool "$PIPELINE_STATUS_FILE" 2>/dev/null || cat "$PIPELINE_STATUS_FILE"
    else
        echo '{"status": "no_data", "message": "No pipeline status recorded yet"}'
    fi
}