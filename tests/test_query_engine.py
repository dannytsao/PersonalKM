from pathlib import Path

from personalkm.query.query_engine import query_wiki, search_raw_and_resolved, search_vault, write_back_answer


def test_query_searches_wiki_raw_and_resolved(tmp_path: Path):
    wiki = tmp_path / "wiki" / "entities"
    raw = tmp_path / "raw" / "Tech"
    resolved = tmp_path / "resolved" / "Tech"
    wiki.mkdir(parents=True)
    raw.mkdir(parents=True)
    resolved.mkdir(parents=True)

    (wiki / "hermes-agent.md").write_text(
        """---
title: Hermes Agent
type: entity
topic: Tech-Trends-&-Insights
tags: [agent]
sources:
  - [[Archive/raw/Tech/hermes]]
confidence: high
---

## Summary

Hermes Agent is a local-first assistant workflow.
""",
        encoding="utf-8",
    )
    (raw / "2026-07-16-hermes.md").write_text(
        """# Hermes clip

## Log ID
202607161200_00001

## 摘要
Hermes Agent raw capture mentions local-first automation.

## 原文連結
https://example.com/hermes
""",
        encoding="utf-8",
    )
    (resolved / "2026-07-16-hermes.md").write_text(
        "# Resolved Hermes\n\nResolved article body about Hermes Agent and automation.",
        encoding="utf-8",
    )

    results = search_vault("Hermes Agent automation", tmp_path, top_k=10)
    kinds = {result["source_kind"] for result in results}

    assert {"wiki", "raw", "resolved"} <= kinds
    raw_result = next(result for result in results if result["source_kind"] == "raw")
    assert raw_result["log_id"] == "202607161200_00001"
    assert raw_result["url"] == "https://example.com/hermes"


def test_query_wiki_works_with_raw_only_vault(tmp_path: Path):
    raw = tmp_path / "raw" / "Tech"
    raw.mkdir(parents=True)
    (raw / "note.md").write_text(
        "# Local-first note\n\nThis raw note mentions query search and source metadata.",
        encoding="utf-8",
    )

    result = query_wiki("query source metadata", tmp_path, top_k=5, use_llm=False)

    assert result["error"] is None
    assert result["total_matches"] == 1
    assert result["matched_pages"][0]["source_kind"] == "raw"


def test_search_raw_and_resolved_returns_source_links(tmp_path: Path):
    raw = tmp_path / "raw" / "Tech"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text(
        """# Source Note

## 原始內容
This note is about personal knowledge search.

## 原文連結
https://example.com/source
""",
        encoding="utf-8",
    )

    results = search_raw_and_resolved("knowledge search", tmp_path)

    assert len(results) == 1
    assert results[0]["page"] == "raw/Tech/source.md"
    assert results[0]["url"] == "https://example.com/source"


def test_search_vault_ranks_wiki_above_raw_on_comparable_relevance(tmp_path: Path):
    # A long raw note repeating the query keywords used to be able to outscore
    # a terse, curated wiki page purely on keyword-count volume. Wiki pages are
    # the distilled surface and should win ties like this.
    wiki = tmp_path / "wiki" / "entities"
    raw = tmp_path / "raw" / "Tech"
    wiki.mkdir(parents=True)
    raw.mkdir(parents=True)

    (wiki / "hermes-agent.md").write_text(
        """---
title: Hermes Agent
type: entity
confidence: high
---

## Summary

Hermes Agent is a local-first assistant workflow.
""",
        encoding="utf-8",
    )
    # Raw note repeats "hermes agent" many times to inflate body_mentions score.
    repeated = " ".join(["hermes agent"] * 12)
    (raw / "note.md").write_text(f"# Hermes agent notes\n\n{repeated}", encoding="utf-8")

    results = search_vault("hermes agent", tmp_path, top_k=10)

    assert results[0]["source_kind"] == "wiki"


def test_write_back_answer_appends_to_existing_cited_page(tmp_path: Path):
    wiki_entities = tmp_path / "wiki" / "entities"
    wiki_entities.mkdir(parents=True)
    page = wiki_entities / "hermes-agent.md"
    page.write_text(
        "---\ntitle: Hermes Agent\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\nBody.\n",
        encoding="utf-8",
    )

    written = write_back_answer(
        tmp_path, "what is hermes agent?", "Hermes Agent is a local-first workflow.", ["hermes-agent"]
    )

    assert written == "wiki/entities/hermes-agent.md"
    content = page.read_text(encoding="utf-8")
    assert "## 問答記錄" in content
    assert "what is hermes agent?" in content
    assert "updated: 2026-07-01" not in content  # timestamp must have bumped


def test_write_back_answer_returns_none_when_no_cited_page_exists(tmp_path: Path):
    (tmp_path / "wiki" / "entities").mkdir(parents=True)

    written = write_back_answer(tmp_path, "unknown?", "some answer", ["nonexistent-page"])

    assert written is None


def test_query_wiki_never_writes_back_without_llm(tmp_path: Path):
    # confirm_write_back=True must still be a no-op when use_llm=False — there
    # is no LLM answer to cite anything, so nothing should be written.
    raw = tmp_path / "raw" / "Tech"
    raw.mkdir(parents=True)
    (raw / "note.md").write_text("# Note\n\nSome content about testing.", encoding="utf-8")

    result = query_wiki("testing", tmp_path, use_llm=False, confirm_write_back=True)

    assert result["written_back"] is None
