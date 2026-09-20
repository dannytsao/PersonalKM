"""Anthropic provider. The only file allowed to import `anthropic`."""
from __future__ import annotations

import os

from .base import Completion, Provider


class ClaudeProvider(Provider):
    def __init__(self, name: str, *, api_key_env: str = "ANTHROPIC_API_KEY"):
        self.name = name
        self._api_key_env = api_key_env
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic  # lazy: not needed when running Ollama-only
            key = os.environ.get(self._api_key_env)
            if not key:
                raise RuntimeError(f"{self._api_key_env} not set")
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        images: list[bytes] | None = None,
        max_output_tokens: int = 1000,
        timeout_s: int = 120,
        json_mode: bool = False,
    ) -> Completion:
        client = self._get_client()
        if images:
            # Anthropic vision: content blocks with type "image" + base64.
            import base64 as _b64
            content: list[dict] = [{"type": "text", "text": prompt}]
            for img in images:
                b64 = _b64.b64encode(img).decode("ascii")
                if img[:8] == b"\x89PNG\r\n\x1a\n":
                    mime = "image/png"
                elif img[:3] == b"\xff\xd8\xff":
                    mime = "image/jpeg"
                else:
                    mime = "image/jpeg"
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime,
                        "data": b64,
                    },
                })
            kwargs: dict = dict(
                model=model,
                max_tokens=max_output_tokens,
                messages=[{"role": "user", "content": content}],
                timeout=timeout_s,
            )
        else:
            kwargs: dict = dict(
                model=model,
                max_tokens=max_output_tokens,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout_s,
            )
        if system:
            kwargs["system"] = system
        msg = client.messages.create(**kwargs)
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return Completion(
            text=text,
            model=f"{self.name}/{model}",
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )
