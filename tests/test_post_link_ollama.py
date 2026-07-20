import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from post_link_ollama import set_frontmatter_value  # noqa: E402


def test_set_frontmatter_value_replaces_whole_old_value_not_just_first_char():
    # Regression: the old regex (`\S` instead of `.*$`) only matched the
    # first character of the existing value, so re-running this hourly cron
    # step kept concatenating a new timestamp onto the undeleted remainder
    # of the old one — e.g. "2026-07-19T01:18:02026-07-18T23:42:56...".
    content = "---\ntitle: Foo\nwikilink_processed: 2026-07-18T15:51:54\n---\n\nBody\n"
    updated = set_frontmatter_value(content, "wikilink_processed", "2026-07-19T01:18:00")
    assert "wikilink_processed: 2026-07-19T01:18:00" in updated
    assert "2026-07-18T15:51:54" not in updated
    assert updated.count("wikilink_processed:") == 1


def test_set_frontmatter_value_survives_multiple_runs():
    content = "---\ntitle: Foo\n---\n\nBody\n"
    for ts in ["2026-07-18T15:51:54", "2026-07-18T17:24:33", "2026-07-19T01:18:00"]:
        content = set_frontmatter_value(content, "wikilink_processed", ts)
    assert content.count("wikilink_processed:") == 1
    assert "wikilink_processed: 2026-07-19T01:18:00" in content


def test_set_frontmatter_value_appends_when_key_missing():
    content = "---\ntitle: Foo\n---\n\nBody\n"
    updated = set_frontmatter_value(content, "wikilink_processed", "2026-07-18T15:51:54")
    assert "wikilink_processed: 2026-07-18T15:51:54" in updated
