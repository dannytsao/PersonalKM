import base64
import hashlib
import hmac
import re
from typing import Optional


URL_PATTERN = re.compile(r"https?://[^\s<>()\"'，。！？、；：「」『』]+", re.IGNORECASE)


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
    messages: list[str] = []
    for event in payload.get("events", []):
        message = event.get("message", {})
        if event.get("type") == "message" and message.get("type") == "text":
            messages.append(message.get("text", ""))
    return messages
