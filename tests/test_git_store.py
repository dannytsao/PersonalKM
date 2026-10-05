import subprocess
from pathlib import Path

from personalkm.capture.config import Settings
from personalkm.capture.git_store import _inject_pat, _get_vault_config, commit_and_push, ensure_vault


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        check=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def test_commit_and_push_clears_stale_index_before_staging_note(tmp_path):
    # Given: a vault clone whose index already has unrelated staged changes.
    remote = tmp_path / "remote.git"
    vault = tmp_path / "vault"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(vault)], check=True, capture_output=True)
    git(vault, "config", "user.name", "Test Bot")
    git(vault, "config", "user.email", "bot@example.com")
    git(vault, "remote", "add", "origin", str(remote))

    raw = vault / "raw"
    obsidian = vault / ".obsidian"
    archive = vault / "Archive" / "General"
    raw.mkdir()
    obsidian.mkdir()
    archive.mkdir(parents=True)
    (raw / "existing.md").write_text("# Existing\n", encoding="utf-8")
    (obsidian / "graph.json").write_text("{}\n", encoding="utf-8")
    (archive / "old.md").write_text("# Old\n", encoding="utf-8")
    git(vault, "add", ".")
    git(vault, "commit", "-m", "Initial vault")
    git(vault, "push", "-u", "origin", "main")

    (obsidian / "graph.json").write_text('{"changed": true}\n', encoding="utf-8")
    (archive / "old.md").write_text("# Changed\n", encoding="utf-8")
    git(vault, "add", ".obsidian/graph.json", "Archive/General/old.md")

    note_path = raw / "new.md"
    note_path.write_text("# New LINE note\n", encoding="utf-8")
    settings = Settings(
        VAULT_PATH=vault,
        VAULT_REPO_URL=str(remote),
        VAULT_BRANCH="main",
        GIT_AUTHOR_NAME="Test Bot",
        GIT_AUTHOR_EMAIL="bot@example.com",
    )

    # When: committing the one new raw note.
    commit_and_push(settings, note_path)

    # Then: only that note is included in the pushed commit.
    changed_files = git(vault, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert changed_files == ["raw/new.md"]


def test_ensure_vault_advances_head_before_capture_commit(tmp_path):
    # Given: Render's reused vault clone is behind origin/main.
    remote = tmp_path / "remote.git"
    vault = tmp_path / "vault"
    other = tmp_path / "other"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(vault)], check=True, capture_output=True)
    git(vault, "config", "user.name", "Test Bot")
    git(vault, "config", "user.email", "bot@example.com")
    git(vault, "remote", "add", "origin", str(remote))

    raw = vault / "raw"
    raw.mkdir()
    (raw / "existing.md").write_text("# Existing\n", encoding="utf-8")
    git(vault, "add", ".")
    git(vault, "commit", "-m", "Initial vault")
    git(vault, "push", "-u", "origin", "main")

    subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
    git(other, "config", "user.name", "Other Bot")
    git(other, "config", "user.email", "other@example.com")
    (other / "raw" / "remote.md").write_text("# Remote note\n", encoding="utf-8")
    git(other, "add", "raw/remote.md")
    git(other, "commit", "-m", "Remote capture")
    git(other, "push", "origin", "main")

    settings = Settings(
        VAULT_PATH=vault,
        VAULT_REPO_URL=str(remote),
        VAULT_BRANCH="main",
        GIT_AUTHOR_NAME="Test Bot",
        GIT_AUTHOR_EMAIL="bot@example.com",
    )

    # When: the webhook prepares the reused vault, writes a note, and pushes.
    ensure_vault(settings)
    assert git(vault, "rev-parse", "HEAD") == git(vault, "rev-parse", "origin/main")

    note_path = raw / "new.md"
    note_path.write_text("# New LINE note\n", encoding="utf-8")
    commit_and_push(settings, note_path)

    # Then: the local commit is based on the remote capture and push succeeds.
    history = git(vault, "log", "--oneline", "-3")
    assert "Remote capture" in history
    assert "Add LINE link note: new" in history
    assert git(vault, "rev-parse", "HEAD") == git(vault, "rev-parse", "origin/main")


# --------------------------------------------------------------------------- #
# _inject_pat — PAT injected at runtime, base URL safe in render.yaml
# --------------------------------------------------------------------------- #

class TestInjectPat:
    """Contract: _inject_pat keeps base URL intact, injects PAT as x-access-token."""

    def test_injects_pat_into_bare_url(self):
        url = "https://github.com/dannytsao/Personalkm-lifestyle-vault.git"
        pat = "github_pat_ABC123"
        result = _inject_pat(url, pat)
        assert result == "https://x-access-token:github_pat_ABC123@github.com/dannytsao/Personalkm-lifestyle-vault.git"

    def test_empty_pat_returns_url_unchanged(self):
        url = "https://github.com/dannytsao/Personalkm-lifestyle-vault.git"
        assert _inject_pat(url, "") == url

    def test_replaces_existing_credentials(self):
        url = "https://olduser:oldpass@github.com/dannytsao/repo.git"
        pat = "github_pat_NEW"
        result = _inject_pat(url, pat)
        assert "olduser" not in result
        assert "oldpass" not in result
        assert "x-access-token:github_pat_NEW@" in result

    def test_non_https_left_alone(self):
        url = "git@github.com:dannytsao/repo.git"
        pat = "github_pat_ABC"
        assert _inject_pat(url, pat) == url


class TestGetVaultConfigPatInjection:
    """Contract: _get_vault_config injects PAT from settings into the URL at runtime."""

    def test_lifestyle_config_injects_pat(self):
        settings = Settings(
            LIFESTYLE_VAULT_REPO_URL="https://github.com/dannytsao/Personalkm-lifestyle-vault.git",
            LIFESTYLE_VAULT_PAT="github_pat_TEST",
        )
        vc = _get_vault_config(settings, "food")
        assert "x-access-token:github_pat_TEST@" in vc.repo_url
        assert vc.branch == "main"

    def test_tech_config_injects_pat(self):
        settings = Settings(
            VAULT_REPO_URL="https://github.com/dannytsao/PersonalKM.git",
            VAULT_PAT="github_pat_TECH",
        )
        vc = _get_vault_config(settings, "tech")
        assert "x-access-token:github_pat_TECH@" in vc.repo_url

    def test_no_pat_falls_back_gracefully(self):
        """When PAT is empty, URL is used as-is (backward compatible)."""
        settings = Settings(
            VAULT_REPO_URL="https://github.com/dannytsao/PersonalKM.git",
        )
        vc = _get_vault_config(settings, "tech")
        assert vc.repo_url == "https://github.com/dannytsao/PersonalKM.git"
