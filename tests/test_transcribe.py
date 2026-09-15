import textwrap

import anyio
import httpx
import pytest

from personalkm.llm import transcribe as transcribe_mod
from personalkm.llm.base import LLMError


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    cfg = textwrap.dedent("""\
        providers:
          groq:
            kind: openai_compat
            base_url: https://api.groq.com/openai/v1
            api_key_env: GROQ_API_KEY
          backup:
            kind: openai_compat
            base_url: https://backup.example.test/v1
            api_key_env: BACKUP_API_KEY
        transcription:
          primary: groq/whisper-large-v3-turbo
          fallback: [backup/whisper-1]
    """)
    p = tmp_path / "models.yaml"
    p.write_text(cfg)
    monkeypatch.setattr(transcribe_mod, "CONFIG_PATH", p)
    transcribe_mod._config.cache_clear()
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("BACKUP_API_KEY", raising=False)
    return p


def test_transcribe_posts_multipart_audio_to_configured_provider(fake_env, monkeypatch) -> None:
    requests = []

    async def fake_post(self, url, headers, data, files):
        requests.append({"url": url, "headers": headers, "data": data, "files": files})
        return httpx.Response(200, json={"text": "北投有什麼早午餐"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    text = anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")

    assert text == "北投有什麼早午餐"
    assert requests[0]["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert requests[0]["headers"]["Authorization"] == "Bearer test-groq-key"
    assert requests[0]["data"] == {"model": "whisper-large-v3-turbo"}
    assert requests[0]["files"] == {"file": ("audio.m4a", b"fake-audio-bytes")}


def test_transcribe_falls_back_when_primary_request_fails(fake_env, monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_API_KEY", "test-backup-key")
    calls = []

    async def fake_post(self, url, headers, data, files):
        calls.append(url)
        if "groq" in url:
            request = httpx.Request("POST", url)
            return httpx.Response(500, text="server error", request=request)
        return httpx.Response(200, json={"text": "fallback transcript"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    text = anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")

    assert text == "fallback transcript"
    assert len(calls) == 2


def test_transcribe_skips_candidate_with_missing_api_key(fake_env, monkeypatch) -> None:
    # BACKUP_API_KEY deliberately left unset by fake_env — both candidates
    # should be considered but neither actually called over the network.
    async def unexpected_post(self, *_args, **_kwargs):
        raise AssertionError("should not be called when no candidate has a key")

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(httpx.AsyncClient, "post", unexpected_post)

    with pytest.raises(LLMError, match="not set"):
        anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")


def test_transcribe_raises_llm_error_when_all_candidates_exhausted(fake_env, monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_API_KEY", "test-backup-key")

    async def always_fails(self, url, headers, data, files):
        return httpx.Response(500, text="boom", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", always_fails)

    with pytest.raises(LLMError):
        anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")


def test_transcribe_raises_on_empty_transcription_text(fake_env, monkeypatch) -> None:
    async def fake_post(self, url, headers, data, files):
        return httpx.Response(200, json={"text": ""}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LLMError):
        anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")


def test_transcribe_converts_simplified_chinese_to_traditional(fake_env, monkeypatch) -> None:
    # Whisper-family models default to Simplified for Chinese speech, but
    # the registry's subject aliases / city names are Traditional-only —
    # an unconverted transcript would silently fail to match.
    async def fake_post(self, url, headers, data, files):
        return httpx.Response(200, json={"text": "附近有什么咖啡厅"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    text = anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")

    assert text == "附近有什麼咖啡廳"


def test_transcribe_keeps_registry_convention_for_tai_character(fake_env, monkeypatch) -> None:
    # OpenCC's own S2T dictionary also "corrects" 台->臺, but this project's
    # registry always writes city names with 台 (e.g. "台北市", never
    # "臺北市") — that one substitution must be reverted, or Taipei/Taichung/
    # Tainan/Taitung queries would silently stop matching after conversion.
    async def fake_post(self, url, headers, data, files):
        return httpx.Response(200, json={"text": "台北市附近有什么美食"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    text = anyio.run(transcribe_mod.transcribe, b"fake-audio-bytes")

    assert text == "台北市附近有什麼美食"
    assert "臺" not in text
