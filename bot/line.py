import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Optional

import httpx


URL_PATTERN = re.compile(r"https?://[^\s<>()\"'，。！？、；：「」『』]+", re.IGNORECASE)


@dataclass(frozen=True)
class LineTextEvent:
    text: str
    mark_as_read_token: str = ""


def verify_line_signature(body: bytes, channel_secret: str, signature: Optional[str]) -> bool:
    if not channel_secret or not signature:
        return False

    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def extract_urls(text: str) -> list[str]:
    urls = []
    for match in URL_PATTERN.findall(text):
        cleaned = match.rstrip(".,;:!?)]}」』，。！？")
        if cleaned not in urls:
            urls.append(cleaned)
    return urls


def text_messages_from_webhook(payload: dict) -> list[str]:
    return [event.text for event in text_message_events_from_webhook(payload)]


def text_message_events_from_webhook(payload: dict) -> list[LineTextEvent]:
    messages: list[LineTextEvent] = []
    for event in payload.get("events", []):
        message = event.get("message", {})
        if event.get("type") == "message" and message.get("type") == "text":
            messages.append(
                LineTextEvent(
                    text=message.get("text", ""),
                    mark_as_read_token=message.get("markAsReadToken", ""),
                )
            )
    return messages


async def mark_message_as_read(channel_access_token: str, mark_as_read_token: str) -> bool:
    if not channel_access_token or not mark_as_read_token:
        return False

    headers = {
        "Authorization": f"Bearer {channel_access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.line.me/v2/bot/chat/markAsRead",
            headers=headers,
            json={"markAsReadToken": mark_as_read_token},
        )
        response.raise_for_status()
    return True
