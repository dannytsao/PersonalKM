#!/usr/bin/env bash
# Temporarily move repos outside ~/Documents/ to bypass macOS TCC
# for launchd background runs.
set -euo pipefail

NEW_CODE="$HOME/.local/share/PersonalKM"
NEW_VAULT="$HOME/.local/share/Personalkm-vault"
OLD_CODE="$HOME/Documents/GitHub/DannyTsao/PersonalKM"
OLD_VAULT="$HOME/Documents/PersonalKM/Personalkm-vault"

echo "This will move repos from ~/Documents/ to ~/.local/share/"
echo "  Code:  $OLD_CODE → $NEW_CODE"
echo "  Vault: $OLD_VAULT → $NEW_VAULT"
echo ""
echo "Then update:"
echo "  - launchd plists (env vars)"
echo "  - PERSOANALKM_REPO_ROOT / VAULT_ROOT"
echo "  - Obsidian vault path"
echo "  - worker.secrets"
echo ""
echo "Run? (Ctrl+C to cancel)"
read -r

# --- Move vault first ---
mkdir -p "$(dirname "$NEW_VAULT")"
mv "$OLD_VAULT" "$NEW_VAULT"

# --- Move code repo ---
mkdir -p "$(dirname "$NEW_CODE")"
mv "$OLD_CODE" "$NEW_CODE"

# --- Update plist env vars ---
for label in phase-a-ingest phase-b-wikilink; do
    PLIST="$HOME/Library/LaunchAgents/com.dannytsao.personalkm.$label.plist"
    sed -i '' "s|$OLD_CODE|$NEW_CODE|g" "$PLIST"
    sed -i '' "s|$OLD_VAULT|$NEW_VAULT|g" "$PLIST"
done

# --- Update shell scripts ---
for script in "$NEW_CODE/scripts/run_mac_mini_phase_"*.sh; do
    sed -i '' "s|REPO_ROOT=\"\${PERSONALKM_REPO_ROOT:-$OLD_CODE}\"|REPO_ROOT=\"\${PERSONALKM_REPO_ROOT:-$NEW_CODE}\"|g" "$script"
    sed -i '' "s|VAULT_ROOT=\"\${PERSONALKM_VAULT_ROOT:-$OLD_VAULT}\"|VAULT_ROOT=\"\${PERSONALKM_VAULT_ROOT:-$NEW_VAULT}\"|g" "$script"
    cp "$script" "$HOME/Library/Application Support/PersonalKM/"
done

echo "Done! Reload launchd to test."
echo "Also update ~/.personalkm/worker.secrets if it has old paths."