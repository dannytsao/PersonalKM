from scripts.fix_duplicate_frontmatter import is_corrupted, repair


def test_is_corrupted_detects_orphaned_frontmatter():
    content = (
        "---\n\nwikilink_processed: 2026-07-21T06:48:52\n\n---\n\n"
        "title: Anthropic\ncanonical: true\nwikilink_processed: 2026-07-20T02:06:10\n---\n\n"
        "## Summary\n\nBody.\n"
    )
    assert is_corrupted(content) is True


def test_is_corrupted_false_for_clean_page():
    content = "---\ntitle: Anthropic\ncanonical: true\n---\n\n## Summary\n\nBody.\n"
    assert is_corrupted(content) is False


def test_repair_collapses_single_orphan_wrapper():
    # Simplified version of the real anthropic.md corruption (3 delimiters).
    content = (
        "---\n\n\nwikilink_processed: 2026-07-21T06:48:52\n\n\n---\n\n\n"
        "title: Anthropic\ncanonical: true\ncreated: 2026-07-17\nupdated: 2026-07-20\n"
        'sources:\n  - "[[a]]"\n  - "[[b]]"\nconfidence: medium\n'
        "wikilink_processed: 2026-07-20T02:06:10\n---\n\n## Summary\n\nBody text.\n"
    )
    result = repair(content)

    assert result.count("---") == 2
    assert result.startswith("---\n")
    assert "title: Anthropic" in result
    assert "canonical: true" in result
    assert '  - "[[a]]"' in result and '  - "[[b]]"' in result
    # Freshest timestamp (from the orphan wrapper) wins.
    assert "wikilink_processed: 2026-07-21T06:48:52" in result
    assert "wikilink_processed: 2026-07-20T02:06:10" not in result
    assert "## Summary" in result
    assert "Body text." in result


def test_repair_collapses_multiple_stacked_orphan_wrappers():
    # Matches the real 2026-07-15-openai-...-gpt-56-...md shape: 4 orphan
    # wrappers stacked in front of the real frontmatter.
    orphans = "".join(
        f"---\n\nwikilink_processed: {ts}\n\n---\n\n"
        for ts in [
            "2026-07-20T02:05:09",
            "2026-07-20T13:06:38",
            "2026-07-20T14:12:45",
            "2026-07-21T06:50:04",
        ]
    )
    real_fm = (
        "title: OpenAI GPT-5.6\ncanonical: true\n"
        "wikilink_processed: 2026-07-20T02:05:09\n"
    )
    content = orphans + "---\n" + real_fm + "---\n\n## Summary\n\nBody.\n"

    result = repair(content)

    assert result.count("---") == 2
    assert "title: OpenAI GPT-5.6" in result
    assert "wikilink_processed: 2026-07-21T06:50:04" in result  # latest across all orphans
    assert "## Summary" in result


def test_repair_is_noop_on_clean_page():
    content = "---\ntitle: Anthropic\ncanonical: true\n---\n\n## Summary\n\nBody.\n"
    assert repair(content) == content
