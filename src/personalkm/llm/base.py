"""Provider-agnostic LLM interface.

Pipeline code must ONLY depend on this module and `router`.
Provider SDKs (anthropic, ollama HTTP, gemini, ...) live in sibling modules
that implement `Provider`. Rule 2 in AGENTS.md.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(RuntimeError):
    """Raised when a stage cannot get a valid completion from any model.

    Callers must NOT catch this and silently continue (skip_llm is a bug).
    Let it propagate; the runner reports it and the raw note stays pending.
    """


@dataclass
class Completion:
    text: str
    model: str            # e.g. "claude/claude-sonnet-4-6"
    input_tokens: int
    output_tokens: int


class Provider(ABC):
    """One concrete backend (Anthropic API, local Ollama, ...)."""

    name: str  # provider key from models.yaml, e.g. "claude"

    @abstractmethod
    def complete(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        max_output_tokens: int = 1000,
        timeout_s: int = 120,
    ) -> Completion:
        """Return a completion or raise (any exception => router falls back)."""


def parse_json_strict(text: str) -> dict | list:
    """Parse JSON out of an LLM reply. Tolerates ```json fences and stray
    prose before/after ONE top-level object/array. Raises LLMError otherwise.
    """
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # last resort: grab the outermost {...} or [...]
    m = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    raise LLMError(f"Model returned unparseable JSON: {text[:200]!r}")
