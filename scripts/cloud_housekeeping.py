#!/usr/bin/env python3
from bot.config import get_settings
from bot.git_store import ensure_vault, run_git
from scripts.archive_inbox import archive


def main() -> None:
    settings = get_settings()
    vault_root = ensure_vault(settings)

    status = run_git(["status", "--porcelain"], vault_root, settings)
    if status:
        raise RuntimeError(f"Vault has pre-existing uncommitted changes:\n{status}")

    moves = archive(vault_root, dry_run=False)
    if not moves:
        print("No completed or trashed Inbox notes found.")
        return

    status = run_git(["status", "--porcelain"], vault_root, settings)
    if not status:
        print("Housekeeping produced no git changes.")
        return

    run_git(["commit", "-m", "Process completed inbox notes"], vault_root, settings)
    run_git(["push", "origin", settings.vault_branch], vault_root, settings)
    print(f"Processed {len(moves)} Inbox note(s).")


if __name__ == "__main__":
    main()
