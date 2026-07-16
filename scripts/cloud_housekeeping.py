#!/usr/bin/env python3
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from bot.config import get_settings
from bot.git_store import ensure_vault, run_git
from scripts.archive_inbox import archive, collect_housekeeping_report, housekeeping_report_markdown


def main() -> None:
    settings = get_settings()
    vault_root = ensure_vault(settings)

    status = run_git(["status", "--porcelain"], vault_root, settings)
    if status:
        raise RuntimeError(f"Vault has pre-existing uncommitted changes:\n{status}")

    report = collect_housekeeping_report(vault_root)
    moves = archive(vault_root, dry_run=False)

    report_dir = vault_root / "outputs" / "housekeeping"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"housekeeping-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    report_path.write_text(housekeeping_report_markdown(vault_root, report), encoding="utf-8")

    status = run_git(["status", "--porcelain"], vault_root, settings)
    if not status:
        print("Housekeeping produced no git changes.")
        return

    run_git(["commit", "-m", "Process completed inbox notes"], vault_root, settings)
    run_git(["push", "origin", settings.vault_branch], vault_root, settings)
    print(f"Processed {len(moves)} Inbox note(s). Report: {report_path.relative_to(vault_root)}")


if __name__ == "__main__":
    main()
