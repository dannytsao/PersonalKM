import httpx
import pytest

from bot.config import Settings
from bot.link_processor import process_url


@pytest.mark.anyio
async def test_process_url_writes_note_when_fetch_is_forbidden(monkeypatch):
    async def fake_fetch_page(url, timeout_seconds, max_chars):
        request = httpx.Request("GET", url)
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError("Forbidden", request=request, response=response)

    monkeypatch.setattr("personalkm.capture.link_processor.fetch_page", fake_fetch_page)

    note = await process_url(Settings(), "https://openai.com/")

    assert note.title == "openai.com"
    assert note.url == "https://openai.com/"
    assert "HTTP 403" in note.summary
    assert note.category == "tech"


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


@pytest.mark.anyio
async def test_process_url_google_maps_uses_the_longer_timeout(monkeypatch):
    # 2026-09-21 regression: a real capture (log 202609201706_00001, sent
    # after the maps.app.goo.gl fix had already landed) still fell through
    # to the "couldn't extract" stub — Jina Reader has to fully render a
    # Google Maps page's client-side JS, which is meaningfully heavier than
    # a static IG/Threads fetch, so the general-purpose
    # request_timeout_seconds (12s) plausibly wasn't enough. Google Maps
    # now gets its own, longer budget (google_maps_timeout_seconds).
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
    async def fake_fetch_social_via_jina(url, timeout_seconds, max_chars, settings=None):
        return None  # Jina timed out / failed to render

    monkeypatch.setattr(
        "personalkm.capture.link_processor.fetch_social_via_jina", fake_fetch_social_via_jina
    )

    note = await process_url(Settings(), GOOGLE_MAPS_SHARE_URL)

    assert note.platform == "google-maps"
    assert note.extraction_status == "blocked"
