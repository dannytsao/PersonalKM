#!/usr/bin/env bash
set -euo pipefail

LABEL="com.dannytsao.personalkm.omnichannel-worker"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SOURCE="$REPO_ROOT/launchd/$LABEL.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/PersonalKM"
APP_SUPPORT="$HOME/Library/Application Support/PersonalKM"
WORKER_REPO="${PERSONALKM_WORKER_REPO:-$HOME/Documents/PersonalKM/Personalkm-vault}"
ORIGIN_URL="$(git -C "$REPO_ROOT" remote get-url origin)"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR" "$APP_SUPPORT" "$(dirname "$WORKER_REPO")"
chmod +x "$REPO_ROOT/scripts/run_mac_mini_worker.sh"
chmod +x "$REPO_ROOT/scripts/uninstall_mac_mini_worker_launchd.sh"
chmod +x "$REPO_ROOT/scripts/install_mac_mini_worker_launchd.sh"

if [ ! -d "$WORKER_REPO/.git" ]; then
  git clone "$ORIGIN_URL" "$WORKER_REPO"
else
  git -C "$WORKER_REPO" pull --rebase origin main
fi

cp "$REPO_ROOT/scripts/run_mac_mini_worker.sh" "$APP_SUPPORT/run_mac_mini_worker.sh"
chmod +x "$APP_SUPPORT/run_mac_mini_worker.sh"
cp "$PLIST_SOURCE" "$PLIST_TARGET"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
echo "Worker repo:"
echo "  $WORKER_REPO"
echo "Logs:"
echo "  $LOG_DIR/omnichannel-worker.out.log"
echo "  $LOG_DIR/omnichannel-worker.err.log"
