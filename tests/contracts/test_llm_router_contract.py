"""CONTRACT: LLM router behavior.

Invariants (AGENTS.md rules 2-3):
  1. Unparseable JSON must raise LLMError — never return garbage silently.
  2. When primary fails, the router must try fallbacks in order.
  3. When a provider is over its daily budget, it is skipped.
  4. If every candidate fails, route() raises LLMError (no skip_llm behavior).
"""
import textwrap
from pathlib import Path

import pytest

from personalkm.llm import router as router_mod
from personalkm.llm import usage as usage_mod
from personalkm.llm.base import Completion, LLMError, Provider, parse_json_strict


class FakeProvider(Provider):
    def __init__(self, name, behavior):
        self.name = name
        self.behavior = behavior     # "ok" | "bad_json" | "boom"
        self.calls = 0

    def complete(self, model, prompt, *, system=None,
                 max_output_tokens=1000, timeout_s=120):
        self.calls += 1
        if self.behavior == "boom":
            raise ConnectionError("provider down")
        text = '{"ok": true}' if self.behavior != "bad_json" else "not json at all"
        return Completion(text=text, model=f"{self.name}/{model}",
                          input_tokens=10, output_tokens=5)


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    cfg = textwrap.dedent("""\
        providers:
          a: {kind: fake}
          b: {kind: fake}
        budgets:
          a: {daily_tokens: 1000000}
          b: {daily_tokens: unlimited}
        defaults: {max_retries: 1, timeout_s: 5}
        stages:
          test_stage:
            primary: a/model-x
            fallback: [b/model-y]
            json_only: true
    """)
    p = tmp_path / "models.yaml"
    p.write_text(cfg)
    monkeypatch.setattr(router_mod, "CONFIG_PATH", p)
    router_mod._config.cache_clear()
    router_mod._provider.cache_clear()
    monkeypatch.setattr(usage_mod, "USAGE_FILE", tmp_path / "usage.json")
    monkeypatch.setattr(usage_mod, "RUNTIME_DIR", tmp_path)
    return p


def _patch_providers(monkeypatch, providers: dict):
    monkeypatch.setattr(router_mod, "_provider",
                        lambda name: providers[name])


def test_bad_json_raises_llmerror():
    with pytest.raises(LLMError):
        parse_json_strict("definitely { not json")


def test_fallback_chain_on_failure(fake_env, monkeypatch):
    a, b = FakeProvider("a", "boom"), FakeProvider("b", "ok")
    _patch_providers(monkeypatch, {"a": a, "b": b})
    result = router_mod.route("test_stage", "prompt")
    assert result == {"ok": True}
    assert a.calls >= 1 and b.calls == 1


def test_over_budget_provider_is_skipped(fake_env, monkeypatch):
    a, b = FakeProvider("a", "ok"), FakeProvider("b", "ok")
    _patch_providers(monkeypatch, {"a": a, "b": b})
    usage_mod.record("a", 999_999, 2)   # blow a's daily budget
    result = router_mod.route("test_stage", "prompt")
    assert result == {"ok": True}
    assert a.calls == 0, "over-budget provider must not be called"
    assert b.calls == 1


def test_all_exhausted_raises_never_silent(fake_env, monkeypatch):
    a, b = FakeProvider("a", "boom"), FakeProvider("b", "bad_json")
    _patch_providers(monkeypatch, {"a": a, "b": b})
    with pytest.raises(LLMError):
        router_mod.route("test_stage", "prompt")


def test_all_exhausted_sends_llm_alert(fake_env, monkeypatch):
    alerts = []
    a, b = FakeProvider("a", "boom"), FakeProvider("b", "bad_json")
    _patch_providers(monkeypatch, {"a": a, "b": b})
    monkeypatch.setattr(router_mod.alerts, "notify_llm_error", lambda stage, error: alerts.append((stage, str(error))))

    with pytest.raises(LLMError):
        router_mod.route("test_stage", "prompt")

    assert len(alerts) == 1
    assert alerts[0][0] == "test_stage"
