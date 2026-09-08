import json
import anyio
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from personalkm.query import line_bot
from personalkm.query.google_sheets import GoogleOAuthConfig, google_authorization_url


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
) -> line_bot.RegistryEntry:
    return line_bot.RegistryEntry(
        city="新北市",
        subject=subject,
        store=store,
        source="wiki/entities/example.md",
        address="新北市板橋區文化路1號",
        gps=(25.0, 121.0),
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
        line_bot.AskDannyEvent("reply-1", "user-1", "1"),
        "1",
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
