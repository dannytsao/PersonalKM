"""Local Ollama provider (Mac Mini). Zero token cost; used as fallback/cheap tier."""
from __future__ import annotations

import json
import urllib.request

from .base import Completion, Provider


class OllamaProvider(Provider):
    def __init__(self, name: str, *, base_url: str = "http://localhost:11434"):
        self.name = name
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Strip thinking tags from model output (e.g. qwen2.5 with thinking capability)."""
        import re
        stripped = re.sub(r"^\s*thinking\s*.*?(?:\n|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
        stripped = stripped.strip()
        return stripped or text

    def complete(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        max_output_tokens: int = 1000,
        timeout_s: int = 120,
    ) -> Completion:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_output_tokens},
        }
        if system:
            payload["system"] = system
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read())
        raw_text = data.get("response", "")
        return Completion(
            text=self._strip_thinking(raw_text),
            model=f"{self.name}/{model}",
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
        )
