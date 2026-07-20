import personalkm.ingest.ingestion_v2 as iv2
from personalkm.ingest.ingestion_v2 import _synthesize_wiki_note


def test_synthesize_wiki_note_defaults_to_ingest_synthesis_stage(monkeypatch):
    seen_stages = []

    def fake_route(stage, prompt, *, system=None, expect_json=False):
        seen_stages.append(stage)
        return {"summary": "s", "tags": [], "topic": "t", "confidence": "medium"}

    monkeypatch.setattr(iv2, "route", fake_route)

    _synthesize_wiki_note("some body", page_type="entity", source_path="raw/x.md")

    assert seen_stages == ["entity_extraction", "ingest_synthesis"]


def test_synthesize_wiki_note_accepts_custom_synthesis_stage(monkeypatch):
    # scripts/compare_ingest_synthesis.py relies on this to A/B test a
    # candidate stage (e.g. "ingest_synthesis_trial") against the live one
    # without changing config/models.yaml or ingest_file_v2's call site.
    seen_stages = []

    def fake_route(stage, prompt, *, system=None, expect_json=False):
        seen_stages.append(stage)
        return {"summary": "s", "tags": [], "topic": "t", "confidence": "medium"}

    monkeypatch.setattr(iv2, "route", fake_route)

    _synthesize_wiki_note(
        "some body", page_type="concept", source_path="raw/x.md",
        synthesis_stage="ingest_synthesis_trial",
    )

    assert seen_stages == ["entity_extraction", "ingest_synthesis_trial"]
