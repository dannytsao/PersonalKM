import subprocess
from pathlib import Path

import pytest

from personalkm.gitstate import ensure_clean_git_state


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
             "HOME": str(repo), "PATH": "/usr/bin:/bin"},
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "vault"
    r.mkdir()
    _git(r, "init", "-b", "main")
    (r / "a.md").write_text("hello\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "initial")
    return r


def test_clean_repo_is_left_untouched(repo: Path):
    assert ensure_clean_git_state(repo, "main") == []
    assert _git(repo, "branch", "--show-current") == "main"


def test_stale_rebase_is_aborted(repo: Path):
    # Manufacture a real stopped rebase: two branches with a conflicting file.
    _git(repo, "checkout", "-b", "other")
    (repo / "a.md").write_text("other version\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "other change")
    _git(repo, "checkout", "main")
    (repo / "a.md").write_text("main version\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "main change")
    result = subprocess.run(
        ["git", "rebase", "other"], cwd=repo, text=True, capture_output=True,
    )
    assert result.returncode != 0  # rebase must have stopped on the conflict
    assert (repo / ".git" / "rebase-merge").exists() or (repo / ".git" / "rebase-apply").exists()

    actions = ensure_clean_git_state(repo, "main")

    assert "aborted_rebase" in actions
    assert not (repo / ".git" / "rebase-merge").exists()
    assert not (repo / ".git" / "rebase-apply").exists()
    assert _git(repo, "branch", "--show-current") == "main"


def test_detached_head_commits_are_rescued_then_branch_restored(repo: Path):
    # Simulate the 2026-07-22 incident: commits made on a detached HEAD.
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", head)
    (repo / "stranded.md").write_text("stranded work\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "stranded cron commit")
    stranded = _git(repo, "rev-parse", "HEAD")

    actions = ensure_clean_git_state(repo, "main")

    assert any(a.startswith("rescued_to:") for a in actions)
    assert "checked_out_branch" in actions
    assert _git(repo, "branch", "--show-current") == "main"
    # The stranded commit must be reachable from the rescue branch.
    rescue = next(a.split(":", 1)[1] for a in actions if a.startswith("rescued_to:"))
    assert _git(repo, "rev-parse", rescue) == stranded


def test_stopped_rebase_with_stacked_commits_rescues_before_abort(repo: Path):
    # The full 2026-07-22 incident shape: a pull-rebase stops on a conflict,
    # is never aborted, and hourly cron runs then stack commits on the
    # stopped rebase's detached HEAD. A naive `rebase --abort` would orphan
    # those commits — they must be parked on a rescue branch first.
    _git(repo, "checkout", "-b", "other")
    (repo / "a.md").write_text("other version\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "other change")
    _git(repo, "checkout", "main")
    (repo / "a.md").write_text("main version\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "main change")
    result = subprocess.run(
        ["git", "rebase", "other"], cwd=repo, text=True, capture_output=True,
    )
    assert result.returncode != 0
    # Cron keeps working on the stopped rebase's HEAD (resolve the
    # conflicted file just enough to commit new work on top).
    (repo / "a.md").write_text("cron overwrote\n", encoding="utf-8")
    (repo / "cron-work.md").write_text("hourly output\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "stranded cron commit")
    stranded = _git(repo, "rev-parse", "HEAD")

    actions = ensure_clean_git_state(repo, "main")

    assert any(a.startswith("rescued_to:") for a in actions)
    assert "aborted_rebase" in actions
    assert _git(repo, "branch", "--show-current") == "main"
    rescue = next(a.split(":", 1)[1] for a in actions if a.startswith("rescued_to:"))
    assert _git(repo, "rev-parse", rescue) == stranded


def test_detached_head_at_branch_tip_needs_no_rescue_branch(repo: Path):
    # Detached but pointing at a commit already on main: just re-attach.
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", head)

    actions = ensure_clean_git_state(repo, "main")

    assert actions == ["checked_out_branch"]
    assert _git(repo, "branch", "--show-current") == "main"
    assert not [b for b in _git(repo, "branch").splitlines() if "rescue" in b]
