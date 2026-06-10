from __future__ import annotations

import json
import os
from urllib import request
from urllib.error import URLError


DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")


def deterministic_summary(title: str, text: str, max_chars: int = 220) -> str:
    clipped = " ".join(text.split())[:max_chars].rstrip()
    if not clipped:
        return f"此內容標題為「{title}」，目前沒有足夠文字可摘要。"
    return f"此內容標題為「{title}」。重點內容：{clipped}"


def summarize_with_ollama(title: str, text: str, model: str = DEFAULT_OLLAMA_MODEL) -> str:
    prompt = (
        "請用繁體中文為以下內容產生 2 句摘要。"
        "不要編造內容，只根據原文。\n\n"
        f"標題：{title}\n\n內容：{text[:6000]}"
    )
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")
    req = request.Request(
        f"{DEFAULT_OLLAMA_URL.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return deterministic_summary(title, text)

    summary = str(data.get("response") or "").strip()
    return summary or deterministic_summary(title, text)
