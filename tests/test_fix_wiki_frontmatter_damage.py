import subprocess
from pathlib import Path

import pytest

from scripts.fix_wiki_frontmatter_damage import (
    normalize_padding,
    peel_wrapper_blocks,
    repair_missing_frontmatter,
    strip_pasted_frontmatter,
)

GOOD = (
    "---\n"
    "title: Claude Code Guide\n"
    "canonical: true\n"
    "created: 2026-06-28\n"
    "wikilink_processed: 2026-06-28T12:00:00\n"
    "---\n\n"
    "## Summary\n\nOriginal summary.\n"
)

# The damaged shape observed on the real claude-code.md: two orphan wrapper
# blocks (wikilink_processed only) stacked before a frontmatter-less body.
DAMAGED = (
    "---\n\n\nwikilink_processed: 2026-07-21T14:33:03\n\n\n---\n\n"
    "---\n\nwikilink_processed: 2026-07-20T09:21:36\n\n---\n\n"
    "## Summary\n\nOriginal summary.\n\n### later capture (2026-07-15)\n\nMore.\n"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
             "HOME": str(repo), "PATH": "/usr/bin:/bin"},
    ).stdout.strip()


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "wiki" / "entities").mkdir(parents=True)
    _git(v, "init", "-b", "main")
    page = v / "wiki" / "entities" / "claude-code.md"
    page.write_text(GOOD, encoding="utf-8")
    _git(v, "add", "-A")
    _git(v, "commit", "-m", "good version")
    page.write_text(DAMAGED, encoding="utf-8")
    _git(v, "add", "-A")
    _git(v, "commit", "-m", "corruption happened")
    return v


def test_peel_wrapper_blocks_extracts_orphans_and_body():
    wrappers, body = peel_wrapper_blocks(DAMAGED)
    assert len(wrappers) == 2
    assert "2026-07-21T14:33:03" in wrappers[0]
    assert body.lstrip().startswith("## Summary")


def test_repair_recovers_title_and_newest_timestamp(vault: Path):
    page = vault / "wiki" / "entities" / "claude-code.md"
    repaired = repair_missing_frontmatter(vault, page)

    assert repaired is not None
    assert repaired.startswith("---\n")
    assert "title: Claude Code Guide" in repaired
    assert "canonical: true" in repaired
    # Newest timestamp across the wrappers wins over the recovered one.
    assert "wikilink_processed: 2026-07-21T14:33:03" in repaired
    assert "wikilink_processed: 2026-06-28T12:00:00" not in repaired
    # Current body survives, wrappers are gone.
    assert "### later capture (2026-07-15)" in repaired
    assert repaired.count("wikilink_processed") == 1


def test_repair_returns_none_when_no_titled_version_exists(vault: Path):
    page = vault / "wiki" / "entities" / "never-titled.md"
    page.write_text("---\nwikilink_processed: 2026-07-01T00:00:00\n---\n\nBody.\n", encoding="utf-8")
    _git(vault, "add", "-A")
    _git(vault, "commit", "-m", "born corrupted")
    assert repair_missing_frontmatter(vault, page) is None


def test_strip_pasted_frontmatter_removes_kimi_shape():
    # The kimi-k3.md shape: another page's full frontmatter pasted bare
    # into the body, including a truncated sources wikilink.
    content = (
        "---\ntitle: Kimi K3\ncanonical: true\n---\n\n"
        "# Kimi K3\n\n"
        "title: OpenAI 官方釋出 GPT-5.6 提示詞指南\n"
        "created: 2026-07-15\n"
        "updated: 2026-07-15\n"
        "topic: Tech-Trends-&-Insights\n"
        "tags: [llm, openai]\n"
        "type: entity\n"
        "sources:\n"
        "  - [[Archive/raw/Tech/2026-07-15-truncated\n\n"
        "## Mentions\n\n- Mentioned in [[somewhere]]\n"
    )
    new_content, removed = strip_pasted_frontmatter(content)
    assert removed == 1
    assert "OpenAI 官方釋出" not in new_content
    assert "title: Kimi K3" in new_content  # real frontmatter untouched
    assert "## Mentions" in new_content


def test_strip_pasted_frontmatter_ignores_short_key_runs():
    content = (
        "---\ntitle: X\n---\n\n"
        "Some text.\n\ntype: entity\ncreated: 2026-07-01\n\nMore text.\n"
    )
    new_content, removed = strip_pasted_frontmatter(content)
    assert removed == 0
    assert new_content == content


def test_normalize_padding_strips_frontmatter_bloat():
    bloated = "---\n" + "\n" * 30 + "title: GitHub\n" + "\n" * 30 + "---\n\n## Summary\n\nS.\n"
    result = normalize_padding(bloated)
    assert result.split("\n")[1] == "title: GitHub"
    assert "## Summary" in result
