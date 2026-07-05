#!/usr/bin/env bash
set -euo pipefail

LABEL="com.dannytsao.personalkm.phase-b-wikilink"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SOURCE="$REPO_ROOT/launchd/$LABEL.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/PersonalKM"
APP_SUPPORT="$HOME/Library/Application Support/PersonalKM"
WORKER_REPO="${PERSONALKM_WORKER_REPO:-$HOME/Documents/PersonalKM/Personalkm-vault}"
ORIGIN_URL="$(git -C "$REPO_ROOT" remote get-url origin)"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR" "$APP_SUPPORT"

chmod +x "$REPO_ROOT/scripts/run_mac_mini_phase_b.sh"

# Copy worker repo to keep it in sync
if [ ! -d "$WORKER_REPO/.git" ]; then
    git clone "$ORIGIN_URL" "$WORKER_REPO"
else
    git -C "$WORKER_REPO" pull --rebase origin main
fi

# Copy Phase B runner script
cp "$REPO_ROOT/scripts/run_mac_mini_phase_b.sh" "$APP_SUPPORT/run_mac_mini_phase_b.sh"
chmod +x "$APP_SUPPORT/run_mac_mini_phase_b.sh"

# Copy Phase B script and Ollama wikilink module into worker repo
mkdir -p "$WORKER_REPO/scripts" "$WORKER_REPO/bot"
cp "$REPO_ROOT/scripts/post_link_ollama.py" "$WORKER_REPO/scripts/post_link_ollama.py"
cp "$REPO_ROOT/bot/ollama_wikilink.py" "$WORKER_REPO/bot/ollama_wikilink.py"
chmod +x "$WORKER_REPO/scripts/post_link_ollama.py"

cp "$PLIST_SOURCE" "$PLIST_TARGET"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
echo "Phase B repo:"
echo "  $WORKER_REPO"
echo "Logs:"
echo "  $LOG_DIR/phase-b.out.log"
echo "  $LOG_DIR/phase-b.err.log"
echo ""
echo "Interval: 3600s (1 hour)"
echo "RunAtLoad: true (fires immediately on install/wake)"
