#!/usr/bin/env bash
# Split the vault (raw/ wiki/ Attachments/ Trash/) out of the current
# PersonalKM repo into a NEW PRIVATE repo, preserving its git history,
# then remove content from the code repo.
#
# Run this ON YOUR MAC, not in CI. Requires: git, git-filter-repo
#   brew install git-filter-repo
#
# It never touches your existing repo in place — it works on fresh clones,
# so nothing is destroyed until you push and verify.
set -euo pipefail

SRC_REPO_URL="git@github.com:dannytsao/PersonalKM.git"
WORK="$HOME/personalkm-migration"
CONTENT_PATHS=(raw wiki Attachments Trash)

echo "==> Working in $WORK"
rm -rf "$WORK" && mkdir -p "$WORK" && cd "$WORK"

# ---------------------------------------------------------------
# 1. Vault repo: clone, keep ONLY content paths (history preserved)
# ---------------------------------------------------------------
git clone "$SRC_REPO_URL" vault && cd vault
ARGS=(); for p in "${CONTENT_PATHS[@]}"; do ARGS+=(--path "$p"); done
git filter-repo "${ARGS[@]}" --force
mkdir -p wiki/_registry
[ -f wiki/_registry/entities.yaml ] || cat > wiki/_registry/entities.yaml << 'EOF'
# Canonical entity registry (moved out of Python code).
# Pipeline reads this file; LLM-proposed entities land under `proposed:`
# and are promoted to `entities:` manually or by confidence threshold.
entities: []      # TODO: paste your 34 canonical slugs here
proposed: []
EOF
git add -A && git commit -m "vault: add entity registry" || true
cd ..

echo ""
echo "==> NOW (manual): create a PRIVATE repo on GitHub, e.g. personalkm-vault"
read -rp "    Enter its SSH url (e.g. git@github.com:dannytsao/personalkm-vault.git): " VAULT_URL
cd vault
git remote add origin "$VAULT_URL"
git push -u origin main
cd ..

# ---------------------------------------------------------------
# 2. Code repo: clone, strip content paths from history
#    (this rewrites history -> requires force push; backup happens
#     implicitly because your original clone still exists)
# ---------------------------------------------------------------
git clone "$SRC_REPO_URL" code && cd code
ARGS=(); for p in "${CONTENT_PATHS[@]}"; do ARGS+=(--path "$p"); done
git filter-repo "${ARGS[@]}" --invert-paths --force
git remote add origin "$SRC_REPO_URL"
echo ""
echo "==> Review the stripped code repo in $WORK/code, then force-push:"
echo "    cd $WORK/code && git push --force origin main"
echo ""
echo "==> Finally, on the Mac Mini:"
echo "    git clone $VAULT_URL ~/.personalkm/personalkm-vault"
echo "    and point config/settings.yaml vault.path at it."
echo "    Update launchd scripts: pull/push the VAULT repo for content,"
echo "    the CODE repo only when deploying code changes."
