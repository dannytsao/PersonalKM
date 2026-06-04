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

    monkeypatch.setattr("bot.link_processor.fetch_page", fake_fetch_page)

    note = await process_url(Settings(), "https://openai.com/")

    assert note.title == "openai.com"
    assert note.url == "https://openai.com/"
    assert "HTTP 403" in note.summary
    assert note.category == "tech"
