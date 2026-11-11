"""Local Ollama provider (Mac Mini). Zero token cost; used as fallback/cheap tier."""
from __future__ import annotations

import json
import threading
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
        images: list[bytes] | None = None,
        max_output_tokens: int = 1000,
        timeout_s: int = 120,
        json_mode: bool = False,
    ) -> Completion:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            # qwen3.5+ are thinking models: without this they burn the whole
            # num_predict budget on a 🤔 pass and return an empty string
            # (eval_count == num_predict, done_reason == "length").
            "think": False,
            "options": {"num_predict": max_output_tokens},
        }
        if images:
            # Ollama vision: base64-encoded images in the "images" field.
            # Works with llava, qwen2.5-vl, minicpm-v, etc.
            import base64 as _b64
            payload["images"] = [_b64.b64encode(img).decode("ascii") for img in images]
        if json_mode:
            # Structured-output constraint: forces valid JSON (quoted keys AND
            # quoted array elements). qwen3.5:9b free-form output sometimes
            # emits bare tags ([restaurant, taiwan]) which json.loads rejects
            # and retries can't fix (2026-08-26 Phase A failure).
            payload["format"] = "json"
        if system:
            payload["system"] = system
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        # Hard deadline: urllib's timeout only guards individual socket
        # operations, so a stalled/trickling response can hang for hours
        # (observed 45min-3.5h per attempt in 2026-11-11 phase-c-lifestyle
        # while cloud budgets were exhausted). Enforce total request time
        # with a join deadline; a timed-out worker is abandoned as daemon.
        holder: dict = {}

        def _fetch() -> None:
            try:
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    holder["data"] = json.loads(resp.read())
            except Exception as e:  # re-raised in caller thread below
                holder["error"] = e

        worker = threading.Thread(target=_fetch, daemon=True)
        worker.start()
        worker.join(timeout_s)
        if "data" not in holder:
            if "error" in holder:
                raise holder["error"]
            raise TimeoutError(
                f"ollama {model} exceeded {timeout_s}s deadline (request abandoned)"
            )
        data = holder["data"]
        raw_text = data.get("response", "")
        return Completion(
            text=self._strip_thinking(raw_text),
            model=f"{self.name}/{model}",
            input_tokens=int(data.get("prompt_eval_count", 0)),
            output_tokens=int(data.get("eval_count", 0)),
        )
