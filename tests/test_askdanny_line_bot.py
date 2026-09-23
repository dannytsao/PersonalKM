import json
import anyio
import httpx
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from personalkm.llm.base import LLMError
from personalkm.query import line_bot
from personalkm.query.google_sheets import GoogleOAuthConfig, google_authorization_url


def test_query_subject_recognizes_scenic_spot_synonyms() -> None:
    # 2026-09-23 regression: "宜蘭美景" resolved to no subject at all (only
    # "景點" itself was a registered alias), so the query skipped the
    # structured subject+location filter path entirely and fell through to
    # a weak LLM fallback that wrongly claimed no data existed — even
    # though "宜蘭景點" (same intent, different wording) worked fine.
    for query in ("宜蘭美景", "宜蘭風景", "宜蘭秘境", "宜蘭海景", "宜蘭絕景", "宜蘭景點"):
        assert line_bot._query_subject(query) == "景點", query


def _write_registry(root: Path, entries: list[dict]) -> None:
    registry = root / "wiki" / "_registry"
    registry.mkdir(parents=True)
    (registry / "city-subject-store.json").write_text(
        json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8"
    )


def _entry(
    store: str,
    subject: str = "餐廳",
    *,
    phone: str = "02-1234-5678",
    reservation_url: str = "https://example.test/reserve",
    google_maps_url: str = "",
    gps: tuple[float, float] | None = (25.0, 121.0),
) -> line_bot.RegistryEntry:
    return line_bot.RegistryEntry(
        city="新北市",
        subject=subject,
        store=store,
        source="wiki/entities/example.md",
        address="新北市板橋區文化路1號",
        gps=gps,
        highlights=("特色",),
        rating=4.5,
        rating_count=10,
        status="resolved",
        phone=phone,
        reservation_url=reservation_url,
        google_maps_url=google_maps_url,
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
                "phone": "02-2897-1234",
                "reservation_url": "https://example.test/coffee-first/reserve",
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
    assert (
        "- 店名：COFFEE FIRST（Google 地圖："
        "https://www.google.com/maps/search/?api=1&query=25.1375317,121.4943154）"
    ) in result["answer"]
    assert "- 地址：臺北市北投區中央北路二段68之5號" in result["answer"]
    assert "- 電話：02-2897-1234" in result["answer"]
    assert "- 預約連結：https://example.test/coffee-first/reserve" in result["answer"]
    assert "- Google 星等：⭐ 4.9（72 則）" in result["answer"]
    assert "- 特色說明：澳式早午餐店；高蛋白巧克力軟餅乾" in result["answer"]
    assert "- GPS：https://www.google.com/maps/search/?api=1&query=25.1375317,121.4943154" in result["answer"]
    assert "<think>" not in result["answer"]


def test_tianmu_food_query_uses_curated_neighborhood_section_without_llm(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "天母餐廳",
                "address": "台北市士林區天母東路1號",
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "其他餐廳",
                "address": "台北市士林區文林路1號",
                "status": "resolved",
            },
        ],
    )
    page = tmp_path / "wiki" / "concepts" / "tianmu-food.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "## 天母（含芝山、士林北段）\n\n"
        "| Subject | Store | 地址 |\n|---|---|---|\n"
        "| 餐廳 | 天母餐廳 | 台北市士林區天母東路1號 |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("天母地區美食", tmp_path)

    assert result["error"] is None
    assert "天母餐廳" in result["answer"]
    assert "其他餐廳" not in result["answer"]


