import httpx
import pytest

from bot.line import extract_urls, mark_message_as_read, text_message_events_from_webhook, text_messages_from_webhook


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
