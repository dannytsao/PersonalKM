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