def test_taipei_ramen_query_matches_ramen_mentions_across_food_subjects(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "天玉麵",
                "address": "台北市士林區中山北路七段63巷3號",
                "highlights": ["天母商圈拉麵店"],
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "小吃",
                "store": "海鮮拉麵",
                "address": "台北市北投區磺港路76號",
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "其他餐廳",
                "address": "台北市大安區仁愛路1號",
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("台北好吃的拉麵", tmp_path)

    assert result["error"] is None
    assert "天玉麵" in result["answer"]
    assert "海鮮拉麵" in result["answer"]
    assert "其他餐廳" not in result["answer"]


def test_juancun_cuisine_query_excludes_unrelated_attraction_mentioning_juancun(
    tmp_path: Path, monkeypatch
) -> None:
    # Regression test for a real production bug (2026-09-15): "眷村菜"
    # wasn't a recognized subject, so the query fell back to plain keyword
    # search with NO category filter at all, pulling in a 景點 (attraction)
    # that happens to mention 眷村 in its description alongside the actual
    # restaurants — exactly what happened with "台北地區眷村菜" pulling in
    # 蟾蜍山煥民新村 (a preserved military-village historic site, not food).
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "陸光小館",
                "address": "台北市松山區敦化北路165巷4號",
                "highlights": ["眷村家常餐館，滷味櫃品項豐富"],
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "景點",
                "store": "蟾蜍山煥民新村",
                "address": "台北市文山區",
                "highlights": ["台北市少數保留完整的空軍眷村山城聚落"],
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("台北地區眷村菜", tmp_path)

    assert result["error"] is None
    assert "陸光小館" in result["answer"]
    assert "蟾蜍山煥民新村" not in result["answer"]


def test_hybrid_index_finds_topic_only_present_in_highlights(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "親子餐廳",
                "address": "台北市大安區仁愛路1號",
                "highlights": ["有兒童遊戲區，適合親子用餐"],
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "餐廳",
                "store": "一般餐廳",
                "address": "台北市大安區仁愛路2號",
                "highlights": ["適合朋友聚餐"],
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("台北適合親子的餐廳", tmp_path)

    assert result["error"] is None
    assert "親子餐廳" in result["answer"]
    assert "一般餐廳" not in result["answer"]


def test_registry_query_filters_beef_noodle_results_to_requested_district(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "小吃",
                "store": "吳家牛肉麵店",
                "address": "台北市北投區中央北路一段224號",
                "status": "resolved",
            },
            {
                "city": "台北市",
                "subject": "小吃",
                "store": "93番茄牛肉麵",
                "address": "台北市中正區青島東路3-2號",
                "status": "resolved",
            },
            {
                "city": "新北市",
                "subject": "小吃",
                "store": "蔡家牛肉麵",
                "address": "新北市中和區秀朗路三段153巷16弄12號",
                "booking_url": "https://example.test/cai/reserve",
                "status": "resolved",
            },
            {
                "city": "新北市",
                "subject": "餐廳",
                "store": "中和牛排館",
                "address": "新北市中和區景平路100號",
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(line_bot, "route", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError()))

    result = line_bot._query_all("中和牛肉麵", tmp_path)

    assert result["error"] is None
    assert "蔡家牛肉麵" in result["answer"]
    assert "- 預約連結：https://example.test/cai/reserve" in result["answer"]
    assert "中和牛排館" not in result["answer"]
    assert "吳家牛肉麵店" not in result["answer"]
    assert "93番茄牛肉麵" not in result["answer"]


def test_registry_query_excludes_removed_entries_and_supports_lodging(tmp_path: Path, monkeypatch) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "台北市",
                "subject": "住宿",
                "store": "北投溫泉旅館",
                "address": "臺北市北投區中山路1號",
                "phone": None,
                "reservation_url": None,
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
    assert "電話：" not in result["answer"]
    assert "預約連結：" not in result["answer"]
    assert (
        "- 店名：北投溫泉旅館（Google 地圖："
        "https://www.google.com/maps/search/?api=1&query=%E8%87%BA%E5%8C%97%E5%B8%82%E5%8C%97%E6%8A%95%E5%8D%80%E4%B8%AD%E5%B1%B1%E8%B7%AF1%E8%99%9F）"
    ) in result["answer"]


def test_registry_store_name_uses_explicit_google_maps_url() -> None:
    entry = _entry(
        "固定地圖店家",
        google_maps_url="https://maps.app.goo.gl/VniCUnrMFfqDtpCc7",
    )

    lines = line_bot._render_registry_entry_lines(entry)

    assert (
        "- 店名：固定地圖店家（Google 地圖："
        "https://maps.app.goo.gl/VniCUnrMFfqDtpCc7）"
    ) in lines
    assert "- GPS：https://maps.app.goo.gl/VniCUnrMFfqDtpCc7" in lines


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
    monkeypatch.setattr(
        line_bot,
        "route",
        lambda *_args, **_kwargs: {
            "subject": "早午餐",
            "scope": "unknown",
            "locations": [],
            "needs_confirmation": False,
        },
    )

    result = line_bot._query_all("北投有什麼早午餐？", tmp_path)

    assert result == {"answer": None, "sources": [], "error": "no_match"}


def test_regional_location_query_requests_confirmation_before_expanding_scope(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "嘉義縣",
                "subject": "住宿",
                "store": "竹崎住宿",
                "address": "嘉義縣竹崎鄉石棹1號",
                "status": "resolved",
            },
            {
                "city": "嘉義縣",
                "subject": "住宿",
                "store": "番路住宿",
                "address": "嘉義縣番路鄉隙頂1號",
                "status": "resolved",
            },
            {
                "city": "嘉義縣",
                "subject": "餐廳",
                "store": "阿里山餐廳",
                "address": "嘉義縣阿里山鄉樂野1號",
                "status": "resolved",
            },
        ],
    )
    monkeypatch.setattr(
        line_bot,
        "route",
        lambda *_args, **_kwargs: {
            "subject": "住宿",
            "scope": "regional",
            "locations": ["阿里山鄉", "竹崎鄉", "番路鄉"],
            "needs_confirmation": True,
        },
    )

    result = line_bot._query_all("阿里山住宿", tmp_path)

    assert result["error"] == "needs_location_confirmation"
    assert result["location_intent"].locations == ("阿里山鄉", "竹崎鄉", "番路鄉")


def test_location_query_asks_for_explicit_label_when_llm_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "嘉義縣",
                "subject": "住宿",
                "store": "嘉義阿里山住宿",
                "address": "嘉義縣竹崎鄉石棹1號",
                "status": "resolved",
            },
            {
                "city": "嘉義縣",
                "subject": "住宿",
                "store": "阿里山番路住宿",
                "address": "嘉義縣番路鄉隙頂1號",
                "status": "resolved",
            },
        ],
    )

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("provider chain exhausted")

    monkeypatch.setattr(line_bot, "route", unavailable)

    result = line_bot._query_all("阿里山住宿", tmp_path)

    assert result["error"] == "needs_location_confirmation"
    assert result["location_intent"].locations == ("番路鄉", "竹崎鄉")
    assert result["location_intent"].needs_confirmation is True


