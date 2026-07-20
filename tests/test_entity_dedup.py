from personalkm.propagate.entity_dedup import canonical_slug_from_name, set_updated_timestamp


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
