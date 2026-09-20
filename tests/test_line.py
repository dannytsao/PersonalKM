import httpx
import pytest

from bot.line import (
    download_line_image,
    extract_urls,
    image_message_events_from_webhook,
    mark_message_as_read,
    text_message_events_from_webhook,
    text_messages_from_webhook,
)


def test_extract_urls_deduplicates_and_trims_punctuation():
    text = "看這個 https://example.com/a?x=1，還有 https://example.com/a?x=1。"

    assert extract_urls(text) == ["https://example.com/a?x=1"]


def test_text_message_events_from_webhook_reads_mark_as_read_token():
    payload = {
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "text": "文章 https://example.com",
                    "markAsReadToken": "read-token",
                },
            }
        ]
    }

    events = text_message_events_from_webhook(payload)

    assert text_messages_from_webhook(payload) == ["文章 https://example.com"]
    assert events[0].text == "文章 https://example.com"
    assert events[0].mark_as_read_token == "read-token"


@pytest.mark.anyio
async def test_mark_message_as_read_posts_read_token(monkeypatch):
    requests = []

    async def fake_post(self, url, headers, json):
        requests.append((url, headers, json))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    marked = await mark_message_as_read("channel-token", "read-token")

    assert marked
    assert requests == [
        (
            "https://api.line.me/v2/bot/chat/markAsRead",
            {"Authorization": "Bearer channel-token", "Content-Type": "application/json"},
            {"markAsReadToken": "read-token"},
        )
    ]


def test_extract_urls_removes_tracking_params():
    text = "主文 https://example.com/a?id=1&utm_source=line&fbclid=abc#comments"

    assert extract_urls(text) == ["https://example.com/a?id=1"]


def test_extract_urls_filters_obvious_ad_and_redirect_urls():
    text = (
        "主文 https://example.com/article "
        "廣告 https://googleads.g.doubleclick.net/pagead/ads?client=x "
        "跳轉 https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.com%2Fspam"
    )

    assert extract_urls(text) == ["https://example.com/article"]


def test_extract_urls_keeps_facebook_group_permalink():
    text = "https://www.facebook.com/groups/1782041272068262/permalink/4587135024892192/?rdid=ft64HYMHIlymEZyv#"

    assert extract_urls(text) == [
        "https://www.facebook.com/groups/1782041272068262/permalink/4587135024892192/?rdid=ft64HYMHIlymEZyv"
    ]


# ── Image message support ────────────────────────────────────────────────


def test_image_message_events_from_webhook_extracts_message_id():
    """A LINE image message carries only a messageId — no image bytes."""
    payload = {
        "events": [
            {
                "type": "message",
                "source": {"userId": "U123"},
                "message": {
                    "type": "image",
                    "id": "msg-abc-123",
                    "markAsReadToken": "read-token-img",
                },
            }
        ]
    }

    events = image_message_events_from_webhook(payload)

    assert len(events) == 1
    assert events[0].message_id == "msg-abc-123"
    assert events[0].user_id == "U123"
    assert events[0].mark_as_read_token == "read-token-img"


def test_image_message_events_from_webhook_ignores_text_messages():
    """Text messages must NOT appear in image event extraction."""
    payload = {
        "events": [
            {
                "type": "message",
                "source": {"userId": "U456"},
                "message": {"type": "text", "text": "hello", "id": "txt-1"},
            }
        ]
    }

    assert image_message_events_from_webhook(payload) == []


def test_image_message_events_from_webhook_handles_empty_payload():
    assert image_message_events_from_webhook({}) == []
    assert image_message_events_from_webhook({"events": []}) == []


@pytest.mark.anyio
async def test_download_line_image_calls_content_api(monkeypatch):
    """download_line_image must hit api-data.line.me (NOT api.line.me)."""
    calls = []

    class FakeResponse:
        status_code = 200
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32  # fake PNG header

        def raise_for_status(self):
            pass

    async def fake_get(self, url, headers=None):
        calls.append((url, headers))
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    image_bytes = await download_line_image("test-token", "msg-abc-123")

    assert image_bytes.startswith(b"\x89PNG")
    assert len(calls) == 1
    called_url, called_headers = calls[0]
    assert "api-data.line.me" in called_url
    assert "msg-abc-123" in called_url
    assert called_headers["Authorization"] == "Bearer test-token"


@pytest.mark.anyio
async def test_download_line_image_rejects_empty_args():
    with pytest.raises(ValueError):
        await download_line_image("", "msg-1")
    with pytest.raises(ValueError):
        await download_line_image("token", "")