def test_location_confirmation_runs_registry_filter_for_confirmed_regions(
    tmp_path: Path, monkeypatch
) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "city": "嘉義縣",
                "subject": "住宿",
                "store": "竹崎住宿",
                "address": "嘉義縣竹崎鄉石棹1號",
                "status": "resolved",
            },
            {
                "city": "嘉義縣",
                "subject": "住宿",
                "store": "番路住宿",
                "address": "嘉義縣番路鄉隙頂1號",
                "status": "resolved",
            },
            {
                "city": "嘉義縣",
                "subject": "餐廳",
                "store": "阿里山餐廳",
                "address": "嘉義縣阿里山鄉樂野1號",
                "status": "resolved",
            },
        ],
    )
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    line_bot.PENDING_LOCATION_CONFIRMATIONS.clear()
    line_bot.QUERY_SESSIONS.clear()
    intent = line_bot.LocationIntent(
        subject="住宿",
        scope="regional",
        locations=("阿里山鄉", "竹崎鄉", "番路鄉"),
        needs_confirmation=True,
    )
    line_bot.PENDING_LOCATION_CONFIRMATIONS["user-1"] = line_bot.PendingLocationConfirmation(
        user_id="user-1",
        query="阿里山住宿",
        intent=intent,
        created_at=line_bot.time.monotonic(),
    )

    handled = anyio.run(
        line_bot._handle_location_confirmation_event,
        {"access_token": "token", "lifestyle_vault": tmp_path},
        line_bot.AskDannyEvent("reply-1", "user-1", "１"),
        "１",
    )

    assert handled is True
    assert "竹崎住宿" in sent[0]
    assert "番路住宿" in sent[0]
    assert "阿里山餐廳" not in sent[0]
    assert line_bot.QUERY_SESSIONS["user-1"].offset == 2
    assert "user-1" not in line_bot.PENDING_LOCATION_CONFIRMATIONS
    line_bot.QUERY_SESSIONS.clear()


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


def test_query_options_and_sheet_rows_use_the_explicit_export_contract() -> None:
    options = line_bot._render_query_options(True)
    rows = line_bot._registry_entry_rows((_entry("測試餐廳"),))

    assert "1. 再看幾筆（例如：再看 10 筆）" in options
    assert "2. 終止輸出" in options
    assert "3. 匯出目前已顯示的資料到我的 Google Sheet" in options
    assert rows == [
        ["主題", "店名", "地址", "電話", "預約連結", "Google 星等", "特色說明", "GPS"],
        [
            "餐廳",
            "測試餐廳",
            "新北市板橋區文化路1號",
            "02-1234-5678",
            "https://example.test/reserve",
            "⭐ 4.5（10 則）",
            "特色",
            "https://www.google.com/maps/search/?api=1&query=25,121",
        ],
    ]


