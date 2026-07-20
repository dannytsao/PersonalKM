from datetime import date
from pathlib import Path

import personalkm.propagate.distill as distill_mod
from personalkm.propagate.distill import (
    attach_source_links,
    build_distillation_prompt,
    check_trigger,
    count_captures,
    extract_capture_sources,
    preview_distillation,
    scan_for_candidates,
)


def test_count_captures_matches_both_heading_shapes():
    body = """
## First Capture (2026-07-01)

body

### Second Capture (2026-07-05)

body
"""
    assert count_captures(body) == 2


def test_check_trigger_fires_on_captures_threshold():
    body = "\n".join(f"### Capture {i} (2026-07-0{i})" for i in range(1, 6))
    fm = {"created": "2026-07-15"}
    result = check_trigger(fm, body, today=date(2026, 7, 19))
    assert result.should_trigger
    assert "captures_count" in result.reason


def test_check_trigger_fires_on_age():
    fm = {"created": "2026-06-01"}
    result = check_trigger(fm, "one capture only", today=date(2026, 7, 19))
    assert result.should_trigger
    assert "age_days" in result.reason


def test_check_trigger_uses_last_distilled_over_created():
    fm = {"created": "2026-01-01", "last_distilled": "2026-07-10"}
    result = check_trigger(fm, "body", today=date(2026, 7, 19))
    assert not result.should_trigger  # only 9 days since last_distilled


def test_check_trigger_does_not_fire_when_fresh_and_few_captures():
    fm = {"created": "2026-07-15"}
    result = check_trigger(fm, "### One capture (2026-07-15)", today=date(2026, 7, 19))
    assert not result.should_trigger


def test_preview_distillation_handles_title_with_unescaped_colon(tmp_path: Path):
    # Real capture titles routinely look like 'X on Instagram: "caption"' and
    # aren't YAML-quoted when written — yaml.safe_load() chokes on this
    # ("mapping values are not allowed here"), so parsing must not use it.
    page = tmp_path / "colon-title.md"
    page.write_text(
        '---\ntitle: Nash今天吃什麼 on Instagram: "邱吉爾優質香腸 Churchill\'s Sausages"\n'
        "created: 2026-07-18\n---\n\n### Only capture (2026-07-18)\n",
        encoding="utf-8",
    )
    preview = preview_distillation(page, call_llm=False)
    assert preview.title.startswith("Nash今天吃什麼 on Instagram:")
    assert not preview.triggered


def test_preview_distillation_skips_llm_when_not_triggered(tmp_path: Path):
    page = tmp_path / "fresh.md"
    page.write_text(
        "---\ntitle: Fresh Page\ncreated: 2026-07-18\n---\n\n### Only capture (2026-07-18)\n",
        encoding="utf-8",
    )
    preview = preview_distillation(page)
    assert not preview.triggered
    assert preview.proposed_summary is None


def test_preview_distillation_calls_llm_when_triggered(tmp_path: Path, monkeypatch):
    page = tmp_path / "busy.md"
    captures = "\n".join(f"### Capture {i} (2026-07-0{i})" for i in range(1, 6))
    page.write_text(
        f"---\ntitle: Busy Page\ncreated: 2026-06-01\n---\n\n{captures}\n",
        encoding="utf-8",
    )

    def fake_route(stage, prompt, *, system=None, expect_json=False):
        assert stage == "entity_distillation"
        assert "Busy Page" in prompt
        return {"summary": "濃縮後的摘要", "key_facts": ["事實一", "事實二"]}

    monkeypatch.setattr(distill_mod, "route", fake_route)

    preview = preview_distillation(page)
    assert preview.triggered
    assert preview.proposed_summary == "濃縮後的摘要"
    assert preview.proposed_key_facts == ["事實一", "事實二"]
    assert preview.error is None


def test_preview_distillation_attaches_source_links_to_dated_facts(tmp_path: Path, monkeypatch):
    page = tmp_path / "busy.md"
    captures = "\n".join(
        f"### Capture {i} (2026-07-0{i})\n\nbody\n\nSource: [[Archive/raw/Tech/2026-07-0{i}-x]]"
        for i in range(1, 6)
    )
    page.write_text(
        f"---\ntitle: Busy Page\ncreated: 2026-06-01\n---\n\n{captures}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        distill_mod, "route",
        lambda *a, **k: {"summary": "ok", "key_facts": ["重點 (2026-07-03)"]},
    )

    preview = preview_distillation(page)
    assert preview.proposed_key_facts == [
        "重點 (2026-07-03) → [[Archive/raw/Tech/2026-07-03-x]]"
    ]


