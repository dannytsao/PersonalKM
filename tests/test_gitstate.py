import subprocess
from pathlib import Path

import pytest

from personalkm.gitstate import ensure_clean_git_state, sync_code_repo


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


@pytest.fixture
def repo_with_origin(tmp_path: Path) -> tuple[Path, Path]:
    """A repo cloned from a bare 'origin', so `git pull` has something real
    to talk to — reproduces the Mac Mini code checkout's actual setup."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    (seed / "a.md").write_text("hello\n", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "initial")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "origin", "main")

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", str(origin), str(clone)],
        text=True, capture_output=True, check=True,
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
    )
    return clone, origin


def test_sync_up_to_date_reports_status_without_pulling(repo_with_origin):
    clone, _origin = repo_with_origin
    result = sync_code_repo(clone, "main")
    assert result["status"] == "up_to_date"
    assert result["repair_actions"] == []


def test_sync_pulls_new_commit_from_origin(repo_with_origin):
    clone, origin = repo_with_origin
    # Push a new commit to origin from a second clone (simulates a fix
    # merged on GitHub after the Mac Mini checkout was last synced).
    second = origin.parent / "second"
    subprocess.run(
        ["git", "clone", str(origin), str(second)],
        text=True, capture_output=True, check=True,
        env={"HOME": str(origin.parent), "PATH": "/usr/bin:/bin"},
    )
    (second / "b.md").write_text("new fix\n", encoding="utf-8")
    _git(second, "add", "-A")
    _git(second, "commit", "-m", "fix landed on main")
    _git(second, "push", "origin", "main")

    before = _git(clone, "rev-parse", "HEAD")
    result = sync_code_repo(clone, "main")
    after = _git(clone, "rev-parse", "HEAD")

    assert result["status"] == "pulled"
    assert before != after
    assert (clone / "b.md").exists()


def test_sync_never_raises_when_origin_unreachable(repo_with_origin):
    clone, origin = repo_with_origin
    import shutil
    shutil.rmtree(origin)  # simulate offline/unreachable remote

    result = sync_code_repo(clone, "main")

    assert result["status"] == "skipped"
    assert "detail" in result


def test_sync_repairs_detached_head_before_pulling(repo_with_origin):
    clone, _origin = repo_with_origin
    head = _git(clone, "rev-parse", "HEAD")
    _git(clone, "checkout", head)  # detach, matching a stranded checkout

    result = sync_code_repo(clone, "main")

    assert "checked_out_branch" in result["repair_actions"]
    assert _git(clone, "branch", "--show-current") == "main"
