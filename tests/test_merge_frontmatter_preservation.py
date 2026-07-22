"""
Regression tests for the two frontmatter round-trip corruption mechanisms
(P7#27 root cause): wholesale frontmatter deletion when leading junk exists
(claude-code.md, 2026-07-12), and padding growth on every rewrite
(github.md's ~63 accumulated blank lines).
"""

from pathlib import Path

from personalkm.propagate.entity_dedup import EntityRegistry
from scripts.post_link_ollama import set_frontmatter_value


def _page_with_leading_blank_line() -> str:
    return (
        "\n"  # the junk that used to flip startswith("---") and delete everything
        "---\n"
        "title: Claude Code Guide\n"
        "canonical: true\n"
        "created: 2026-06-28\n"
        "updated: 2026-07-01\n"
        "sources:\n"
        '  - "[[Archive/raw/Tech/original-source]]"\n'
        "---\n\n"
        "## Summary\n\nExisting summary.\n"
    )


def test_append_capture_preserves_frontmatter_despite_leading_junk(tmp_path: Path):
    page = tmp_path / "claude-code.md"
    page.write_text(_page_with_leading_blank_line(), encoding="utf-8")

    registry = EntityRegistry.__new__(EntityRegistry)
    registry._append_capture(
        page,
        title="new capture",
        content="Capture body.",
        source="[[Archive/raw/Tech/new-source]]",
        date_str="2026-07-22",
    )

    result = page.read_text(encoding="utf-8")
    assert "title: Claude Code Guide" in result
    assert "canonical: true" in result
    assert result.startswith("---\n")
    assert result.count("---") == 2
    assert "### new capture (2026-07-22)" in result


def test_append_capture_roundtrip_does_not_grow_padding(tmp_path: Path):
    page = tmp_path / "github.md"
    page.write_text(
        "---\ntitle: GitHub\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\n## Summary\n\nS.\n",
        encoding="utf-8",
    )
    registry = EntityRegistry.__new__(EntityRegistry)
    for i in range(5):
        registry._append_capture(
            page, title=f"capture {i}", content="C.", source="", date_str="2026-07-22"
        )
    result = page.read_text(encoding="utf-8")
    # The old rewrap added a blank line top+bottom of the frontmatter per
    # write; after 5 writes the title had drifted 5 lines down.
    assert result.split("\n")[1] == "title: GitHub"
    assert "\n\n\n" not in result.split("## Summary")[0]


def test_set_frontmatter_value_does_not_grow_padding():
    content = "---\ntitle: X\n---\n\nBody.\n"
    for i in range(5):
        content = set_frontmatter_value(content, "wikilink_processed", f"2026-07-22T0{i}:00:00")
    assert content.split("\n")[1] == "title: X"
    assert "\n\n\n" not in content.split("Body.")[0]
