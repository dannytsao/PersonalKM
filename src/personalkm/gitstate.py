"""
Git working-state guard for the vault repo (IMPROVEMENT-BACKLOG.md P7#29).

2026-07-22 incident: a cron `git pull --rebase` stopped on a conflict and
was never aborted, leaving the vault on a detached HEAD with
`.git/rebase-merge` in place. Every subsequent hourly cron run then
committed onto that detached HEAD for ~12 hours — work that could never be
pushed — while origin/main moved ahead. Nothing in the pipeline detected
or recovered from this.

`ensure_clean_git_state()` runs before any cron git work and repairs the
two stranded states this incident produced:

1. Rebase in progress (`.git/rebase-merge` / `.git/rebase-apply` exists):
   abort it. A cron repo should never be mid-rebase between runs — a
   leftover rebase dir is always a previous run's failure, not someone's
   work in progress (the runner lock already prevents concurrent runs).
2. Detached HEAD with local commits (after an abort, or from an older
   incident): park the commits on a timestamped rescue branch so nothing
   is lost, then check out the target branch. The rescue branch is left
   for a human to merge — an automated merge of unknown stranded work is
   how content gets silently mangled.
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=False
    )


def _rebase_in_progress(repo: Path) -> bool:
    git_dir = repo / ".git"
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def _is_detached(repo: Path) -> bool:
    return _git(repo, "symbolic-ref", "-q", "HEAD").returncode != 0


def ensure_clean_git_state(repo: Path, branch: str = "main") -> list[str]:
    """
    Detect and repair a stranded rebase / detached HEAD before cron git work.

    Returns the list of repair actions taken (empty when already clean):
    "aborted_rebase", "rescued_to:<branch-name>", "checked_out_branch".
    Raises RuntimeError if the repo is stranded and repair failed — callers
    must treat that as "skip this cycle", never proceed to commit.
    """
    actions: list[str] = []

    if _rebase_in_progress(repo):
        # Rescue BEFORE aborting: in the 2026-07-22 incident, hourly cron
        # runs had stacked commits on the stopped rebase's detached HEAD.
        # `rebase --abort` resets HEAD back to the original branch, which
        # would orphan those commits — park them on a branch first.
        rescued = _rescue_unreachable_head(repo, branch)
        if rescued:
            actions.append(f"rescued_to:{rescued}")

        logger.warning("Stale rebase in progress detected in %s — aborting it", repo)
        result = _git(repo, "rebase", "--abort")
        if _rebase_in_progress(repo):
            raise RuntimeError(
                f"git rebase --abort failed in {repo}: {result.stderr.strip()}"
            )
        actions.append("aborted_rebase")

    if _is_detached(repo):
        rescued = _rescue_unreachable_head(repo, branch)
        if rescued:
            actions.append(f"rescued_to:{rescued}")

        result = _git(repo, "checkout", branch)
        if result.returncode != 0:
            raise RuntimeError(
                f"could not check out {branch} in {repo}: {result.stderr.strip()}"
            )
        actions.append("checked_out_branch")

    return actions


def _rescue_unreachable_head(repo: Path, branch: str) -> str | None:
    """Park HEAD on a timestamped rescue branch if it holds commits not
    reachable from *branch*. Returns the rescue branch name, or None if
    HEAD is already contained in the branch (nothing to lose)."""
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    if _git(repo, "merge-base", "--is-ancestor", head, branch).returncode == 0:
        return None
    rescue = f"rescue/detached-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    result = _git(repo, "branch", rescue, head)
    if result.returncode != 0:
        raise RuntimeError(
            f"could not create rescue branch in {repo}: {result.stderr.strip()}"
        )
    logger.warning(
        "HEAD in %s holds commits not on %s — parked on %s for manual merge",
        repo, branch, rescue,
    )
    return rescue