def test_query_session_can_show_user_selected_count_and_terminate(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    line_bot.QUERY_SESSIONS.clear()
    line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(
        entries=(_entry("第一家"), _entry("第二家"), _entry("第三家")),
        offset=1,
    )
    cfg = {"access_token": "token"}
    event = line_bot.AskDannyEvent("reply-1", "user-1", "再看 2 筆")

    anyio.run(line_bot._handle_query_session_event, cfg, event, event.text)

    assert "第二家" in sent[0]
    assert "第三家" in sent[0]
    assert line_bot.QUERY_SESSIONS["user-1"].offset == 3

    anyio.run(
        line_bot._handle_query_session_event,
        cfg,
        line_bot.AskDannyEvent("reply-2", "user-1", "2"),
        "2",
    )

    assert sent[-1] == "已終止這次輸出。"
    assert "user-1" not in line_bot.QUERY_SESSIONS


def test_query_session_accepts_bare_numeric_count_after_prompt(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    line_bot.QUERY_SESSIONS.clear()
    line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(
        entries=(_entry("第一家"), _entry("第二家"), _entry("第三家")),
        offset=1,
    )

    handled = anyio.run(
        line_bot._handle_query_session_event,
        {"access_token": "token"},
        line_bot.AskDannyEvent("reply-1", "user-1", "10"),
        "10",
    )

    assert handled is True
    assert "第二家" in sent[0]
    assert "第三家" in sent[0]
    assert line_bot.QUERY_SESSIONS["user-1"].offset == 3


def test_query_session_option_1_sets_awaiting_count_flag(monkeypatch) -> None:
    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    line_bot.QUERY_SESSIONS.clear()
    line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(
        entries=tuple(_entry(f"第{i}家") for i in range(7)),
        offset=1,
    )

    anyio.run(
        line_bot._handle_query_session_event,
        {"access_token": "token"},
        line_bot.AskDannyEvent("reply-1", "user-1", "1"),
        "1",
    )

    assert line_bot.QUERY_SESSIONS["user-1"].awaiting_count is True


def test_query_session_count_of_1_to_3_after_prompt_does_not_collide_with_menu(monkeypatch) -> None:
    # Regression test for a real bug reported after live use (2026-09-15):
    # answering "how many more?" with exactly 1, 2, or 3 was silently
    # swallowed by the fixed menu options (1=再看幾筆, 2=終止輸出,
    # 3=匯出...) instead of being treated as the requested count.
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)

    for answer, expected_offset in (("1", 2), ("2", 3), ("3", 4)):
        sent.clear()
        line_bot.QUERY_SESSIONS.clear()
        line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(
            entries=tuple(_entry(f"第{i}家") for i in range(7)),
            offset=1,
            awaiting_count=True,
        )

        handled = anyio.run(
            line_bot._handle_query_session_event,
            {"access_token": "token"},
            line_bot.AskDannyEvent("reply-1", "user-1", answer),
            answer,
        )

        assert handled is True
        assert sent != ["已終止這次輸出。"], f"answer={answer!r} was treated as terminate"
        assert sent[-1].startswith("目前顯示第"), f"answer={answer!r} did not render as a result page"
        # If export had incorrectly triggered, _start_google_export pops the
        # session — this line would KeyError instead of just failing.
        assert line_bot.QUERY_SESSIONS["user-1"].offset == expected_offset
        assert line_bot.QUERY_SESSIONS["user-1"].awaiting_count is False


def test_query_session_awaiting_count_falls_through_to_terminate_on_non_numeric_reply(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    line_bot.QUERY_SESSIONS.clear()
    line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(
        entries=tuple(_entry(f"第{i}家") for i in range(7)),
        offset=1,
        awaiting_count=True,
    )

    anyio.run(
        line_bot._handle_query_session_event,
        {"access_token": "token"},
        line_bot.AskDannyEvent("reply-1", "user-1", "終止"),
        "終止",
    )

    assert sent == ["已終止這次輸出。"]
    assert "user-1" not in line_bot.QUERY_SESSIONS


def test_google_export_option_is_fail_closed_without_oauth_config(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "google_oauth_config_from_env", lambda: None)
    line_bot.QUERY_SESSIONS.clear()
    line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(
        entries=(_entry("第一家"),),
        offset=1,
    )

    anyio.run(
        line_bot._handle_query_session_event,
        {"access_token": "token"},
        line_bot.AskDannyEvent("reply-1", "user-1", "3"),
        "3",
    )

    assert sent == ["Google Sheet 匯出尚未設定，請先通知 Danny 設定 Google OAuth。"]
    assert "user-1" in line_bot.QUERY_SESSIONS


def test_initial_registry_reply_includes_actions_and_stores_displayed_offset(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    entries = tuple(_entry(f"第 {index} 家") for index in range(1, 7))
    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(
        line_bot,
        "_query_all",
        lambda _text, _root: {
            "answer": line_bot._render_registry_answer(list(entries)),
            "sources": [line_bot.REGISTRY_SOURCE_TITLE],
            "error": None,
            "registry_entries": entries,
        },
    )
    monkeypatch.setattr(line_bot, "vault_root", lambda _cfg: Path("/tmp/lifestyle-vault"))
    line_bot.QUERY_SESSIONS.clear()

    anyio.run(
        line_bot.handle_text_event,
        {"access_token": "token", "allowed_users": set()},
        line_bot.AskDannyEvent("reply-1", "user-1", "新北市有什麼美食？"),
    )

    assert "1. 再看幾筆（例如：再看 10 筆）" in sent[0]
    assert "3. 匯出目前已顯示的資料到我的 Google Sheet" in sent[0]
    assert line_bot.QUERY_SESSIONS["user-1"].offset == 5


def test_google_export_stores_only_currently_displayed_entries(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "google_oauth_config_from_env", lambda: object())
    monkeypatch.setattr(
        line_bot,
        "google_authorization_url",
        lambda _config, state: f"https://accounts.google.com/?state={state}",
    )
    line_bot.QUERY_SESSIONS.clear()
    line_bot.PENDING_GOOGLE_EXPORTS.clear()
    entries = tuple(_entry(f"第 {index} 家") for index in range(1, 5))
    line_bot.QUERY_SESSIONS["user-1"] = line_bot.QuerySession(entries=entries, offset=2)

    anyio.run(
        line_bot._handle_query_session_event,
        {"access_token": "token"},
        line_bot.AskDannyEvent("reply-1", "user-1", "3"),
        "3",
    )

    assert "請點擊以下連結" in sent[0]
    assert "user-1" not in line_bot.QUERY_SESSIONS
    assert len(line_bot.PENDING_GOOGLE_EXPORTS) == 1
    pending = next(iter(line_bot.PENDING_GOOGLE_EXPORTS.values()))
    assert pending.entries == entries[:2]


def test_google_authorization_is_one_time_and_does_not_request_account_identity() -> None:
    url = google_authorization_url(
        GoogleOAuthConfig("client-id", "client-secret", "https://example.test/callback"),
        "opaque-state",
    )
    params = parse_qs(urlparse(url).query)

    assert params["access_type"] == ["online"]
    assert params["prompt"] == ["select_account"]
    assert params["scope"] == ["https://www.googleapis.com/auth/spreadsheets"]
    assert "email" not in params
    assert "openid" not in params


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


# ── Nearby (location-based) queries ────────────────────────────────────────

def test_webhook_event_parser_accepts_location_messages() -> None:
    events = line_bot.askdanny_events_from_webhook(
        {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-1",
                    "source": {"userId": "user-1"},
                    "message": {"type": "location", "latitude": 25.0330, "longitude": 121.5654},
                },
                {
                    "type": "message",
                    "replyToken": "reply-2",
                    "source": {"userId": "user-2"},
                    "message": {"type": "location", "latitude": "not-a-number", "longitude": 121.0},
                },
                {
                    "type": "message",
                    "replyToken": "",
                    "source": {"userId": "user-3"},
                    "message": {"type": "location", "latitude": 25.0, "longitude": 121.0},
                },
            ]
        }
    )

    assert events == [
        line_bot.AskDannyLocationEvent("reply-1", "user-1", 25.0330, 121.5654)
    ]


def test_haversine_distance_matches_known_one_degree_latitude() -> None:
    # 1 degree of latitude is ~111.2 km everywhere on Earth — a stable,
    # easy-to-verify sanity check independent of longitude convergence.
    distance = line_bot._haversine_km(25.0, 121.0, 26.0, 121.0)
    assert 111.0 < distance < 111.4


def test_haversine_distance_is_zero_for_identical_points() -> None:
    assert line_bot._haversine_km(25.0, 121.0, 25.0, 121.0) == 0.0


def test_parse_nearby_radius_prefers_explicit_km_over_minutes() -> None:
    assert line_bot._parse_nearby_radius("附近 5 公里有什麼美食") == (5.0, "walk")
    assert line_bot._parse_nearby_radius("附近 500 公尺有什麼美食") == (0.5, "walk")


def test_parse_nearby_radius_converts_walk_minutes_conservatively() -> None:
    radius, mode = line_bot._parse_nearby_radius("走路 10 分鐘內有什麼早餐店")
    # 10 min * 80 m/min / 1.3 road-indirection factor / 1000 ≈ 0.615 km.
    assert mode == "walk"
    assert 0.5 < radius < 0.7


def test_parse_nearby_radius_falls_back_to_default_and_clamps() -> None:
    assert line_bot._parse_nearby_radius("附近有什麼美食") == (line_bot.DEFAULT_NEARBY_RADIUS_KM, "walk")
    radius, _mode = line_bot._parse_nearby_radius("附近 999 公里有什麼美食")
    assert radius == line_bot.MAX_NEARBY_RADIUS_KM


def test_parse_nearby_radius_detects_drive_mode_from_hours() -> None:
    radius, mode = line_bot._parse_nearby_radius("開車1小時有什麼美食")
    assert mode == "drive"
    # 1 hr * 40 km/h / 1.3 road-indirection factor ≈ 30.8 km.
    assert 30.0 < radius < 31.5


def test_parse_nearby_radius_drive_mode_uses_its_own_default_and_cap() -> None:
    assert line_bot._parse_nearby_radius("開車有什麼美食") == (line_bot.DEFAULT_DRIVE_RADIUS_KM, "drive")
    radius, mode = line_bot._parse_nearby_radius("開車 99 小時有什麼美食")
    assert mode == "drive"
    assert radius == line_bot.MAX_DRIVE_RADIUS_KM


def test_parse_nearby_radius_explicit_km_overrides_drive_mode_default() -> None:
    assert line_bot._parse_nearby_radius("開車 10 公里有什麼美食") == (10.0, "drive")


def test_parse_nearby_radius_handles_chinese_numerals_from_voice_transcripts() -> None:
    # Regression test for a real production bug (2026-09-15): voice queries
    # transcribe numbers as Chinese numerals, not Arabic digits, and the
    # radius silently fell back to the 1km default every time as a result.
    assert line_bot._parse_nearby_radius("附近兩公里之內有什麼餐廳") == (2.0, "walk")
    assert line_bot._parse_nearby_radius("附近十公里之內有什麼餐廳") == (10.0, "walk")
    assert line_bot._parse_nearby_radius("開車一小時內有什麼美食")[1] == "drive"
    radius, _mode = line_bot._parse_nearby_radius("開車一小時內有什麼美食")
    assert 30.0 < radius < 31.5  # same 1hr drive-mode math as the digit form


def test_parse_nearby_radius_handles_chinese_tens_and_half() -> None:
    assert line_bot._parse_nearby_radius("附近十五公里有什麼景點") == (15.0, "walk")
    assert line_bot._parse_nearby_radius("附近半公里有什麼咖啡廳") == (0.5, "walk")


def test_normalize_chinese_numerals_only_touches_numbers_immediately_before_a_unit() -> None:
    # "十字路口" has no unit word after "十" — must not be mangled.
    assert line_bot._normalize_chinese_numerals("十字路口附近有什麼美食") == "十字路口附近有什麼美食"


def test_nearby_registry_matches_filters_by_radius_subject_and_gps_presence() -> None:
    near_food = _entry("附近的店", subject="早午餐", gps=(25.001, 121.001))
    far_food = _entry("很遠的店", subject="早午餐", gps=(25.5, 121.5))
    no_gps = _entry("沒有座標的店", subject="早午餐", gps=None)
    wrong_subject = _entry("附近的旅館", subject="住宿", gps=(25.001, 121.001))

    matches = line_bot._nearby_registry_matches(
        "早午餐", 25.0, 121.0, 5.0, [near_food, far_food, no_gps, wrong_subject]
    )

    assert [entry.store for entry in matches] == ["附近的店"]
    assert matches[0].distance_km is not None
    assert matches[0].distance_km < 1.0


def test_nearby_registry_matches_sorts_by_ascending_distance_when_subject_omitted() -> None:
    closer = _entry("比較近", subject="景點", gps=(25.001, 121.001))
    farther = _entry("比較遠", subject="早午餐", gps=(25.01, 121.01))

    matches = line_bot._nearby_registry_matches(None, 25.0, 121.0, 5.0, [farther, closer])

    assert [entry.store for entry in matches] == ["比較近", "比較遠"]
    assert matches[0].distance_km < matches[1].distance_km


def test_location_event_then_nearby_text_query_returns_distance_and_pagination(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    entries = [_entry("巷口早餐店", subject="早午餐", gps=(25.001, 121.001))]
    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_load_registry_entries", lambda _root: entries)
    monkeypatch.setattr(line_bot, "vault_root", lambda _cfg: Path("/fake/vault"))
    line_bot.PENDING_LOCATIONS.clear()
    line_bot.QUERY_SESSIONS.clear()
    cfg = {"access_token": "token", "allowed_users": set()}

    anyio.run(
        line_bot.handle_location_event,
        cfg,
        line_bot.AskDannyLocationEvent("reply-1", "user-1", 25.0, 121.0),
    )
    assert "收到你的位置了" in sent[-1]
    assert "user-1" in line_bot.PENDING_LOCATIONS

    handled = anyio.run(
        line_bot._handle_nearby_event,
        cfg,
        line_bot.AskDannyEvent("reply-2", "user-1", "附近有什麼早餐店"),
        "附近有什麼早餐店",
    )

    assert handled is True
    assert "巷口早餐店" in sent[-1]
    assert "距離：約 0.2 公里（直線距離估算，非實際路徑）" in sent[-1]
    assert "搜尋範圍：走路約" in sent[-1]
    assert "再看幾筆" in sent[-1] or "已沒有更多資料" in sent[-1]
    assert "user-1" in line_bot.QUERY_SESSIONS


def test_nearby_query_without_pending_location_falls_through(monkeypatch) -> None:
    line_bot.PENDING_LOCATIONS.clear()
    handled = anyio.run(
        line_bot._handle_nearby_event,
        {"access_token": "token"},
        line_bot.AskDannyEvent("reply-1", "user-1", "附近有什麼美食"),
        "附近有什麼美食",
    )
    assert handled is False


def test_unauthorized_user_location_is_not_stored(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    line_bot.PENDING_LOCATIONS.clear()
    cfg = {"access_token": "token", "allowed_users": {"someone-else"}}

    anyio.run(
        line_bot.handle_location_event,
        cfg,
        line_bot.AskDannyLocationEvent("reply-1", "intruder", 25.0, 121.0),
    )

    assert "intruder" not in line_bot.PENDING_LOCATIONS
    assert sent == [line_bot.GENERIC_DENY_TEXT]


# ── Pasted Google Maps links ────────────────────────────────────────────────

def test_extract_maps_coords_parses_at_sign_query_and_place_pin_formats() -> None:
    assert line_bot._extract_maps_coords("https://www.google.com/maps/@25.033,121.5654,17z") == (
        25.033, 121.5654,
    )
    assert line_bot._extract_maps_coords(
        "https://www.google.com/maps?q=25.033,121.5654"
    ) == (25.033, 121.5654)
    assert line_bot._extract_maps_coords(
        "https://www.google.com/maps/place/x/data=!4m2!3m1!1s0x0!3d25.033!4d121.5654"
    ) == (25.033, 121.5654)
    assert line_bot._extract_maps_coords("https://maps.app.goo.gl/opaque-id") is None


def test_extract_maps_place_name_decodes_url_encoded_segment() -> None:
    url = "https://www.google.com/maps/place/251%E6%96%B0%E5%8C%97%E5%B8%82%E6%B7%A1%E6%B0%B4%E5%8D%80/data=!4m2"
    assert line_bot._extract_maps_place_name(url) == "251新北市淡水區"
    assert line_bot._extract_maps_place_name("https://www.google.com/maps/@25.0,121.0,17z") is None


def test_resolve_location_from_text_ignores_non_maps_hosts() -> None:
    coords = anyio.run(line_bot._resolve_location_from_text, "看這個 https://example.com/foo")
    assert coords is None


def test_resolve_location_from_text_parses_direct_coords_without_any_network_call(monkeypatch) -> None:
    async def unexpected_get(self, *_args, **_kwargs):
        raise AssertionError("should not make a network call when coords are already in the URL")

    monkeypatch.setattr(httpx.AsyncClient, "get", unexpected_get)

    coords = anyio.run(
        line_bot._resolve_location_from_text,
        "這附近 https://www.google.com/maps/@25.033,121.5654,17z 有什麼美食",
    )

    assert coords == (25.033, 121.5654)


def test_resolve_location_from_text_follows_short_link_redirect_for_pin_links(monkeypatch) -> None:
    resolved_url = "https://www.google.com/maps/@25.1737,121.4392,17z"

    async def fake_get(self, url, **_kwargs):
        return httpx.Response(200, request=httpx.Request("GET", resolved_url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    coords = anyio.run(
        line_bot._resolve_location_from_text, "https://maps.app.goo.gl/nZjE34bdegmKbXND7?g_st=ac"
    )

    assert coords == (25.1737, 121.4392)


def test_resolve_location_from_text_falls_back_to_places_api_for_place_share_links(monkeypatch) -> None:
    resolved_url = (
        "https://www.google.com/maps/place/251%E6%96%B0%E5%8C%97%E5%B8%82%E6%B7%A1%E6%B0%B4%E5%8D%80"
        "/data=!4m2!3m1!1s0x3442afb9f6cca331:0x303a389d8bef900f"
    )
    places_requests: list[dict] = []

    async def fake_get(self, url, **_kwargs):
        return httpx.Response(200, request=httpx.Request("GET", resolved_url))

    async def fake_post(self, url, json, headers):
        places_requests.append({"url": url, "json": json, "headers": headers})
        return httpx.Response(
            200,
            json={"places": [{"location": {"latitude": 25.17, "longitude": 121.45}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "test-key")

    coords = anyio.run(
        line_bot._resolve_location_from_text, "https://maps.app.goo.gl/nZjE34bdegmKbXND7?g_st=ac"
    )

    assert coords == (25.17, 121.45)
    assert places_requests[0]["json"] == {"textQuery": "251新北市淡水區"}
    assert places_requests[0]["headers"]["X-Goog-Api-Key"] == "test-key"


def test_resolve_location_from_text_returns_none_without_places_api_key(monkeypatch) -> None:
    resolved_url = (
        "https://www.google.com/maps/place/251%E6%96%B0%E5%8C%97%E5%B8%82%E6%B7%A1%E6%B0%B4%E5%8D%80"
        "/data=!4m2!3m1!1s0x3442afb9f6cca331:0x303a389d8bef900f"
    )

    async def fake_get(self, url, **_kwargs):
        return httpx.Response(200, request=httpx.Request("GET", resolved_url))

    async def unexpected_post(self, *_args, **_kwargs):
        raise AssertionError("should not call Places API without a configured key")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "post", unexpected_post)
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)

    coords = anyio.run(
        line_bot._resolve_location_from_text, "https://maps.app.goo.gl/nZjE34bdegmKbXND7?g_st=ac"
    )

    assert coords is None


def test_maps_link_event_with_query_answers_immediately(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_resolve(_text: str) -> tuple[float, float]:
        return (25.001, 121.001)

    entries = [_entry("巷口早餐店", subject="早午餐", gps=(25.001, 121.001))]
    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_resolve_location_from_text", fake_resolve)
    monkeypatch.setattr(line_bot, "_load_registry_entries", lambda _root: entries)
    monkeypatch.setattr(line_bot, "vault_root", lambda _cfg: Path("/fake/vault"))
    line_bot.PENDING_LOCATIONS.clear()
    line_bot.QUERY_SESSIONS.clear()
    cfg = {"access_token": "token", "allowed_users": set()}

    handled = anyio.run(
        line_bot._handle_maps_link_event,
        cfg,
        line_bot.AskDannyEvent("reply-1", "user-1", "https://maps.app.goo.gl/xyz 附近有什麼早午餐"),
        "https://maps.app.goo.gl/xyz 附近有什麼早午餐",
    )

    assert handled is True
    assert "巷口早餐店" in sent[-1]
    assert "user-1" in line_bot.PENDING_LOCATIONS
    assert "user-1" in line_bot.QUERY_SESSIONS


def test_maps_link_event_without_query_prompts_for_next_step(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_resolve(_text: str) -> tuple[float, float]:
        return (25.001, 121.001)

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_resolve_location_from_text", fake_resolve)
    line_bot.PENDING_LOCATIONS.clear()
    cfg = {"access_token": "token", "allowed_users": set()}

    handled = anyio.run(
        line_bot._handle_maps_link_event,
        cfg,
        line_bot.AskDannyEvent("reply-1", "user-1", "https://maps.app.goo.gl/xyz"),
        "https://maps.app.goo.gl/xyz",
    )

    assert handled is True
    assert "收到你分享的地圖位置了" in sent[-1]
    assert "user-1" in line_bot.PENDING_LOCATIONS


def test_maps_link_event_replies_with_guidance_when_resolution_fails(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_resolve(_text: str) -> None:
        return None

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_resolve_location_from_text", fake_resolve)
    line_bot.PENDING_LOCATIONS.clear()
    cfg = {"access_token": "token", "allowed_users": set()}

    handled = anyio.run(
        line_bot._handle_maps_link_event,
        cfg,
        line_bot.AskDannyEvent("reply-1", "user-1", "https://example.com/not-a-maps-link"),
        "https://example.com/not-a-maps-link",
    )

    assert handled is True
    assert "沒辦法從這個地圖連結取得座標" in sent[-1]
    assert "user-1" not in line_bot.PENDING_LOCATIONS


def test_maps_link_event_returns_false_without_any_url() -> None:
    handled = anyio.run(
        line_bot._handle_maps_link_event,
        {"access_token": "token", "allowed_users": set()},
        line_bot.AskDannyEvent("reply-1", "user-1", "附近有什麼美食"),
        "附近有什麼美食",
    )
    assert handled is False


# ── Voice queries ────────────────────────────────────────────────────────

def test_webhook_event_parser_accepts_audio_messages() -> None:
    events = line_bot.askdanny_events_from_webhook(
        {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-1",
                    "source": {"userId": "user-1"},
                    "message": {"type": "audio", "id": "msg-abc", "duration": 4200},
                },
                {
                    "type": "message",
                    "replyToken": "reply-2",
                    "source": {"userId": "user-2"},
                    "message": {"type": "audio", "duration": 1000},
                },
            ]
        }
    )

    assert events == [line_bot.AskDannyAudioEvent("reply-1", "user-1", "msg-abc")]


def test_download_line_audio_content_returns_bytes_on_success(monkeypatch) -> None:
    async def fake_get(self, url, headers):
        assert url == "https://api-data.line.me/v2/bot/message/msg-abc/content"
        assert headers == {"Authorization": "Bearer token"}
        return httpx.Response(200, content=b"raw-audio-bytes", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    content = anyio.run(line_bot._download_line_audio_content, "token", "msg-abc")

    assert content == b"raw-audio-bytes"


def test_download_line_audio_content_returns_none_on_failure(monkeypatch) -> None:
    async def fake_get(self, url, headers):
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    content = anyio.run(line_bot._download_line_audio_content, "token", "msg-abc")

    assert content is None


def test_handle_audio_event_transcribes_and_reuses_text_pipeline(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_download(_access_token: str, _message_id: str) -> bytes:
        return b"raw-audio-bytes"

    async def fake_transcribe(_audio_bytes: bytes, **_kwargs) -> str:
        return "北投有什麼早午餐"

    def fake_query_all(query, _root):
        assert query == "北投有什麼早午餐"
        return {
            "answer": "\n- 主題：早午餐\n- 店名：COFFEE FIRST",
            "sources": ["城市 × 主題 × 店家彙整"],
            "error": None,
        }

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_download_line_audio_content", fake_download)
    monkeypatch.setattr(line_bot, "transcribe", fake_transcribe)
    monkeypatch.setattr(line_bot, "vault_root", lambda _cfg: Path("/fake/vault"))
    monkeypatch.setattr(line_bot, "_query_all", fake_query_all)
    line_bot.QUERY_SESSIONS.clear()
    line_bot.PENDING_LOCATIONS.clear()
    cfg = {"access_token": "token", "allowed_users": set()}

    anyio.run(
        line_bot.handle_audio_event, cfg, line_bot.AskDannyAudioEvent("reply-1", "user-1", "msg-abc")
    )

    assert "COFFEE FIRST" in sent[-1]


def test_handle_audio_event_replies_with_guidance_when_download_fails(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_download(_access_token: str, _message_id: str) -> None:
        return None

    async def unexpected_transcribe(*_args, **_kwargs):
        raise AssertionError("should not transcribe when download failed")

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_download_line_audio_content", fake_download)
    monkeypatch.setattr(line_bot, "transcribe", unexpected_transcribe)
    cfg = {"access_token": "token", "allowed_users": set()}

    anyio.run(
        line_bot.handle_audio_event, cfg, line_bot.AskDannyAudioEvent("reply-1", "user-1", "msg-abc")
    )

    assert "沒辦法下載這段語音" in sent[-1]


def test_handle_audio_event_replies_with_guidance_when_transcription_fails(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_download(_access_token: str, _message_id: str) -> bytes:
        return b"raw-audio-bytes"

    async def fake_transcribe(*_args, **_kwargs):
        raise LLMError("all candidates exhausted")

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_download_line_audio_content", fake_download)
    monkeypatch.setattr(line_bot, "transcribe", fake_transcribe)
    cfg = {"access_token": "token", "allowed_users": set()}

    anyio.run(
        line_bot.handle_audio_event, cfg, line_bot.AskDannyAudioEvent("reply-1", "user-1", "msg-abc")
    )

    assert "暫時沒辦法辨識這段語音" in sent[-1]


def test_handle_audio_event_replies_with_guidance_for_empty_transcript(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def fake_download(_access_token: str, _message_id: str) -> bytes:
        return b"raw-audio-bytes"

    async def fake_transcribe(*_args, **_kwargs) -> str:
        return ""

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_download_line_audio_content", fake_download)
    monkeypatch.setattr(line_bot, "transcribe", fake_transcribe)
    cfg = {"access_token": "token", "allowed_users": set()}

    anyio.run(
        line_bot.handle_audio_event, cfg, line_bot.AskDannyAudioEvent("reply-1", "user-1", "msg-abc")
    )

    assert "聽不清楚這段語音內容" in sent[-1]


def test_unauthorized_user_audio_is_not_downloaded_or_transcribed(monkeypatch) -> None:
    sent: list[str] = []

    async def fake_reply(_access_token: str, _reply_token: str, text: str) -> bool:
        sent.append(text)
        return True

    async def unexpected_download(*_args, **_kwargs):
        raise AssertionError("should not download audio for an unauthorized user")

    async def unexpected_transcribe(*_args, **_kwargs):
        raise AssertionError("should not transcribe for an unauthorized user")

    monkeypatch.setattr(line_bot, "reply_message", fake_reply)
    monkeypatch.setattr(line_bot, "_download_line_audio_content", unexpected_download)
    monkeypatch.setattr(line_bot, "transcribe", unexpected_transcribe)
    cfg = {"access_token": "token", "allowed_users": {"someone-else"}}

    anyio.run(
        line_bot.handle_audio_event, cfg, line_bot.AskDannyAudioEvent("reply-1", "intruder", "msg-abc")
    )

    assert sent == [line_bot.GENERIC_DENY_TEXT]
