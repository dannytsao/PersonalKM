"""OpenAI-compatible provider — covers MiniMax and OpenAI.

The only file (besides existing bot/llm_clients.py, which this replaces
in Step 3 of MIGRATION.md) allowed to import the `openai` SDK.
"""
from __future__ import annotations

import os

from .base import Completion, Provider


class OpenAICompatProvider(Provider):
    def __init__(self, name: str, *, api_key_env: str, base_url: str | None = None):
        self.name = name
        self._api_key_env = api_key_env
        self._base_url = base_url        # None => api.openai.com
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy import
            key = os.environ.get(self._api_key_env)
            if not key:
                raise RuntimeError(f"{self._api_key_env} not set")
            kwargs = {"api_key": key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = OpenAI(**kwargs)
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
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_output_tokens,
            timeout=timeout_s,
        )
        usage = resp.usage
        return Completion(
            text=resp.choices[0].message.content or "",
            model=f"{self.name}/{model}",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
