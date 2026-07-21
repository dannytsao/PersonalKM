from scripts.fix_stub_sources_pollution import is_polluted, repair


def _page(sources_block: str, has_mentions: bool = True) -> str:
    mentions = "\n## Mentions\n\n- Mentioned in [[github]]: ...\n" if has_mentions else ""
    return (
        "---\n"
        "title: Antigravity\n"
        "canonical: true\n"
        f"{sources_block}"
        "confidence: medium\n"
        "---\n\n"
        "# Antigravity\n\nBody text.\n"
        f"{mentions}"
    )


def test_is_polluted_true_when_all_sources_are_wiki_paths_and_mentions_exists():
    content = _page('sources:\n  - "wiki/entities/github.md"\n  - "wiki/entities/openrouter.md"\n')
    assert is_polluted(content) is True


def test_is_polluted_false_when_a_real_raw_citation_present():
    content = _page('sources:\n  - "[[Archive/raw/Tech/2026-07-15-some-capture]]"\n')
    assert is_polluted(content) is False


def test_is_polluted_false_when_mixed_wiki_and_real_source():
    content = _page(
        'sources:\n  - "wiki/entities/github.md"\n  - "[[Archive/raw/Tech/real-capture]]"\n'
    )
    assert is_polluted(content) is False


def test_is_polluted_false_without_mentions_section():
    content = _page('sources:\n  - "wiki/entities/github.md"\n', has_mentions=False)
    assert is_polluted(content) is False


def test_is_polluted_false_for_empty_sources():
    content = _page("sources: []\n")
    assert is_polluted(content) is False


def test_repair_resets_sources_to_empty_list():
    content = _page('sources:\n  - "wiki/entities/github.md"\n  - "wiki/entities/openrouter.md"\n')
    result = repair(content)
    assert "sources: []" in result
    assert "wiki/entities/github.md" not in result
    assert "## Mentions" in result  # untouched
    assert "Body text." in result  # untouched
