from pathlib import Path

from personalkm.propagate.entity_dedup import (
    CANONICAL_ENTITIES,
    DEFAULT_CANONICAL_ENTITIES,
    EntityRegistry,
    canonical_slug_from_name,
    load_canonical_registry,
)
from scripts.build_entities_registry import collect_candidates


def _restore_defaults():
    CANONICAL_ENTITIES.clear()
    CANONICAL_ENTITIES.update(DEFAULT_CANONICAL_ENTITIES)


def test_missing_file_falls_back_to_defaults(tmp_path: Path):
    try:
        source = load_canonical_registry(tmp_path)
        assert source == "defaults"
        assert CANONICAL_ENTITIES == DEFAULT_CANONICAL_ENTITIES
    finally:
        _restore_defaults()


def test_file_becomes_the_whole_whitelist(tmp_path: Path):
    reg = tmp_path / "_registry"
    reg.mkdir()
    (reg / "entities.yaml").write_text(
        "canonical:\n  my-new-entity: My New Entity\n  claude-code: Claude Code\n",
        encoding="utf-8",
    )
    try:
        source = load_canonical_registry(tmp_path)
        assert source == "file"
        assert CANONICAL_ENTITIES == {
            "my-new-entity": "My New Entity",
            "claude-code": "Claude Code",
        }
        # Promotion: matching now works for the file-added entity...
        assert canonical_slug_from_name("all about My New Entity today") == "my-new-entity"
        # ...and demotion: entities absent from the file stop matching.
        assert canonical_slug_from_name("Kimi K3 news") is None
    finally:
        _restore_defaults()


def test_unparseable_file_falls_back_to_defaults(tmp_path: Path):
    reg = tmp_path / "_registry"
    reg.mkdir()
    (reg / "entities.yaml").write_text("canonical: [not, a, mapping\n", encoding="utf-8")
    try:
        assert load_canonical_registry(tmp_path) == "defaults"
        assert CANONICAL_ENTITIES == DEFAULT_CANONICAL_ENTITIES
    finally:
        _restore_defaults()


def test_entity_registry_loads_file_on_construction(tmp_path: Path):
    (tmp_path / "entities").mkdir()
    (tmp_path / "concepts").mkdir()
    reg = tmp_path / "_registry"
    reg.mkdir()
    (reg / "entities.yaml").write_text(
        "canonical:\n  graphify: Graphify\n", encoding="utf-8"
    )
    try:
        EntityRegistry(tmp_path)
        assert CANONICAL_ENTITIES == {"graphify": "Graphify"}
    finally:
        _restore_defaults()


def test_collect_candidates_scores_captures_and_incoming_links(tmp_path: Path):
    wiki = tmp_path
    (wiki / "entities").mkdir()
    (wiki / "concepts").mkdir()
    # A date-prefixed page with 2 capture sections
    (wiki / "entities" / "2026-07-10-hot-topic.md").write_text(
        "---\ntitle: Hot Topic\n---\n\n## Captures\n\n"
        "### a (2026-07-10)\n\nx\n\n### b (2026-07-11)\n\ny\n",
        encoding="utf-8",
    )
    # Another page linking to it (1 incoming link)
    (wiki / "entities" / "other.md").write_text(
        "---\ntitle: Other\n---\n\nSee [[2026-07-10-hot-topic]].\n",
        encoding="utf-8",
    )
    # A quiet date-prefixed page (no signals)
    (wiki / "entities" / "2026-07-11-quiet.md").write_text(
        "---\ntitle: Quiet\n---\n\nNothing links here.\n", encoding="utf-8"
    )

    candidates = collect_candidates(wiki, canonical={}, min_signals=2)
    assert "2026-07-10-hot-topic" in candidates
    assert candidates["2026-07-10-hot-topic"]["captures"] == 2
    assert candidates["2026-07-10-hot-topic"]["incoming_links"] == 1
    assert "2026-07-11-quiet" not in candidates
