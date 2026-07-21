from personalkm.ingest.llm_summarizer import detect_entity_mentions, distill_to_markdown


def test_detect_entity_mentions_no_longer_produces_topic_junk():
    # Regression: the old free-form Chinese matcher (`[CJK]{2,12}` with an
    # 8-word stoplist) turned ordinary sentence fragments into fake
    # `topic-*` entities — confirmed against the real vault, where these
    # accounted for broken wikilinks like `topic-下載`, `topic-五步驟剪片流程`.
    body = "電腦 C 盤被擠爆，刪掉這 7 個隱藏垃圾瞬間騰出 200GB 空間，零度解說"
    entities = detect_entity_mentions(body)
    assert not any(e.startswith("topic-") for e in entities)


def test_detect_entity_mentions_still_finds_english_entities():
    body = "We used Docker and Kubernetes alongside Claude-3.5 for this pipeline."
    entities = detect_entity_mentions(body)
    assert "docker" in entities
    assert "kubernetes" in entities
    assert "claude-3-5" in entities


def test_distill_to_markdown_wikilinks_entities_by_slug_not_raw_name():
    # Regression: distill_to_markdown computed `_slugify(entity)` but never
    # used it, wikilinking the raw LLM string instead (e.g. "[[KIMI K3]]"),
    # which can never resolve since pages are saved as `kimi-k3.md`.
    result = {
        "summary": "A test summary.",
        "entities_mentioned": ["KIMI K3", "GLM-5.2"],
    }
    markdown = distill_to_markdown(result, page_type="entity")

    assert "[[KIMI K3]]" not in markdown
    assert "[[GLM-5.2]]" not in markdown
    assert "[[kimi-k3|KIMI K3]]" in markdown
    assert "[[glm-52|GLM-5.2]]" in markdown


def test_distill_to_markdown_omits_display_alias_when_slug_matches():
    result = {
        "summary": "A test summary.",
        "entities_mentioned": ["docker"],
    }
    markdown = distill_to_markdown(result, page_type="entity")

    assert "[[docker]]" in markdown
    assert "|" not in markdown.split("[[docker]]")[0].split("\n")[-1]


def test_distill_to_markdown_wikilinks_concepts_tools_prerequisites_by_slug():
    result = {
        "summary": "A test summary.",
        "related_concepts": ["Local-First Automation"],
        "prerequisites": ["Node.js"],
        "related_tools": ["VS Code"],
    }
    markdown = distill_to_markdown(result, page_type="concept")

    assert "[[Local-First Automation]]" not in markdown
    assert "[[Node.js]]" not in markdown
    assert "[[VS Code]]" not in markdown
    assert "[[local-first-automation|Local-First Automation]]" in markdown
    assert "[[nodejs|Node.js]]" in markdown
    assert "[[vs-code|VS Code]]" in markdown
