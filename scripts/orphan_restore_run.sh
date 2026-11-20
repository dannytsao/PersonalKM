#!/bin/bash
# PersonalKM orphan restore — moves all orphaned Archive/raw notes back to raw/ and re-ingests both vaults.
set -e
BASE="$HOME/Documents/PersonalKM"
REPO="$HOME/Documents/GitHub/DannyTsao/PersonalKM"
source ~/.personalkm/worker.secrets 2>/dev/null || true

restore() {  # $1 = vault path
  python3 - "$1" <<'PY'
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path.home()/"Documents/GitHub/DannyTsao/PersonalKM/src"))
from personalkm.ingest.archive_integrity import find_archive_orphans
root = Path(sys.argv[1])
orphs = find_archive_orphans(root)
n = 0
for o in orphs:
    src = root/"Archive/raw"/(o+".md"); dst = root/"raw"/(o+".md")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst)); n += 1
print(f"{root.name}: moved {n} orphans to raw/")
PY
}

restore "$BASE/Personalkm-vault"
restore "$BASE/Personalkm-lifestyle-vault"

for V in Personalkm-vault Personalkm-lifestyle-vault; do
  echo "=== Ingesting $V ==="
  "$REPO/.venv/bin/python3" "$REPO/scripts/ingest_wiki.py" --vault "$BASE/$V"
done
echo "DONE. Verify with: python3 -m personalkm.pipeline_status check"
