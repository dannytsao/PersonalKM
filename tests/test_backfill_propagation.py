from pathlib import Path

from scripts.backfill_propagation import excerpt_body, plan_backfill
from personalkm.ingest.ingestion_v2 import _propagate_to_entity_pages


def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    (wiki / "entities").mkdir(parents=True)
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "entities" / "docker.md").write_text(
        "---\ntitle: Docker\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\n"
        "## Summary\n\nContainer runtime.\n",
        encoding="utf-8",
    )
    (wiki / "concepts" / "some-guide.md").write_text(
        "---\ntitle: Some Guide\ncreated: 2026-07-01\nupdated: 2026-07-01\n---\n\n"
        "## Summary\n\nA guide that uses Docker and Kubernetes heavily.\n",
        encoding="utf-8",
    )
    return wiki


def test_excerpt_body_drops_heading_lines():
    body = "## Summary\n\nReal text.\n\n### Sub\n\nMore.\n"
    result = excerpt_body(body)
    assert "## Summary" not in result
    assert "Real text." in result
    assert "More." in result


def test_plan_finds_cross_page_mentions_and_skips_self(tmp_path: Path):
    wiki = _make_wiki(tmp_path)
    plan = plan_backfill(wiki)

    sources = {p.stem: targets for p, targets, _ in plan}
    assert "docker" in sources.get("some-guide", [])
    # docker.md's own body doesn't mention some-guide; and a page must
    # never propagate to itself.
    assert "docker" not in sources.get("docker", ["docker"]) or "docker" not in sources


def test_backfill_is_additive_and_idempotent(tmp_path: Path):
    wiki = _make_wiki(tmp_path)
    plan = plan_backfill(wiki)
    source, targets, clean_body = next(
        (p, t, b) for p, t, b in plan if p.stem == "some-guide"
    )

    first = _propagate_to_entity_pages(wiki, source, targets, raw_path=None, body=clean_body)
    assert first >= 1
    docker_content = (wiki / "entities" / "docker.md").read_text(encoding="utf-8")
    assert "### some-guide (" in docker_content
    assert "## Summary" in docker_content  # original content intact
    assert "title: Docker" in docker_content

    # Second run must be a no-op (idempotency).
    second = _propagate_to_entity_pages(wiki, source, targets, raw_path=None, body=clean_body)
    assert second == 0
    assert docker_content == (wiki / "entities" / "docker.md").read_text(encoding="utf-8")
