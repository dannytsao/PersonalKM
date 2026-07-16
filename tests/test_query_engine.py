from pathlib import Path

from personalkm.query.query_engine import query_wiki, search_raw_and_resolved, search_vault


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
