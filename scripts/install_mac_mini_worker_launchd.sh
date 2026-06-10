#!/usr/bin/env bash
set -euo pipefail

LABEL="com.dannytsao.personalkm.omnichannel-worker"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SOURCE="$REPO_ROOT/launchd/$LABEL.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/PersonalKM"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
chmod +x "$REPO_ROOT/scripts/run_mac_mini_worker.sh"
cp "$PLIST_SOURCE" "$PLIST_TARGET"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
echo "Logs:"
echo "  $LOG_DIR/omnichannel-worker.out.log"
echo "  $LOG_DIR/omnichannel-worker.err.log"
