#!/usr/bin/env bash
# ============================================================================
# Pipeline Quality Feedback Loop — Local Status Reporter (bash)
# ============================================================================
# Source this from shell scripts. Writes ~/.personalkm/status/pipeline.json
# on EVERY exit path, even when the pipeline skips.
#
# Usage:
#   source scripts/pipeline_status.sh
#   write_phase_status "A" 0 "success" "processed=3 failed=0 skipped=7"
#   write_phase_status "A" 0 "skipped" "Vault repo has uncommitted changes"
#
# For human-readable view (call from CLI):
#   python3 src/personalkm/pipeline_status.py check
# ============================================================================

PIPELINE_STATUS_DIR="${PERSONALKM_STATUS_DIR:-$HOME/.personalkm/status}"
PIPELINE_STATUS_FILE="$PIPELINE_STATUS_DIR/pipeline.json"
PIPELINE_HISTORY_FILE="$PIPELINE_STATUS_DIR/run_history.jsonl"

# Ensure status directory exists (ALWAYS — even if script fails later)
mkdir -p "$PIPELINE_STATUS_DIR"

# ---------------------------------------------------------------------------
# Detect vault & repo state (shared by both phases)
# ---------------------------------------------------------------------------
_detect_vault_state() {
    local vault_root="${VAULT_ROOT:-$HOME/Documents/PersonalKM/Personalkm-vault}"
    local repo_root="${REPO_ROOT:-$HOME/Documents/GitHub/DannyTsao/PersonalKM}"

    local dirty=0
    local uncommitted=0
    local last_commit=""
    local last_commit_msg=""

    if [ -d "$vault_root/.git" ]; then
        pushd "$vault_root" >/dev/null 2>&1 || true
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            dirty=1
            uncommitted=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
        fi
        last_commit=$(git log --oneline -1 2>/dev/null || echo "")
        popd >/dev/null 2>&1 || true
    fi

    # Count raw files by resolvability
    local raw_count=0
    local raw_oldest_days=0
    local raw_threads=0
    local raw_facebook=0
    local raw_instagram=0
    local raw_other=0

    if [ -d "$vault_root/raw" ]; then
        raw_count=$(find "$vault_root/raw" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
        # Find oldest raw file (approximate)
        local oldest_file
        oldest_file=$(find "$vault_root/raw" -name "*.md" -print 2>/dev/null | head -1)
        if [ -n "$oldest_file" ]; then
            local oldest_epoch
            oldest_epoch=$(stat -f "%m" "$oldest_file" 2>/dev/null || echo 0)
            local now_epoch
            now_epoch=$(date +%s)
            if [ "$oldest_epoch" -gt 0 ]; then
                raw_oldest_days=$(( (now_epoch - oldest_epoch) / 86400 ))
            fi
        fi
        # Count by type (heuristic from filename)
        raw_threads=$(find "$vault_root/raw" -name "*on-threads*" -o -name "*threads*" 2>/dev/null | wc -l | tr -d ' ')
        raw_facebook=$(find "$vault_root/raw" -name "*facebook*" 2>/dev/null | wc -l | tr -d ' ')
        raw_instagram=$(find "$vault_root/raw" -name "*instagram*" -o -name "*on-instagram*" 2>/dev/null | wc -l | tr -d ' ')
        raw_other=$(( raw_count - raw_threads - raw_facebook - raw_instagram ))
        if [ "$raw_other" -lt 0 ]; then raw_other=0; fi
    fi

    local resolved_count=0
    if [ -d "$vault_root/resolved" ]; then
        resolved_count=$(find "$vault_root/resolved" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    fi

    local archive_count=0
    if [ -d "$vault_root/Archive" ]; then
        archive_count=$(find "$vault_root/Archive" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    fi

    cat <<JSON
    "vault": {
        "dirty": $dirty,
        "uncommitted_files": $uncommitted,
        "last_commit": $(echo "$last_commit" | jq -R -s '. | rtrimstr("\n")' 2>/dev/null || echo "\"$last_commit\""),
        "raw_unprocessed": $raw_count,
        "raw_oldest_days": $raw_oldest_days,
        "raw_breakdown": {
            "resolvable": $raw_other,
            "threads": $raw_threads,
            "facebook": $raw_facebook,
            "instagram": $raw_instagram
        },
        "resolved_count": $resolved_count,
        "archive_count": $archive_count
    }
JSON
}

# ---------------------------------------------------------------------------
# Detect blockers
# ---------------------------------------------------------------------------
_detect_blockers() {
    local phase="${1:-A}"
    local exit_code="${2:-0}"
    local skip_reason="${3:-}"
    local prev_exit="${4:-0}"
    local vault_dirty="${5:-0}"
    local raw_stale="${6:-0}"

    local blockers="["
    local first=true

    if [ "$vault_dirty" = "1" ]; then
        if $first; then first=false; else blockers+=","; fi
        blockers+=$(cat <<EOF
        {"severity":"high","phase":"all","reason":"Vault repo has uncommitted changes — both phases will skip on next cron tick"}
EOF
)
    fi

    if [ "$exit_code" != "0" ] && [ "$skip_reason" = "skip" ]; then
        : # skip is not a blocker by itself
    fi

    if [ "$exit_code" != "0" ] && [ "$skip_reason" != "skip" ]; then
        if $first; then first=false; else blockers+=","; fi
        blockers+=$(cat <<EOF
        {"severity":"high","phase":"$phase","reason":"Phase $ phase exited with code $exit_code"}
EOF
)
    fi

    if [ "$prev_exit" != "0" ]; then
        if $first; then first=false; else blockers+=","; fi
        blockers+=$(cat <<EOF
        {"severity":"high","phase":"all","reason":"Phase $phase previous exit was non-zero ($prev_exit) — unresolved failure"}
EOF
)
    fi

    if [ "$raw_stale" -gt 7 ]; then
        if $first; then first=false; else blockers+=","; fi
        blockers+=$(cat <<EOF
        {"severity":"medium","phase":"A","reason":"$raw_stale raw files have been unprocessed for 7+ days (oldest: $(cat /dev/stdin <<< ''; echo '?'))"}
EOF
)
    fi

    blockers+="]"
    echo "$blockers"
}

# ---------------------------------------------------------------------------
# Generate summary line
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
# Main entry point — write comprehensive status JSON
# ---------------------------------------------------------------------------
write_phase_status() {
    local phase="${1:-A}"
    local exit_code="${2:-0}"
    local status="${3:-unknown}"
    local detail="${4:-}"
    local why_skipped="${5:-}"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Detect state
    local vault_state
    vault_state=$(_detect_vault_state)

    local vault_dirty
    vault_dirty=$(echo "$vault_state" | grep -c '"dirty": 1' || true)

    local raw_count
    raw_count=$(echo "$vault_state" | grep '"raw_unprocessed"' | grep -o '[0-9]\+' || echo "0")

    # Read previous status (if any)
    local prev_exit=0
    if [ -f "$PIPELINE_STATUS_FILE" ]; then
        prev_exit=$(grep -o "\"exit_code\": [0-9]" "$PIPELINE_STATUS_FILE" 2>/dev/null | tail -1 | grep -o '[0-9]' || echo "0")
    fi

    # Build blockers list
    local blockers
    blockers=$(_detect_blockers "$phase" "$exit_code" "$status" "$prev_exit" "$vault_dirty" "$raw_count")

    # Summary
    local summary
    summary=$(_summarize "$phase" "$status" "$exit_code" "$detail")

    # Read existing file to preserve other phase's data
    local existing="{}"
    if [ -f "$PIPELINE_STATUS_FILE" ]; then
        existing=$(cat "$PIPELINE_STATUS_FILE" 2>/dev/null || echo "{}")
    fi

    # Build status JSON for THIS phase
    local phase_key="phase_$(echo "$phase" | tr 'A-Z' 'a-z')"

    # Since we can't easily merge JSON in bash, we write per-phase files and combine
    local per_phase_file="$PIPELINE_STATUS_DIR/phase_${phase}.json"
    cat > "$per_phase_file" <<PHASE_JSON
{
    "last_run": "$timestamp",
    "exit_code": $exit_code,
    "status": "$status",
    "detail": $(echo "$detail" | jq -R -s '. | rtrimstr("\n")' 2>/dev/null || echo "\"$detail\""),
    "why_skipped": $(echo "$why_skipped" | jq -R -s '. | rtrimstr("\n")' 2>/dev/null || echo "\"$why_skipped\"")
}
PHASE_JSON

    # Try to merge into full pipeline.json using Python if available
    if command -v "${PYTHON_BIN:-python3}" >/dev/null 2>&1; then
        "${PYTHON_BIN:-python3}" -c "
import json, sys, os
from pathlib import Path

status_dir = Path(os.path.expanduser('$PIPELINE_STATUS_DIR'))
pipeline_file = status_dir / 'pipeline.json'

# Load existing or start fresh
if pipeline_file.exists():
    try:
        current = json.loads(pipeline_file.read_text())
    except (json.JSONDecodeError, OSError):
        current = {}
else:
    current = {}

# Update this phase
phase_key = '$phase_key'

# Load per-phase file
phase_file = status_dir / f'phase_{phase}.json'
if phase_file.exists():
    try:
        phase_data = json.loads(phase_file.read_text())
    except (json.JSONDecodeError, OSError):
        phase_data = {}
    current[phase_key] = phase_data

# Add vault state
vault_state_str = '''$vault_state'''
try:
    import re
    # Extract the vault JSON block
    match = re.search(r'\"vault\":\s*\{.*?\}', vault_state_str, re.DOTALL)
    if match:
        current['vault'] = json.loads('{' + match.group(0) + '}')
except:
    pass

# Add blockers
blockers_str = '''$blockers'''
try:
    current['blockers'] = json.loads(blockers_str)
except:
    current['blockers'] = []

# Add summary and timestamp
current['last_updated'] = '$timestamp'
current['summary'] = '$(echo "$summary" | sed "s/'//g")'

# Count blockers
blocker_count = len(current.get('blockers', []))
raw_unproc = current.get('vault', {}).get('raw_unprocessed', 0)
vault_dirty_v = $vault_dirty
if vault_dirty_v or raw_unproc > 0 or blocker_count > 0:
    current['overall_status'] = 'degraded'
else:
    current['overall_status'] = 'healthy'

pipeline_file.write_text(json.dumps(current, indent=2, ensure_ascii=False))

# Also append to history
history_file = status_dir / 'run_history.jsonl'
history_entry = {
    'timestamp': '$timestamp',
    'phase': 'phase_$phase',
    'exit_code': $exit_code,
    'status': '$status',
    'blockers': current.get('blockers', []),
    'vault_dirty': $vault_dirty,
    'raw_unprocessed': $raw_count,
}
with history_file.open('a') as f:
    f.write(json.dumps(history_entry, ensure_ascii=False) + '\\n')
        " 2>/dev/null || {
            # Fallback: just write timestamped log
            echo "$summary" >> "$PIPELINE_STATUS_DIR/status.log"
        }
    else:
        echo "$summary" >> "$PIPELINE_STATUS_DIR/status.log"
    fi

    # Always log to system log
    log "$summary"
}

# ---------------------------------------------------------------------------
# Quick check helper (for interactive use)
# ---------------------------------------------------------------------------
pipeline_status() {
    if [ -f "$PIPELINE_STATUS_FILE" ]; then
        cat "$PIPELINE_STATUS_FILE"
    else
        echo "{\"status\": \"no_data\", \"message\": \"No pipeline status recorded yet\"}"
    fi
}