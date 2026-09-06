import json
from pathlib import Path
from types import SimpleNamespace

from personalkm.query import line_bot


def _write_registry(root: Path, entries: list[dict]) -> None:
    registry = root / "wiki" / "_registry"
    registry.mkdir(parents=True)
    (registry / "city-subject-store.json").write_text(
        json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8"
    )


def test_registry_query_filters_location_and_subject_without_llm(tmp_path: Path, monkeypatch) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "早午餐",
                "store": "COFFEE FIRST",
                "source": "wiki/entities/coffee.md",
                "address": "臺北市北投區中央北路二段68之5號",
                "highlights": ["澳式早午餐店", "高蛋白巧克力軟餅乾"],
                "rating": 4.9,
                "rating_count": 72,
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "早午餐",
                "store": "士林早午餐",
                "source": "wiki/entities/shilin.md",
                "address": "臺北市士林區劍潭路78號",
                "highlights": [],
                "rating": 4.4,
                "rating_count": 10,
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "住宿",
                "store": "北投旅館",
                "source": "wiki/entities/hotel.md",
                "address": "臺北市北投區中山路1號",
                "highlights": [],
                "rating": 4.8,
                "rating_count": 20,
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("北投有什麼早午餐？", tmp_path)

    assert result["error"] is None
    assert result["sources"] == ["城市 × 主題 × 店家彙整"]
    assert "COFFEE FIRST" in result["answer"]
    assert "士林早午餐" not in result["answer"]
    assert "北投旅館" not in result["answer"]
    assert "<think>" not in result["answer"]


def test_llm_output_gate_removes_reasoning_and_rejects_work_trace() -> None:
    assert line_bot._safe_llm_answer("<think>檢查資料</think>\n答案：有資料") == "答案：有資料"
    assert line_bot._safe_llm_answer("我先檢視資料，再回答。") is None


def test_llm_query_replaces_reasoning_leak_with_safe_fallback(tmp_path: Path, monkeypatch) -> None:
    concepts = tmp_path / "wiki" / "concepts"
    concepts.mkdir(parents=True)
    (concepts / "city-subject-store.md").write_text(
        "---\ntitle: 城市資料\n---\n\n北投的生活資料。", encoding="utf-8"
    )
    monkeypatch.setattr(
        line_bot,
        "route",
        lambda *_args, **_kwargs: SimpleNamespace(text="<think>內部搜尋</think>\n我先檢視資料。"),
    )

    result = line_bot._query_all("Danny 的生活資料", tmp_path)

    assert result["error"] == "unsafe_llm_output"
    assert "<think>" not in result["answer"]
    assert "我先檢視" not in result["answer"]
