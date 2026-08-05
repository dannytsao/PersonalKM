import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from personalkm.capture.config import Settings


@dataclass(frozen=True)
class VaultConfig:
    """Configuration for a single vault repo."""
    repo_url: str = ""
    branch: str = "main"
    path: Path = Path("/tmp/personal-km-vault")


def _get_vault_config(settings: Settings, category: str = "tech") -> VaultConfig:
    """Return the vault config for a given category.

    Falls back to tech vault if lifestyle vault is not configured.
    """
    is_lifestyle = category in ("food", "photography") and settings.lifestyle_vault_repo_url
    if is_lifestyle:
        return VaultConfig(
            repo_url=settings.lifestyle_vault_repo_url,
            branch=settings.lifestyle_vault_branch,
            path=settings.lifestyle_vault_path,
        )
    return VaultConfig(
        repo_url=settings.vault_repo_url,
        branch=settings.vault_branch,
        path=settings.vault_path,
    )


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


def _is_non_fast_forward(error: GitError) -> bool:
    stderr = (error.stderr or "").lower()
    return "non-fast-forward" in stderr or "fetch first" in stderr


def _push_with_rebase(vault_path: Path, settings: Settings, vault_config: VaultConfig) -> None:
    try:
        run_git(["push", "origin", vault_config.branch], vault_path, settings)
    except GitError as e:
        if not _is_non_fast_forward(e):
            raise
        import logging
        logging.getLogger(__name__).warning(
            "Vault push rejected as non-fast-forward; rebasing onto origin/%s",
            vault_config.branch,
        )
        run_git(["fetch", "origin", vault_config.branch], vault_path, settings)
        run_git(["rebase", f"origin/{vault_config.branch}"], vault_path, settings)
        run_git(["push", "origin", vault_config.branch], vault_path, settings)


def _try_repair_and_checkout(vault_path: Path, settings: Settings, vault_config: VaultConfig) -> bool:
    """Try to repair a broken git repo and checkout the target branch.

    Returns True if checkout succeeded, False if fresh clone is needed.
    """
    try:
        run_git(["fetch", "origin", vault_config.branch], vault_path, settings)
        run_git(["sparse-checkout", "init", "--cone"], vault_path, settings)
        run_git(["sparse-checkout", "set", "raw/"], vault_path, settings)
        run_git(["reset", "--hard", f"origin/{vault_config.branch}"], vault_path, settings)
        return True
    except Exception:
        import logging
        logging.getLogger(__name__).debug("Repair attempt 1 failed", exc_info=True)

    try:
        run_git(["read-tree", "--empty"], vault_path, settings)
        run_git(["reset", "--soft", f"origin/{vault_config.branch}"], vault_path, settings)
        run_git(["sparse-checkout", "init", "--cone"], vault_path, settings)
        run_git(["sparse-checkout", "set", "raw/"], vault_path, settings)
        run_git(["checkout", f"origin/{vault_config.branch}"], vault_path, settings)
        return True
    except Exception:
        import logging
        logging.getLogger(__name__).debug("Repair attempt 2 failed", exc_info=True)

    return False


def ensure_vault(settings: Settings, vault_config: Optional[VaultConfig] = None) -> Path:
    """Ensure the vault repo is cloned and ready.

    Uses the provided vault_config, or falls back to settings.vault_*.
    Returns the vault path.
    """
    vc = vault_config or VaultConfig(
        repo_url=settings.vault_repo_url,
        branch=settings.vault_branch,
        path=settings.vault_path,
    )
    vault_path = vc.path

    if (vault_path / ".git").exists():
        if _try_repair_and_checkout(vault_path, settings, vc):
            return vault_path
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

    if not vc.repo_url:
        raise RuntimeError("VAULT_REPO_URL is required when VAULT_PATH is not an existing git repo.")

    vault_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Sparse clone: only raw/ is materialized in the working tree.
        # Using git sparse-checkout avoids the phantom-deletion problem
        # where non-raw files (wiki/, etc.) show up as deleted in
        # `git status` because they exist in HEAD but not on disk.
        run_git(
            ["clone", "--branch", vc.branch, "--no-checkout", "--depth", "1",
             "--filter=blob:none", "--sparse", vc.repo_url, str(vault_path)],
            Path.cwd(), settings,
        )
        run_git(["sparse-checkout", "init", "--cone"], vault_path, settings)
        run_git(["sparse-checkout", "set", "raw/"], vault_path, settings)
        run_git(["checkout", vc.branch], vault_path, settings)
    except subprocess.CalledProcessError:
        raise
    return vault_path


def commit_and_push(settings: Settings, note_path: Path, vault_config: Optional[VaultConfig] = None) -> None:
    """Commit and push a single note file to the vault.

    Uses --only to commit ONLY the specified file, ignoring any other staged
    changes (e.g. phantom deletions from sparse checkout index state).
    """
    vc = vault_config or VaultConfig(
        repo_url=settings.vault_repo_url,
        branch=settings.vault_branch,
        path=settings.vault_path,
    )
    vault_path = vc.path
    relative_path = note_path.relative_to(vault_path)

    run_git(["reset", "HEAD", "--", "."], vault_path, settings)
    run_git(["add", str(relative_path)], vault_path, settings)

    staged_check = run_git(
        ["diff", "--cached", "--name-only", "--", str(relative_path)],
        vault_path, settings,
    )
    if not staged_check.strip():
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("File %s not staged — skipping commit", relative_path)
        return

    staged_all = run_git(["diff", "--cached", "--name-only"], vault_path, settings)
    staged_lines = len(staged_all.splitlines()) if staged_all else 0
    if staged_lines > 2:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            "ABORTING commit: %d files staged (expected 1). "
            "Index state is corrupted — refusing to commit.",
            staged_lines,
        )
        logger.error("Staged files: %s", staged_all[:2000])
        raise RuntimeError(
            f"Refusing to commit {staged_lines} files — aborting to protect vault. "
            f"Staged: {staged_all[:200]}"
        )

    run_git(["commit", "--only", str(relative_path),
             "-m", f"Add LINE link note: {note_path.stem}"], vault_path, settings)
    _push_with_rebase(vault_path, settings, vc)

    import logging
    logging.getLogger(__name__).info(
        "✅ Pushed %s to vault %s", relative_path, vc.branch,
    )