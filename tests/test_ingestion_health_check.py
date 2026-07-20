from pathlib import Path

from personalkm.ingest.ingestion_health_check import IngestionHealthCheck
from personalkm.propagate.knowledge_graph import build_knowledge_graph


def _make_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    (wiki / "entities").mkdir(parents=True)
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "entities" / "claude-code.md").write_text(
        "---\ntitle: Claude Code\ncanonical: true\n---\n\nBody with [[docker]] link.\n",
        encoding="utf-8",
    )
    (wiki / "concepts" / "docker.md").write_text(
        "---\ntitle: Docker\n---\n\nBody.\n", encoding="utf-8",
    )
    return wiki


def test_check_knowledge_graph_accepts_real_generator_output(tmp_path: Path):
    # Regression: this check used to require emoji-decorated headers
    # ("# 📊 Knowledge Graph" / "## 🔗 Entities" / "## 💡 Concepts") that
    # build_knowledge_graph() has never produced, so it failed on every
    # single real Phase A run without anyone investigating why.
    wiki = _make_wiki(tmp_path)
    content = build_knowledge_graph(wiki)
    (wiki / "knowledge-graph.md").write_text(content, encoding="utf-8")

    hc = IngestionHealthCheck(tmp_path)
    assert hc.check_knowledge_graph() is True
    assert "knowledge-graph.md valid ✅" in hc.checks_passed
    assert hc.checks_failed == []


def test_check_knowledge_graph_still_fails_on_genuinely_broken_content(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "knowledge-graph.md").write_text("not a real knowledge graph file\n", encoding="utf-8")

    hc = IngestionHealthCheck(tmp_path)
    assert hc.check_knowledge_graph() is False
    assert "knowledge-graph.md structure invalid ❌" in hc.checks_failed


def test_check_knowledge_graph_is_optional_when_missing(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir(parents=True)

    hc = IngestionHealthCheck(tmp_path)
    assert hc.check_knowledge_graph() is True
    assert any("MISSING" in w for w in hc.warnings)
