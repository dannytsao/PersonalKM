import os
import subprocess
from pathlib import Path

from bot.config import Settings


def run_git(args: list[str], cwd: Path, settings: Settings) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": settings.git_author_name,
            "GIT_AUTHOR_EMAIL": settings.git_author_email,
            "GIT_COMMITTER_NAME": settings.git_author_name,
            "GIT_COMMITTER_EMAIL": settings.git_author_email,
        }
    )
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        check=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def ensure_vault(settings: Settings) -> Path:
    vault_path = settings.vault_path
    if (vault_path / ".git").exists():
        run_git(["fetch", "origin", settings.vault_branch], vault_path, settings)
        run_git(["checkout", settings.vault_branch], vault_path, settings)
        run_git(["pull", "--ff-only", "origin", settings.vault_branch], vault_path, settings)
        return vault_path

    if not settings.vault_repo_url:
        raise RuntimeError("VAULT_REPO_URL is required when VAULT_PATH is not an existing git repo.")

    vault_path.parent.mkdir(parents=True, exist_ok=True)
    run_git(["clone", "--branch", settings.vault_branch, settings.vault_repo_url, str(vault_path)], Path.cwd(), settings)
    return vault_path


def commit_and_push(settings: Settings, note_path: Path) -> None:
    vault_path = settings.vault_path
    relative_path = note_path.relative_to(vault_path)
    run_git(["add", str(relative_path)], vault_path, settings)

    status = run_git(["status", "--porcelain"], vault_path, settings)
    if not status:
        return

    run_git(["commit", "-m", f"Add LINE link note: {note_path.stem}"], vault_path, settings)
    run_git(["push", "origin", settings.vault_branch], vault_path, settings)
