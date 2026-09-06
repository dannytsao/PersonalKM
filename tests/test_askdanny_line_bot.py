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
                "gps": [25.1375317, 121.4943154],
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
    assert "- 主題：早午餐" in result["answer"]
    assert "- 店名：COFFEE FIRST" in result["answer"]
    assert "- Google 星等：⭐ 4.9（72 則）" in result["answer"]
    assert "- 特色說明：澳式早午餐店；高蛋白巧克力軟餅乾" in result["answer"]
    assert "- GPS：https://www.google.com/maps/search/?api=1&query=25.1375317,121.4943154" in result["answer"]
    assert "地址：" not in result["answer"]
    assert "<think>" not in result["answer"]


def test_registry_query_excludes_removed_entries_and_supports_lodging(tmp_path: Path, monkeypatch) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "住宿",
                "store": "北投溫泉旅館",
                "address": "臺北市北投區中山路1號",
                "highlights": ["溫泉"],
                "rating": 4.8,
                "rating_count": 20,
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "住宿",
                "store": "已移除旅館",
                "address": "臺北市北投區中山路2號",
                "status": "removed",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("北投有什麼住宿？", tmp_path)

    assert result["error"] is None
    assert "北投溫泉旅館" in result["answer"]
    assert "已移除旅館" not in result["answer"]
    assert "GPS：" not in result["answer"]


def test_registry_query_returns_no_match_for_known_location_without_subject(tmp_path: Path, monkeypatch) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "住宿",
                "store": "北投溫泉旅館",
                "address": "臺北市北投區中山路1號",
                "status": "resolved",
            }
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("北投有什麼早午餐？", tmp_path)

    assert result == {"answer": None, "sources": [], "error": "no_match"}


def test_registry_query_expands_food_alias_across_subjects_without_llm(tmp_path: Path, monkeypatch) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "新北市",
                "subject": "餐廳",
                "store": "新北餐廳",
                "address": "新北市板橋區文化路1號",
                "rating": 4.7,
                "status": "resolved",
            },
            {
                "city": "新北市",
                "subject": "咖啡廳",
                "store": "新北咖啡廳",
                "address": "新北市淡水區中正路2號",
                "rating": 4.9,
                "status": "resolved",
            },
            {
                "city": "新北市",
                "subject": "甜點",
                "store": "新北甜點店",
                "address": "新北市三重區重新路3號",
                "rating": 4.6,
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "台北餐廳",
                "address": "台北市大安區信義路4號",
                "rating": 5.0,
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("新北市有什麼美食？", tmp_path)

    assert result["error"] is None
    assert result["sources"] == ["城市 × 主題 × 店家彙整"]
    assert "目前整理到 3 筆符合條件的資料：" in result["answer"]
    assert "新北餐廳" in result["answer"]
    assert "新北咖啡廳" in result["answer"]
    assert "新北甜點店" in result["answer"]
    assert "台北餐廳" not in result["answer"]


def test_llm_query_only_includes_relevant_allowed_page(tmp_path: Path, monkeypatch) -> None:
    concepts = tmp_path / "wiki" / "concepts"
    concepts.mkdir(parents=True)
    (concepts / "city-subject-store.md").write_text(
        "---\ntitle: 城市店家\n---\n\n北投住宿資料。", encoding="utf-8"
    )
    (concepts / "tianmu-food.md").write_text(
        "---\ntitle: 天母美食\n---\n\n天母 brunch 推薦資料。", encoding="utf-8"
    )
    captured: dict[str, str] = {}

    def fake_route(_stage: str, prompt: str):
        captured["prompt"] = prompt
        return SimpleNamespace(text="天母目前有整理過的 brunch 資料。")

    monkeypatch.setattr(line_bot, "route", fake_route)

    result = line_bot._query_all("天母有什麼推薦？", tmp_path)

    assert result["error"] is None
    assert result["sources"] == ["天母美食"]
    assert "天母 brunch 推薦資料" in captured["prompt"]
    assert "北投住宿資料" not in captured["prompt"]


def test_llm_output_gate_removes_reasoning_and_rejects_work_trace() -> None:
    assert line_bot._safe_llm_answer("<think>檢查資料</think>\n答案：有資料") == "答案：有資料"
    assert line_bot._safe_llm_answer("<analysis>檢查資料</analysis>\n答案：有資料") == "答案：有資料"
    assert line_bot._safe_llm_answer("我先檢視資料，再回答。") is None


def test_webhook_event_parser_accepts_text_and_ignores_other_events() -> None:
    events = line_bot.askdanny_events_from_webhook(
        {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-1",
                    "source": {"userId": "user-1"},
                    "message": {"type": "text", "text": "北投早午餐"},
                },
                {
                    "type": "message",
                    "replyToken": "reply-2",
                    "source": {"userId": "user-2"},
                    "message": {"type": "image", "id": "image-1"},
                },
                {"type": "follow", "replyToken": "reply-3"},
            ]
        }
    )

    assert events == [line_bot.AskDannyEvent("reply-1", "user-1", "北投早午餐")]


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
