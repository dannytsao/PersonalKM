import os
import subprocess
from pathlib import Path

from personalkm.capture.config import Settings


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
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            text=True,
            check=True,
            capture_output=True,
        )
        return completed.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Log stderr so we can see the actual git error in Render logs
        import logging
        stderr = (e.stderr or "").strip()
        stdout = (e.stdout or "").strip()
        logging.getLogger(__name__).error(
            "git %s failed (exit %d)\nstdout: %s\nstderr: %s",
            " ".join(args), e.returncode, stdout[:500], stderr[:500],
        )
        raise GitError(e.returncode, e.cmd, output=e.stdout, stderr=e.stderr)


class GitError(subprocess.CalledProcessError):
    """Extends CalledProcessError to include stderr in the message."""

    def __str__(self) -> str:
        orig = super().__str__()
        stderr = (self.stderr or "").strip()
        if stderr:
            return f"{orig}\nstderr: {stderr}"
        return orig


def _try_repair_and_checkout(vault_path: Path, settings: Settings) -> bool:
    """Try to repair a broken git repo and checkout the target branch.

    Returns True if checkout succeeded, False if fresh clone is needed.
    """
    try:
        run_git(["fetch", "origin", settings.vault_branch], vault_path, settings)
        run_git(["checkout", settings.vault_branch, "--", "raw/"], vault_path, settings)
        return True
    except Exception:
        import logging
        logging.getLogger(__name__).debug("Repair attempt 1 failed", exc_info=True)

    # Try harder: clean up working tree and orphaned state
    try:
        run_git(["read-tree", "--empty"], vault_path, settings)
        run_git(["checkout", settings.vault_branch, "--", "raw/"], vault_path, settings)
        return True
    except Exception:
        import logging
        logging.getLogger(__name__).debug("Repair attempt 2 failed", exc_info=True)

    return False


def ensure_vault(settings: Settings) -> Path:
    vault_path = settings.vault_path
    if (vault_path / ".git").exists():
        if _try_repair_and_checkout(vault_path, settings):
            return vault_path
        # Repair failed — remove and re-clone
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Vault git repair failed — removing %s for fresh clone", vault_path)
        for attempt in range(3):
            try:
                import shutil
                shutil.rmtree(vault_path)
                break
            except OSError as e:
                logger.warning("rmtree attempt %d failed: %s", attempt + 1, e)
                if attempt < 2:
                    import time
                    time.sleep(1)
                else:
                    import shutil
                    shutil.rmtree(vault_path, ignore_errors=True)

    if not settings.vault_repo_url:
        raise RuntimeError("VAULT_REPO_URL is required when VAULT_PATH is not an existing git repo.")

    vault_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Clone without checkout to avoid "File name too long" errors on wiki/entities
        # (Render's /tmp filesystem has a 255-byte filename limit)
        run_git(
            ["clone", "--branch", settings.vault_branch, "--no-checkout", "--depth", "1",
             settings.vault_repo_url, str(vault_path)],
            Path.cwd(), settings,
        )
        # Only checkout the raw/ directory — that's all capture_line_messages needs
        run_git(["checkout", settings.vault_branch, "--", "raw/"], vault_path, settings)
    except subprocess.CalledProcessError:
        raise  # re-raise so the caller sees the error with stderr
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
