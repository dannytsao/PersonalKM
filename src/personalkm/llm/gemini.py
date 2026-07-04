"""Gemini provider. Wire in when you enable gemini in models.yaml."""
from __future__ import annotations

import os

from .base import Completion, Provider


class GeminiProvider(Provider):
    def __init__(self, name: str, *, api_key_env: str = "GEMINI_API_KEY"):
        self.name = name
        self._api_key_env = api_key_env

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        max_output_tokens: int = 1000,
        timeout_s: int = 120,
    ) -> Completion:
        from google import genai  # lazy import; only file allowed to import it

        key = os.environ.get(self._api_key_env)
        if not key:
            raise RuntimeError(f"{self._api_key_env} not set")
        client = genai.Client(api_key=key)
        contents = prompt if not system else f"{system}\n\n---\n\n{prompt}"
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config={"max_output_tokens": max_output_tokens},
        )
        um = getattr(resp, "usage_metadata", None)
        return Completion(
            text=resp.text or "",
            model=f"{self.name}/{model}",
            input_tokens=getattr(um, "prompt_token_count", 0) or 0,
            output_tokens=getattr(um, "candidates_token_count", 0) or 0,
        )
