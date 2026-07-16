"""Stage-based model router with budget-aware fallback.

Usage (the ONLY way pipeline code talks to LLMs):

    from personalkm.llm.router import route

    result = route("ingest_synthesis", prompt, system="...")
    data   = route("entity_extraction", prompt, expect_json=True)

Resolution order for a stage:
    primary -> fallback[0] -> fallback[1] -> ... -> LLMError

A model is skipped when its provider is over its daily token budget
(config/models.yaml `budgets`), and abandoned after `max_retries` failures.
Every successful call is recorded to usage accounting.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

import yaml

from . import usage
from . import alerts
from .base import Completion, LLMError, Provider, parse_json_strict

log = logging.getLogger(__name__)

CONFIG_PATH = Path(
    os.environ.get(
        "PERSONALKM_MODELS_YAML",
        Path(__file__).resolve().parents[3] / "config" / "models.yaml",
    )
)


@lru_cache(maxsize=1)
def _config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


@lru_cache(maxsize=None)
def _provider(name: str) -> Provider:
    cfg = _config()["providers"][name]
    kind = cfg["kind"]
    if kind == "anthropic":
        from .claude import ClaudeProvider
        return ClaudeProvider(name, api_key_env=cfg["api_key_env"])
    if kind == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(name, base_url=cfg.get("base_url", "http://localhost:11434"))
    if kind == "openai_compat":
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(
            name, api_key_env=cfg["api_key_env"], base_url=cfg.get("base_url")
        )
    if kind == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(name, api_key_env=cfg["api_key_env"])
    raise ValueError(f"Unknown provider kind: {kind}")


def _candidates(stage: str) -> list[str]:
    s = _config()["stages"][stage]
    return [s["primary"], *s.get("fallback", [])]


def route(
    stage: str,
    prompt: str,
    *,
    system: str | None = None,
    expect_json: bool = False,
):
    """Run `prompt` through the model chain configured for `stage`.

    Returns Completion, or parsed dict/list when expect_json=True.
    Raises LLMError when every candidate is exhausted — callers must let
    it propagate (AGENTS.md rule 3: no silent fallbacks).
    """
    cfg = _config()
    stage_cfg = cfg["stages"][stage]
    defaults = cfg.get("defaults", {})
    max_retries = int(defaults.get("max_retries", 2))
    timeout_s = int(defaults.get("timeout_s", 120))
    max_out = int(stage_cfg.get("max_output_tokens", 1000))
    budgets = cfg.get("budgets", {})

    errors: list[str] = []
    for candidate in _candidates(stage):
        provider_name, model = candidate.split("/", 1)
        budget = budgets.get(provider_name, {}).get("daily_tokens", "unlimited")
        if usage.is_over_budget(provider_name, budget):
            log.warning("[%s] %s over daily budget, skipping", stage, provider_name)
            errors.append(f"{candidate}: over budget")
            continue

        provider = _provider(provider_name)
        for attempt in range(1, max_retries + 1):
            try:
                comp: Completion = provider.complete(
                    model, prompt, system=system,
                    max_output_tokens=max_out, timeout_s=timeout_s,
                )
                usage.record(provider_name, comp.input_tokens, comp.output_tokens)
                if expect_json or stage_cfg.get("json_only"):
                    return parse_json_strict(comp.text)
                return comp
            except LLMError as e:  # unparseable JSON — retry same model once
                log.warning("[%s] %s attempt %d: %s", stage, candidate, attempt, e)
                errors.append(f"{candidate}#{attempt}: {e}")
            except Exception as e:  # transport/provider failure
                log.warning("[%s] %s attempt %d failed: %s", stage, candidate, attempt, e)
                errors.append(f"{candidate}#{attempt}: {e}")

    error = LLMError(f"All models exhausted for stage '{stage}': {errors}")
    alerts.notify_llm_error(stage, error)
    raise error
