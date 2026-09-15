"""Audio transcription (speech-to-text) for AskDanny voice queries.

Separate from router.py's route() because transcription is a different API
shape — a multipart audio file upload to an OpenAI-compatible
/audio/transcriptions endpoint, not a JSON chat-completion prompt. Still
config-driven from config/models.yaml's `transcription:` section
(provider/model strings, primary + fallback, same convention as a `stages:`
entry), and provider names stay confined to this file + models.yaml
(AGENTS.md rule 2).

Usage:
    from personalkm.llm.transcribe import transcribe
    text = await transcribe(audio_bytes, filename="voice.m4a")

Raises LLMError if every configured candidate fails — callers decide how to
degrade (AskDanny replies with a friendly "couldn't understand that"
message rather than crashing; this is a live chat bot, not the ingest
pipeline, so graceful degradation here is correct, unlike AGENTS.md rule 3's
"no silent fallback" for skip_llm on note synthesis).
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

import httpx
import yaml
from opencc import OpenCC

from .base import LLMError

log = logging.getLogger(__name__)

# Whisper-family models transcribe Chinese speech into Simplified script by
# default (confirmed empirically 2026-09-15 — synthetic Traditional-Chinese
# test audio speaking "咖啡廳" came back transcribed as "咖啡厅"), while
# every registry lookup in personalkm.query.line_bot (SUBJECT_ALIASES,
# entry.city, district regexes) is Traditional-only — an unconverted
# transcript silently fails to match and degrades to the much weaker LLM
# fallback path. `s2t` handles the general case; OpenCC's own dictionaries
# additionally "correct" 台→臺 (a separate, real ambiguity — 台 is valid in
# both scripts and is what this project's registry always uses for city
# names, e.g. "台北市", never "臺北市"), which would break exactly the most
# common city queries if left uncorrected — so that one substitution is
# reverted back afterward.
_S2T = OpenCC("s2t")


def _normalize_transcript_script(text: str) -> str:
    return _S2T.convert(text).replace("臺", "台")

CONFIG_PATH = Path(
    os.environ.get(
        "PERSONALKM_MODELS_YAML",
        Path(__file__).resolve().parents[3] / "config" / "models.yaml",
    )
)


@lru_cache(maxsize=1)
def _config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def _candidates() -> list[str]:
    cfg = _config().get("transcription") or {}
    primary = cfg.get("primary")
    if not primary:
        return []
    return [primary, *cfg.get("fallback", [])]


async def transcribe(audio_bytes: bytes, *, filename: str = "audio.m4a", timeout_s: float = 30.0) -> str:
    cfg = _config()
    providers_cfg = cfg.get("providers", {})
    errors: list[str] = []

    for candidate in _candidates():
        provider_name, model = candidate.split("/", 1)
        provider_cfg = providers_cfg.get(provider_name)
        if not provider_cfg:
            errors.append(f"{candidate}: unknown provider '{provider_name}'")
            continue

        api_key_env = provider_cfg.get("api_key_env", "")
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            errors.append(f"{candidate}: {api_key_env or 'api_key_env'} not set")
            continue

        base_url = provider_cfg["base_url"].rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                response = await client.post(
                    f"{base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={"model": model},
                    files={"file": (filename, audio_bytes)},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            log.warning("Transcription via %s failed: %s", candidate, exc)
            errors.append(f"{candidate}: {exc}")
            continue

        text = data.get("text") if isinstance(data, dict) else None
        if isinstance(text, str) and text.strip():
            return _normalize_transcript_script(text.strip())
        errors.append(f"{candidate}: empty or invalid transcription response")

    error = LLMError(f"All transcription candidates exhausted: {errors}")
    log.warning(str(error))
    raise error
