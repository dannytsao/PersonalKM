from pathlib import Path

from personalkm.ingest.ingestion_v2 import _propagate_to_entity_pages


def test_propagate_to_entity_pages_updates_concepts_dir_too(tmp_path: Path):
    # Previously this only looked at wiki/entities/ and only for the ~34
    # hardcoded CANONICAL_ENTITIES — a capture mentioning a non-canonical
    # concept page left that page stale (1 source -> 1 page instead of N).
    wiki = tmp_path / "wiki"
    entities = wiki / "entities"
    concepts = wiki / "concepts"
    entities.mkdir(parents=True)
    concepts.mkdir(parents=True)

    entity_page = entities / "claude-code.md"
    entity_page.write_text(
        "---\ntitle: Claude Code\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\nBody.\n",
        encoding="utf-8",
    )
    concept_page = concepts / "local-first-automation.md"
    concept_page.write_text(
        "---\ntitle: Local-first automation\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\nBody.\n",
        encoding="utf-8",
    )

    capture_page = wiki / "entities" / "2026-07-19-some-capture.md"
    capture_page.write_text("---\ntitle: Some Capture\n---\n\nBody\n", encoding="utf-8")

    updated = _propagate_to_entity_pages(
        wiki,
        capture_page,
        detected_entities=["claude-code", "local-first-automation"],
        raw_path=None,
        body="This capture discusses Claude Code and local-first automation together.",
    )

    assert updated == 2
    assert "## Captures" in entity_page.read_text(encoding="utf-8")
    assert "## Captures" in concept_page.read_text(encoding="utf-8")


def test_propagate_to_entity_pages_skips_self_reference(tmp_path: Path):
    wiki = tmp_path / "wiki"
    entities = wiki / "entities"
    entities.mkdir(parents=True)
    page = entities / "claude-code.md"
    page.write_text(
        "---\ntitle: Claude Code\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\nBody.\n",
        encoding="utf-8",
    )

    updated = _propagate_to_entity_pages(
        wiki, page, detected_entities=["claude-code"], raw_path=None, body="Some body about itself."
    )

    assert updated == 0
