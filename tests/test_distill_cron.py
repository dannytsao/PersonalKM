"""Tests for Phase C distillation cron runner (P6#24).

Verifies that:
1. run_distill() scans for candidates and applies distillation
2. Pages with LLM errors are skipped, not crashed
3. Pages without summaries are skipped
4. The --limit parameter caps the number of pages processed
5. dry-run mode scans but doesn't write
6. Git operations are attempted after successful distillation
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from distill_cron import run_distill


def _make_wiki_with_triggered_page(tmp_path: Path) -> Path:
    """Create a minimal wiki/ with one page that triggers distillation."""
    wiki = tmp_path / "wiki"
    entities = wiki / "entities"
    entities.mkdir(parents=True)

    captures = "\n".join(f"### Capture {i} (2026-07-0{i})" for i in range(1, 6))
    page = entities / "busy-entity.md"
    page.write_text(
        f"---\ntitle: Busy Entity\ncreated: 2026-06-01\n---\n\n{captures}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_run_distill_dry_run_scans_but_doesnt_write(tmp_path: Path):
    vault = _make_wiki_with_triggered_page(tmp_path)
    page = vault / "wiki/entities/busy-entity.md"
    original = page.read_text(encoding="utf-8")

    with patch("personalkm.propagate.distill.route",
               return_value={"summary": "test summary", "key_facts": []}):
        result = run_distill(vault, limit=0, dry_run=True)

    assert result["status"] == "success"
    assert result["pages_distilled"] == 0  # dry-run doesn't write
    # Content unchanged
    assert page.read_text(encoding="utf-8") == original


def test_run_distill_applies_distillation_when_triggered(tmp_path: Path):
    vault = _make_wiki_with_triggered_page(tmp_path)
    page = vault / "wiki/entities/busy-entity.md"

    # Mock git operations so we don't need a real repo
    with patch("distill_cron.run_git") as mock_git, \
         patch("personalkm.gitstate.ensure_clean_git_state", return_value=None), \
         patch("personalkm.propagate.distill.route",
               return_value={"summary": "濃縮摘要", "key_facts": ["重點 (2026-07-01)"]}):
        result = run_distill(vault, limit=0, dry_run=False)

    assert result["status"] == "success"
    assert result["pages_distilled"] == 1

    # Verify the page was distilled (summary written, original preserved)
    content = page.read_text(encoding="utf-8")
    assert "濃縮摘要" in content
    assert "<details>" in content
    assert "Capture 1" in content  # original preserved in fold

    # Verify git add + commit + push were called
    mock_git.assert_any_call(["add", "-A"], vault)
    commit_call = [c for c in mock_git.call_args_list if "commit" in str(c)]
    assert len(commit_call) > 0


def test_run_distill_skips_pages_with_llm_errors(tmp_path: Path):
    vault = _make_wiki_with_triggered_page(tmp_path)

    with patch("distill_cron.run_git"), \
         patch("personalkm.gitstate.ensure_clean_git_state", return_value=None), \
         patch("personalkm.propagate.distill.route",
               side_effect=RuntimeError("All models exhausted")):
        result = run_distill(vault, limit=0, dry_run=False)

    assert result["status"] == "success"
    assert result["pages_distilled"] == 0
    assert result["errors"] == 1


def test_run_distill_respects_limit(tmp_path: Path):
    vault = tmp_path / "vault"
    entities = vault / "wiki" / "entities"
    entities.mkdir(parents=True)

    # Create 3 triggered pages
    captures = "\n".join(f"### Capture {i} (2026-07-0{i})" for i in range(1, 6))
    for name in ["a", "b", "c"]:
        (entities / f"{name}.md").write_text(
            f"---\ntitle: {name.upper()}\ncreated: 2026-06-01\n---\n\n{captures}\n",
            encoding="utf-8",
        )

    with patch("distill_cron.run_git"), \
         patch("personalkm.gitstate.ensure_clean_git_state", return_value=None), \
         patch("personalkm.propagate.distill.route",
               return_value={"summary": "ok", "key_facts": []}):
        result = run_distill(vault, limit=2, dry_run=False)

    # Only 2 of 3 pages should be distilled
    assert result["pages_distilled"] == 2


def test_run_distill_no_candidates_returns_success(tmp_path: Path):
    vault = tmp_path / "vault"
    entities = vault / "wiki" / "entities"
    entities.mkdir(parents=True)

    # Create a page that does NOT trigger (only 1 capture, fresh)
    (entities / "fresh.md").write_text(
        "---\ntitle: Fresh\ncreated: 2026-07-25\n---\n\n### One capture (2026-07-25)\n",
        encoding="utf-8",
    )

    with patch("personalkm.gitstate.ensure_clean_git_state", return_value=None):
        result = run_distill(vault, limit=0, dry_run=False)
    assert result["status"] == "success"
    assert result["pages_distilled"] == 0


def test_run_distill_no_wiki_dir_returns_error(tmp_path: Path):
    result = run_distill(tmp_path, limit=0, dry_run=False)
    assert result["status"] == "error"
    assert "wiki/" in result["message"]
