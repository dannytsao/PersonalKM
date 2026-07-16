import subprocess
from pathlib import Path

from personalkm.capture.config import Settings
from personalkm.capture.git_store import commit_and_push


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
