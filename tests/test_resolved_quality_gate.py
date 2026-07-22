"""Resolved content must supersede the raw capture's fetch-failure text.

Regression test for the P7 bug where notes whose capture-time fetch failed
(raw body contains "網站回傳 HTTP 403" → matches low-quality pattern
'http 40') were trashed by ingest even though the resolver had since
fetched the real article into resolved/.
"""

from pathlib import Path

import pytest

import personalkm.ingest.ingestion_v2 as iv2
from personalkm.ingest.ingestion_v2 import (
    _get_substantial_resolved_content,
    ingest_file_v2,
    is_low_quality,
)

RAW_FETCH_FAILURE = """# albertblog.tw

## 摘要
無法擷取網頁內容，網站回傳 HTTP 403，表示網站拒絕自動化擷取。

## 原文連結
https://example.com/article
"""

RESOLVED_ARTICLE = (
    "位於桃園大溪的麵食館，從小店面重新裝潢成獨棟大店面，"
    "假日晚餐時段人潮爆滿，Google 評論突破 4,400 則維持 4.1 顆星。"
)


def _make_vault(tmp_path: Path, with_resolved: bool) -> Path:
    raw_file = tmp_path / "raw" / "General" / "2026-07-16-note.md"
    raw_file.parent.mkdir(parents=True)
    raw_file.write_text(RAW_FETCH_FAILURE, encoding="utf-8")
    if with_resolved:
        resolved_file = tmp_path / "resolved" / "General" / "2026-07-16-note.md"
        resolved_file.parent.mkdir(parents=True)
        resolved_file.write_text(RESOLVED_ARTICLE, encoding="utf-8")
    return raw_file


def test_raw_fetch_failure_text_matches_pattern():
    low, reason = is_low_quality(RAW_FETCH_FAILURE)
    assert low
    assert "http 40" in reason


def test_get_substantial_resolved_content_found(tmp_path):
    raw_file = _make_vault(tmp_path, with_resolved=True)
    assert _get_substantial_resolved_content(raw_file) == RESOLVED_ARTICLE


def test_get_substantial_resolved_content_absent(tmp_path):
    raw_file = _make_vault(tmp_path, with_resolved=False)
    assert _get_substantial_resolved_content(raw_file) is None


def test_ingest_trashes_fetch_failure_without_resolved(tmp_path):
    raw_file = _make_vault(tmp_path, with_resolved=False)
    success, result = ingest_file_v2(raw_file, tmp_path / "wiki")
    assert not success
    assert "Low-quality content" in result["error"]


def test_ingest_proceeds_when_resolved_content_exists(tmp_path, monkeypatch):
    raw_file = _make_vault(tmp_path, with_resolved=True)

    seen = {}

    def fake_synthesize(body, **kwargs):
        seen["body"] = body
        raise RuntimeError("synthesis-reached")

    monkeypatch.setattr(iv2, "_synthesize_wiki_note", fake_synthesize)

    with pytest.raises(RuntimeError, match="synthesis-reached"):
        ingest_file_v2(raw_file, tmp_path / "wiki")

    # The LLM must see the resolved article, not the raw error text
    assert seen["body"] == RESOLVED_ARTICLE
