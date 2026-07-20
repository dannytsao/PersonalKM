"""CONTRACT: wiki/raw note frontmatter schema.

Any agent changing the schema must update this file in the same commit
(AGENTS.md rule 4). All other code must conform to it.

2026-07-19: rewritten to mirror what the pipeline actually writes, verified
field-by-field against personalkm.capture.notes.render_note() and every wiki
page writer in personalkm.ingest.ingestion_v2 / personalkm.propagate.entity_dedup.
The previous version (created/source/summary/fetch_status/...) described an
aspirational schema no production code path ever wrote — it only passed
because the one fixture it checked was hand-crafted to match the aspiration,
not generated from real output. wiki/stubs/ pages
(personalkm.resolve.runner._create_stub) have their own distinct frontmatter
shape (stub/platform/worker_status/...) and are not covered by this contract
yet — tracked as a separate follow-up, not solved here.
"""
import re
from pathlib import Path

import yaml

FIXTURES = Path(__file__).parents[1] / "fixtures"

# Raw notes (personalkm.capture.notes.render_note) are pure markdown body
# today — no YAML frontmatter. fetch_status/retry_count tracking described in
# SPEC.md was never implemented this way; see IMPROVEMENT-BACKLOG.md P5
# follow-ups / CHECKLIST.md #2 for that still-open gap.

# Fields written by every live wiki-page-creation path (ingestion_v2.py's
# canonical-create and legacy-create branches).
WIKI_REQUIRED = {"title", "created", "updated", "type", "sources", "confidence"}
# topic/tags: written by ingestion_v2.py's creation paths but omitted by
# entity_dedup.py's _write_canonical_page (used by scripts/phase6_backfill.py)
# — not universal, so optional rather than required.
# canonical: only present on canonical entity pages.
# contested/contradictions: structurally supported by
# ingestion_wiki_helpers.build_frontmatter's key_order but nothing populates
# them yet — reserved, not yet in active use.
WIKI_OPTIONAL = {"topic", "tags", "canonical", "contested", "contradictions"}


def _frontmatter(path: Path) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Empty dict if there is no frontmatter block."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}, text
    data = yaml.safe_load(m.group(1))
    assert isinstance(data, dict), f"{path.name}: frontmatter is not a mapping"
    return data, text[m.end():]


def test_raw_fixtures_have_no_frontmatter():
    """render_note() emits a bare '# Title' + body — no YAML block at all."""
    for p in sorted((FIXTURES / "raw").glob("*.md")):
        fm, body = _frontmatter(p)
        assert fm == {}, (
            f"{p.name}: raw notes have no frontmatter today — if this "
            f"fixture now needs one, capture/notes.py must have changed; "
            f"update this contract deliberately, not by accident"
        )
        assert body.lstrip().startswith("# "), f"{p.name}: expected a '# Title' heading"


def test_wiki_fixtures_conform():
    for p in sorted((FIXTURES / "wiki").glob("*.md")):
        fm, _ = _frontmatter(p)
        missing = WIKI_REQUIRED - fm.keys()
        assert not missing, f"{p.name}: missing required fields {missing}"
        unknown = fm.keys() - WIKI_REQUIRED - WIKI_OPTIONAL
        assert not unknown, f"{p.name}: unknown fields {unknown} (update contract?)"
        assert isinstance(fm["sources"], list), f"{p.name}: sources must be a list"
