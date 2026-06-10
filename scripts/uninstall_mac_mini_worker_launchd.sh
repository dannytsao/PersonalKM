#!/usr/bin/env bash
set -euo pipefail

LABEL="com.dannytsao.personalkm.omnichannel-worker"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" >/dev/null 2>&1 || true
rm -f "$PLIST_TARGET"

echo "Uninstalled $LABEL"
