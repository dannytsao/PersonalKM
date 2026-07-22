from pathlib import Path

from personalkm.propagate.entity_dedup import (
    EntityRegistry,
    _append_source_to_frontmatter,
    canonical_slug_from_name,
    resolve_canonical_from_entities,
    set_updated_timestamp,
)


def test_set_updated_timestamp_replaces_existing_field():
    text = "title: Foo\ncreated: 2026-07-01\nupdated: 2026-07-01\ntype: entity"
    result = set_updated_timestamp(text, "2026-07-19")
    assert "updated: 2026-07-19" in result
    assert "updated: 2026-07-01" not in result


def test_set_updated_timestamp_inserts_after_created_when_missing():
    # This is the bug this fix closes: a bare re.sub on `^updated: .+$` used to
    # silently no-op when the field didn't exist, leaving the page's staleness
    # signal wrong forever.
    text = "title: Foo\ncreated: 2026-07-01\ntype: entity"
    result = set_updated_timestamp(text, "2026-07-19")
    assert "updated: 2026-07-19" in result
    lines = result.splitlines()
    assert lines[lines.index("created: 2026-07-01") + 1] == "updated: 2026-07-19"


def test_set_updated_timestamp_inserts_after_delimiter_when_no_created_field():
    text = "---\ntitle: Foo\ntype: entity\n---\n\nBody"
    result = set_updated_timestamp(text, "2026-07-19")
    assert "updated: 2026-07-19" in result
    assert result.startswith("---\nupdated: 2026-07-19\n")


def test_canonical_slug_prefers_earliest_mentioned_entity():
    # Regression: this exact real title merged into claude-code.md instead of
    # a Kimi page, because "claude-code" was enumerated before "kimi-k3" in
    # CANONICAL_ENTITIES and the old code returned the first dict match it
    # found, not the one that actually leads the title.
    title = "🚀kimi-k3编程能力倍增!在claude-code中全方位实测代码能力"
    assert canonical_slug_from_name(title) == "kimi-k3"


def test_canonical_slug_still_matches_when_only_one_entity_present():
    assert canonical_slug_from_name("Claude Code 教學") == "claude-code"
    assert canonical_slug_from_name("random topic with no entity") is None


def test_canonical_slug_prefers_entity_leading_the_title_over_later_mention():
    # A title genuinely about Anthropic that also name-drops other tools later
    # should still resolve to Anthropic, since it leads the title.
    title = "Anthropic's downfall... kimi-k3.1, grok-4.6, deepseek-v4-ga"
    assert canonical_slug_from_name(title) == "anthropic"


def test_resolve_canonical_single_unambiguous_hit():
    # P6#21: a capture whose title never names the entity but whose
    # LLM-detected entities resolve to exactly one canonical slug.
    assert resolve_canonical_from_entities(["Claude Code", "some random tool"]) == "claude-code"


def test_resolve_canonical_ambiguous_returns_none():
    # Two distinct canonical entities -> ambiguity gate refuses to route.
    assert resolve_canonical_from_entities(["Claude Code", "Kimi K3"]) is None


def test_resolve_canonical_no_hit_returns_none():
    assert resolve_canonical_from_entities(["random", "unknown things"]) is None
    assert resolve_canonical_from_entities([]) is None
    assert resolve_canonical_from_entities(None) is None


def test_resolve_canonical_duplicate_mentions_of_same_entity_still_route():
    # The same canonical entity named twice (different spellings) is still
    # ONE distinct target — not ambiguity.
    assert resolve_canonical_from_entities(["Claude Code", "claude-code guide"]) == "claude-code"


def test_append_source_to_frontmatter_appends_after_existing_entries():
    # Regression: the old regex matched only the "sources:" line itself
    # (`.*$` doesn't cross into the following indented list lines), so
    # re.sub replaced just that line with "sources:\n  - new", inserting
    # the new source BEFORE existing ones instead of after.
    fm = (
        "title: Anthropic\n"
        "sources:\n"
        '  - "[[Archive/raw/Tech/first]]"\n'
        '  - "[[Archive/raw/Tech/second]]"\n'
        "confidence: medium\n"
    )
    result = _append_source_to_frontmatter(fm, "[[Archive/raw/Tech/third]]")
    lines = result.splitlines()
    first_idx = lines.index('  - "[[Archive/raw/Tech/first]]"')
    second_idx = lines.index('  - "[[Archive/raw/Tech/second]]"')
    third_idx = lines.index('  - "[[Archive/raw/Tech/third]]"')
    assert first_idx < second_idx < third_idx
    assert "confidence: medium" in result


def test_append_source_to_frontmatter_handles_empty_inline_list():
    fm = "title: Foo\nsources: []\nconfidence: medium\n"
    result = _append_source_to_frontmatter(fm, "[[new-source]]")
    assert "sources: []" not in result
    assert '  - "[[new-source]]"' in result


def test_append_source_to_frontmatter_creates_field_when_missing():
    fm = "title: Foo\nconfidence: medium\n"
    result = _append_source_to_frontmatter(fm, "[[new-source]]")
    assert 'sources:\n  - "[[new-source]]"' in result


def test_append_source_to_frontmatter_skips_duplicate():
    fm = 'title: Foo\nsources:\n  - "[[existing]]"\n'
    result = _append_source_to_frontmatter(fm, "[[existing]]")
    assert result.count("existing") == 1


def test_append_capture_preserves_single_frontmatter_block(tmp_path: Path):
    # Regression: this exact sequence (merging a capture with a source into
    # a page whose sources: list already had entries) previously corrupted
    # the frontmatter delimiter structure, orphaning title/canonical/etc. as
    # plain body text invisible to any frontmatter reader.
    page = tmp_path / "anthropic.md"
    page.write_text(
        "---\n"
        "title: Anthropic\n"
        "canonical: true\n"
        "created: 2026-07-17\n"
        "updated: 2026-07-20\n"
        "sources:\n"
        '  - "[[Archive/raw/Tech/first]]"\n'
        '  - "[[Archive/raw/Tech/second]]"\n'
        "confidence: medium\n"
        "---\n\n"
        "## Summary\n\nExisting summary.\n",
        encoding="utf-8",
    )

    registry = EntityRegistry.__new__(EntityRegistry)
    registry._append_capture(
        page,
        title="qwen",
        content="Qwen mentions Anthropic in passing.",
        source="[[Archive/raw/Tech/third]]",
        date_str="2026-07-20",
    )

    result = page.read_text(encoding="utf-8")
    assert result.count("---") == 2
    assert result.startswith("---\n")
    assert "title: Anthropic" in result
    assert "canonical: true" in result
    lines = result.splitlines()
    first_idx = lines.index('  - "[[Archive/raw/Tech/first]]"')
    second_idx = lines.index('  - "[[Archive/raw/Tech/second]]"')
    third_idx = lines.index('  - "[[Archive/raw/Tech/third]]"')
    assert first_idx < second_idx < third_idx