def test_preview_distillation_records_llm_error_without_raising(tmp_path: Path, monkeypatch):
    page = tmp_path / "busy.md"
    captures = "\n".join(f"### Capture {i} (2026-07-0{i})" for i in range(1, 6))
    page.write_text(
        f"---\ntitle: Busy Page\ncreated: 2026-06-01\n---\n\n{captures}\n",
        encoding="utf-8",
    )

    def failing_route(*args, **kwargs):
        raise RuntimeError("All models exhausted")

    monkeypatch.setattr(distill_mod, "route", failing_route)

    preview = preview_distillation(page)
    assert preview.triggered
    assert preview.error == "All models exhausted"
    assert preview.proposed_summary is None


def test_scan_for_candidates_only_returns_triggered_pages(tmp_path: Path, monkeypatch):
    wiki = tmp_path / "wiki"
    entities = wiki / "entities"
    concepts = wiki / "concepts"
    entities.mkdir(parents=True)
    concepts.mkdir(parents=True)

    captures = "\n".join(f"### Capture {i} (2026-07-0{i})" for i in range(1, 6))
    (entities / "busy.md").write_text(
        f"---\ntitle: Busy\ncreated: 2026-06-01\n---\n\n{captures}\n", encoding="utf-8"
    )
    (concepts / "fresh.md").write_text(
        "---\ntitle: Fresh\ncreated: 2026-07-18\n---\n\n### One capture (2026-07-18)\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        distill_mod, "route",
        lambda *a, **k: {"summary": "ok", "key_facts": []},
    )

    previews = scan_for_candidates(wiki)
    assert len(previews) == 1
    assert previews[0].title == "Busy"


def test_extract_capture_sources_maps_date_to_backlink():
    body = """
### First Capture (2026-07-01)

body text

Source: [[Archive/raw/Tech/2026-07-01-first]]

### Second Capture (2026-07-05)

more body

Source: [[Archive/raw/Tech/2026-07-05-second]]
"""
    sources = extract_capture_sources(body)
    assert sources == {
        "2026-07-01": "[[Archive/raw/Tech/2026-07-01-first]]",
        "2026-07-05": "[[Archive/raw/Tech/2026-07-05-second]]",
    }


def test_extract_capture_sources_skips_captures_without_source_line():
    # Pre-2026-07-19 captures (or a page's first capture) have no inline
    # Source line — must not error, just resolve to no backlink.
    body = "### Old Capture (2026-06-01)\n\nno source line here\n"
    assert extract_capture_sources(body) == {}


def test_attach_source_links_appends_backlink_when_date_resolves():
    body = "### X (2026-07-01)\n\nbody\n\nSource: [[Archive/raw/Tech/2026-07-01-x]]\n"
    facts = ["某個重點 (2026-07-01)"]
    result = attach_source_links(facts, body)
    assert result == ["某個重點 (2026-07-01) → [[Archive/raw/Tech/2026-07-01-x]]"]


def test_attach_source_links_tolerates_fullwidth_parens():
    body = "### X (2026-07-01)\n\nbody\n\nSource: [[Archive/raw/Tech/2026-07-01-x]]\n"
    facts = ["某個重點（2026-07-01）"]
    result = attach_source_links(facts, body)
    assert result == ["某個重點（2026-07-01） → [[Archive/raw/Tech/2026-07-01-x]]"]


def test_attach_source_links_leaves_fact_unchanged_when_no_source_resolves():
    facts = ["沒有日期的重點", "有日期但查不到 (2026-01-01)"]
    result = attach_source_links(facts, body="no capture headings at all")
    assert result == facts


def test_build_distillation_prompt_includes_body_and_title():
    prompt = build_distillation_prompt("Hermes Agent", "some accumulated body text")
    assert "Hermes Agent" in prompt
    assert "some accumulated body text" in prompt
    assert "JSON" in prompt


def test_build_distillation_prompt_requires_dates_on_key_facts():
    # Regression: DeepSeek's first real-vault dry-run dropped every date from
    # key_facts even though it kept numbers/URLs/proper nouns intact — the
    # prompt didn't call out dates on key_facts specifically, only generally.
    prompt = build_distillation_prompt("Claude Code", "body")
    assert "YYYY-MM-DD" in prompt
