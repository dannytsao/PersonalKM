from pathlib import Path

from scripts.fix_legacy_entity_wikilinks import collect_existing_slugs, fix_body


def test_removes_standalone_topic_bullet_line():
    content = (
        "## Related Entities\n\n"
        "- [[kimi-k3]]\n"
        "- [[topic-下載]]\n"
    )
    new_content, stats = fix_body(content, existing_slugs={"kimi-k3"})
    assert "[[topic-下載]]" not in new_content
    assert "- [[kimi-k3]]" in new_content
    assert stats["topic_removed"] == 1


def test_unwraps_inline_topic_link_to_plain_text():
    content = "This mentions 電腦 in passing, see [[topic-電腦]] for context.\n"
    new_content, stats = fix_body(content, existing_slugs=set())
    assert "[[topic-電腦]]" not in new_content
    assert "topic-電腦" not in new_content
    assert "電腦" in new_content
    assert stats["topic_removed"] == 1


def test_relinks_mismatched_case_to_existing_slug():
    # _slugify("GLM-5.2") == "glm-52" (the "." is stripped, not hyphenated).
    content = "## Related Entities\n\n- [[KIMI K3]]\n- [[GLM-5.2]]\n"
    new_content, stats = fix_body(content, existing_slugs={"kimi-k3", "glm-52"})
    assert "[[kimi-k3|KIMI K3]]" in new_content
    assert "[[glm-52|GLM-5.2]]" in new_content
    assert stats["relinked"] == 2


def test_leaves_link_unchanged_when_no_matching_page_exists_even_after_slugify():
    content = "- [[claude]]\n"
    new_content, stats = fix_body(content, existing_slugs=set())
    assert new_content == content
    assert stats["relinked"] == 0
    assert stats["topic_removed"] == 0


def test_leaves_already_correct_link_unchanged():
    content = "- [[docker]]\n"
    new_content, stats = fix_body(content, existing_slugs={"docker"})
    assert new_content == content


def test_collect_existing_slugs_reads_entities_and_concepts(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "entities").mkdir(parents=True)
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "entities" / "kimi-k3.md").write_text("x", encoding="utf-8")
    (wiki / "concepts" / "local-first-automation.md").write_text("x", encoding="utf-8")

    slugs = collect_existing_slugs(wiki)
    assert slugs == {"kimi-k3", "local-first-automation"}
