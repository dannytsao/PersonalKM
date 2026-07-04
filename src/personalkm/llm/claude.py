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
        max_output_tokens: int = 1000,
        timeout_s: int = 120,
    ) -> Completion:
        client = self._get_client()
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
