import httpx
import pytest

from bot.config import Settings
from bot.link_processor import process_url, resolve_google_maps_short_link


@pytest.mark.anyio
async def test_process_url_writes_note_when_fetch_is_forbidden(monkeypatch):
    async def fake_fetch_page(url, timeout_seconds, max_chars):
        request = httpx.Request("GET", url)
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("Forbidden", request=request, response=response)

    async def fake_jina_returns_none(url, timeout_seconds, max_chars, settings=None):
        return None  # Jina also failed → fall back to error stub

    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_jina_returns_none
    )

    note = await process_url(Settings(), "https://openai.com/")

    assert note.title == "openai.com"
    assert note.url == "https://openai.com/"
    assert "HTTP 403" in note.summary
    assert note.category == "tech"


@pytest.mark.anyio
async def test_process_url_403_falls_back_to_jina(monkeypatch):
    """When a generic URL returns 403, the capture bot should try Jina
    Reader before giving up with a hollow error stub. This is the
    bobowin.blog case — WAF blocks Render IPs but Jina can fetch it."""

    async def fake_fetch_page(url, timeout_seconds, max_chars):
        request = httpx.Request("GET", url)
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("Forbidden", request=request, response=response)

    async def fake_jina_success(url, timeout_seconds, max_chars, settings=None):
        from personalkm.capture.link_processor import ExtractedContent

        return ExtractedContent(
            title="望古瀑布步道｜Bobowin",
            text="望古瀑布步道攻略，交通便利度、路線難易度、推薦指數。",
            platform="web",
            extraction_status="ok",
        )

    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_jina_success
    )

    note = await process_url(Settings(), "https://bobowin.blog/wanggu-hiking/")

    assert note.extraction_status == "ok"
    assert "HTTP 403" not in (note.summary or "")
    assert "望古瀑布" in note.title or "望古瀑布" in (note.summary or "")


@pytest.mark.anyio
async def test_process_url_handles_google_ai_mode_share_without_fetching(monkeypatch):
    async def fake_fetch_page(url, timeout_seconds, max_chars):
        raise AssertionError("Google AI Mode share links should not be fetched")

    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fake_fetch_page)

    note = await process_url(Settings(), "https://share.google/aimode/8uyYWVgle7A2ZDGFx")

    assert note.title == "Google AI Mode share"
    assert note.url == "https://share.google/aimode/8uyYWVgle7A2ZDGFx"
    assert note.platform == "google-ai-mode"
    assert note.extraction_status == "blocked"
    assert note.needs_review
    assert "HTTP 429" in note.summary
    assert note.category == "tech"


@pytest.mark.anyio
async def test_process_url_summarizes_google_ai_mode_pasted_answer(monkeypatch):
    async def fake_fetch_page(url, timeout_seconds, max_chars):
        raise AssertionError("Google AI Mode pasted answers should not fetch the share page")

    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fake_fetch_page)

    url = "https://share.google/aimode/YyTssJIr44VpGTZWt"
    message = f"{url}\nAI Mode 回答：這篇內容整理 AI agent workflow、自動化與知識管理實作。"

    note = await process_url(Settings(), url, message)

    assert note.title == "Google AI Mode pasted answer"
    assert note.platform == "google-ai-mode"
    assert note.extraction_status == "ok"
    assert not note.needs_review
    assert "AI agent workflow" in note.summary
    assert note.category == "tech"


@pytest.mark.anyio
async def test_process_url_prefers_pasted_social_caption(monkeypatch):
    async def fake_fetch_page(url, timeout_seconds, max_chars):
        raise AssertionError("Social caption text should be used before fetching auth-walled pages")

    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fake_fetch_page)

    url = "https://www.threads.net/@user/post/abc"
    message = f"{url}\n這篇貼文整理 AI agent workflow、local-first 知識管理與自動化實作心得。"

    note = await process_url(Settings(), url, message)

    assert note.title == "Threads pasted post"
    assert note.platform == "threads"
    assert note.extraction_status == "ok"
    assert not note.needs_review
    assert not note.needs_local_worker
    assert "AI agent workflow" in note.summary
    assert "使用者貼上的社群貼文內容" in note.body_markdown


FB_SHARE_URL = "https://www.facebook.com/share/p/1DeswYpjik/"


@pytest.mark.anyio
async def test_process_url_facebook_uses_jina_not_direct_fetch(monkeypatch):
    """2026-08-24 regression: FB share links used to hit the generic web
    branch, where the direct GET got HTTP 400 and the capture became an
    error stub. They must route through Jina like IG/Threads instead."""

    async def fake_fetch_social_via_jina(url, timeout_seconds, max_chars, settings=None):
        assert "facebook.com" in url or "fb.me" in url
        from personalkm.capture.link_processor import ExtractedContent

        return ExtractedContent(
            title="張維峰's Post",
            text="ChatGPT 內建瀏覽器的 10 個實用用法，升級後的桌面應用程式內建多頁籤瀏覽與帳號登入態保持等能力。",
            platform="facebook",
            extraction_status="ok",
        )

    async def fail_fetch_page(url, timeout_seconds, max_chars):
        raise AssertionError("Facebook links must never go through direct fetch_page")

    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_fetch_social_via_jina
    )
    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fail_fetch_page)

    note = await process_url(Settings(), FB_SHARE_URL)

    assert note.platform == "facebook"
    assert note.extraction_status == "ok"
    assert "HTTP 400" not in (note.summary or "")
    assert "張維峰" in note.title or "ChatGPT" in note.summary


@pytest.mark.anyio
async def test_process_url_facebook_jina_failure_yields_blocked_stub(monkeypatch):
    async def fake_fetch_social_via_jina(url, timeout_seconds, max_chars, settings=None):
        return None  # Jina failed (private post / rate limit)

    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_fetch_social_via_jina
    )

    note = await process_url(Settings(), FB_SHARE_URL)

    # Blocked-stub semantics (like IG/Threads), NOT the generic-web error text
    assert note.platform == "facebook"
    assert note.extraction_status == "blocked"
    assert "HTTP 400" not in (note.summary or "")


GOOGLE_MAPS_SHARE_URL = "https://maps.app.goo.gl/UPEyo91mh8ztNetp9"


class _FakeRedirectResponse:
    def __init__(self, final_url: str, body: str = ""):
        self.url = final_url
        self.text = body


@pytest.mark.anyio
async def test_resolve_google_maps_short_link_extracts_place_name_and_coords(monkeypatch):
    # 2026-09-21: maps.app.goo.gl short links redirect (a plain HTTP 302,
    # no JS) straight to a canonical .../maps/place/<name>/@<lat>,<lng>,<z>z
    # URL when the link was shared as a distinct named place.
    async def fake_get(self, url, *args, **kwargs):
        return _FakeRedirectResponse(
            "https://www.google.com/maps/place/%E9%8F%A1%E6%B9%96/@25.174659,121.655503,17z/"
            "data=!3m1!4b1!4m6!3m5!1s0x345d4ce1e0f2861d:0x68f069c30e74f9f!8m2!3d25.174659!4d121.655503"
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    resolution = await resolve_google_maps_short_link(
        "https://maps.app.goo.gl/d24qMcNijvXy6rKv8", 30.0
    )

    assert resolution is not None
    assert resolution.name == "鏡湖"
    assert resolution.lat == pytest.approx(25.174659)
    assert resolution.lng == pytest.approx(121.655503)
    assert resolution.maps_url == (
        "https://www.google.com/maps/search/?api=1&query=25.174659,121.655503"
    )


@pytest.mark.anyio
async def test_resolve_google_maps_short_link_handles_coords_only_pin_shares(monkeypatch):
    # A bare pin-drop share (no associated named place) redirects to
    # .../maps/search/<lat>,+<lng> instead — coordinates only, no name.
    async def fake_get(self, url, *args, **kwargs):
        return _FakeRedirectResponse(
            "https://www.google.com/maps/search/25.165030,+121.409595?entry=tts"
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    resolution = await resolve_google_maps_short_link(
        "https://maps.app.goo.gl/UPEyo91mh8ztNetp9", 30.0
    )

    assert resolution is not None
    assert resolution.name is None
    assert resolution.lat == pytest.approx(25.165030)
    assert resolution.lng == pytest.approx(121.409595)


@pytest.mark.anyio
async def test_resolve_google_maps_short_link_returns_none_on_network_failure(monkeypatch):
    async def fake_get(self, url, *args, **kwargs):
        raise httpx.ConnectTimeout("boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    resolution = await resolve_google_maps_short_link("https://maps.app.goo.gl/x", 30.0)

    assert resolution is None


@pytest.mark.anyio
async def test_resolve_google_maps_short_link_returns_none_when_shape_unrecognized(monkeypatch):
    async def fake_get(self, url, *args, **kwargs):
        return _FakeRedirectResponse("https://www.google.com/maps/@25.0,121.0,10z")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    # No /place/ or /search/ segment — falls back to the generic @lat,lng
    # sniff, which this DOES match (still useful — coordinates only).
    resolution = await resolve_google_maps_short_link("https://maps.app.goo.gl/x", 30.0)

    assert resolution is not None
    assert resolution.name is None
    assert resolution.lat == pytest.approx(25.0)


@pytest.mark.anyio
async def test_resolve_google_maps_short_link_extracts_name_and_coords_from_data_url(monkeypatch):
    # 2026-09-22: some maps.app.goo.gl share links redirect to
    # /maps/place/<name>/data=… (no @lat,lng in the URL path). The
    # coordinates are in the HTML body's embedded JSON array.
    body = (
        '[[\\"0x3467f9752b9159b7:0xb410fad71255c407\\",'
        '\\"232宜蘭縣坪林區頭城鎮北宜公路56.5km處石牌縣界公園\\",'
        '[[231467.9279044201,121.20916580000001,24.976779399999998],'
        '[0,0,0],[1024,768],13.1]]'
    )

    async def fake_get(self, url, *args, **kwargs):
        return _FakeRedirectResponse(
            "https://www.google.com/maps/place/232%E5%AE%9C%E8%98%AD%E7%B8%A3%E5%9D%AA%E6%9E%97%E5%8D%80%E9%A0%AD%E5%9F%8E%E9%8E%AE%E5%8C%97%E5%AE%9C%E5%85%AC%E8%B7%AF56.5km%E8%99%95%E7%9F%B3%E7%89%8C%E7%B8%A3%E7%95%8C%E5%85%AC%E5%9C%92"
            "/data=!4m2!3m1!1s0x3467f9752b9159b7:0xb410fad71255c407",
            body=body,
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    resolution = await resolve_google_maps_short_link(
        "https://maps.app.goo.gl/f4rzsXd8bKX79iVj9", 30.0
    )

    assert resolution is not None
    assert resolution.name == "232宜蘭縣坪林區頭城鎮北宜公路56.5km處石牌縣界公園"
    assert resolution.lat == pytest.approx(24.976779399999998)
    assert resolution.lng == pytest.approx(121.20916580000001)
    assert resolution.maps_url == (
        "https://www.google.com/maps/search/?api=1&query=24.976779399999998,121.20916580000001"
    )


def _mock_no_resolution(monkeypatch):
    """No test here should hit the real network — resolve_google_maps_short_link()
    does a real httpx redirect follow, so every test mocks it explicitly.
    This variant simulates the redirect not resolving (offline, unknown
    shape, etc.), matching pre-#36 behavior for tests that don't care about
    the resolver."""
    async def fake_resolve(url, timeout_seconds):
        return None

    monkeypatch.setattr(
        "personalkm.capture.link_processor.resolve_google_maps_short_link", fake_resolve
    )


@pytest.mark.anyio
async def test_process_url_google_maps_uses_the_longer_timeout(monkeypatch):
    # 2026-09-21 regression: a real capture (log 202609201706_00001, sent
    # after the maps.app.goo.gl fix had already landed) still fell through
    # to the "couldn't extract" stub — Jina Reader has to fully render a
    # Google Maps page's client-side JS, which is meaningfully heavier than
    # a static IG/Threads fetch, so the general-purpose
    # request_timeout_seconds (12s) plausibly wasn't enough. Google Maps
    # now gets its own, longer budget (google_maps_timeout_seconds).
    _mock_no_resolution(monkeypatch)
    seen_timeout = None

    async def fake_fetch_social_via_jina(url, timeout_seconds, max_chars, settings=None):
        nonlocal seen_timeout
        seen_timeout = timeout_seconds
        from personalkm.capture.link_processor import ExtractedContent

        return ExtractedContent(
            title="某家咖啡廳",
            text="店名：某家咖啡廳\n地址：台北市中山區...",
            platform="google-maps",
            extraction_status="ok",
        )

    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_fetch_social_via_jina
    )

    settings = Settings()
    note = await process_url(settings, GOOGLE_MAPS_SHARE_URL)

    assert seen_timeout == settings.google_maps_timeout_seconds
    assert seen_timeout > settings.request_timeout_seconds
    assert note.extraction_status == "ok"


@pytest.mark.anyio
async def test_process_url_google_maps_jina_failure_yields_blocked_stub(monkeypatch):
    # Worst case: the redirect resolve AND Jina both come back empty —
    # only then should this still fall all the way to the fully-empty stub.
    _mock_no_resolution(monkeypatch)

    async def fake_fetch_social_via_jina(url, timeout_seconds, max_chars, settings=None):
        return None  # Jina timed out / failed to render

    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_fetch_social_via_jina
    )

    note = await process_url(Settings(), GOOGLE_MAPS_SHARE_URL)

    assert note.platform == "google-maps"
    assert note.extraction_status == "blocked"


@pytest.mark.anyio
async def test_process_url_google_maps_resolution_survives_jina_failure(monkeypatch):
    # 2026-09-21 fix: even when Jina Reader fails entirely, a successful
    # redirect resolve (name + coordinates, no rendering needed) should
    # still produce a usable place with a precise, coordinates-based
    # google_maps_url — not the fully-empty "please paste manually" stub.
    from personalkm.capture.link_processor import GoogleMapsResolution

    async def fake_resolve(url, timeout_seconds):
        return GoogleMapsResolution(
            name="鏡湖", lat=25.174659, lng=121.655503,
            maps_url="https://www.google.com/maps/search/?api=1&query=25.174659,121.655503",
        )

    async def fake_fetch_social_via_jina(url, timeout_seconds, max_chars, settings=None):
        return None  # Jina still fails — resolution alone must carry the capture

    monkeypatch.setattr(
        "personalkm.capture.link_processor.resolve_google_maps_short_link", fake_resolve
    )
    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_fetch_social_via_jina
    )

    note = await process_url(Settings(), GOOGLE_MAPS_SHARE_URL)

    assert note.platform == "google-maps"
    assert note.extraction_status != "blocked"
    assert len(note.places) == 1
    place = note.places[0]
    assert place["name"] == "鏡湖"
    assert place["google_maps_url"] == "https://www.google.com/maps/search/?api=1&query=25.174659,121.655503"
