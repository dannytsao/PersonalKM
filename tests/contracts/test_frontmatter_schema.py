"""CONTRACT: wiki/raw note frontmatter schema.

Any agent changing the schema must update this file in the same commit
(AGENTS.md rule 4). All other code must conform to it.
"""
import re
from pathlib import Path

import yaml

FIXTURES = Path(__file__).parents[1] / "fixtures"

RAW_REQUIRED = {"created", "source", "fetch_status"}
RAW_OPTIONAL = {"url", "source_type", "retry_count", "fetched_at"}

WIKI_REQUIRED = {"created", "source", "summary", "tags"}
WIKI_OPTIONAL = {"topic", "contested", "stub", "entities", "confidence"}

VALID_FETCH_STATUS = {
    "pending", "fetched", "auth_required", "dead", "failed", "failed_final",
}


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{path.name}: missing frontmatter block"
    data = yaml.safe_load(m.group(1))
    assert isinstance(data, dict), f"{path.name}: frontmatter is not a mapping"
    return data


def test_raw_fixtures_conform():
    for p in sorted((FIXTURES / "raw").glob("*.md")):
        fm = _frontmatter(p)
        missing = RAW_REQUIRED - fm.keys()
        assert not missing, f"{p.name}: missing required fields {missing}"
        unknown = fm.keys() - RAW_REQUIRED - RAW_OPTIONAL
        assert not unknown, f"{p.name}: unknown fields {unknown} (update contract?)"
        assert fm["fetch_status"] in VALID_FETCH_STATUS, (
            f"{p.name}: invalid fetch_status {fm['fetch_status']!r}"
        )


def test_wiki_fixtures_conform():
    for p in sorted((FIXTURES / "wiki").glob("*.md")):
        fm = _frontmatter(p)
        missing = WIKI_REQUIRED - fm.keys()
        assert not missing, f"{p.name}: missing required fields {missing}"
        unknown = fm.keys() - WIKI_REQUIRED - WIKI_OPTIONAL
        assert not unknown, f"{p.name}: unknown fields {unknown} (update contract?)"
        assert isinstance(fm["tags"], list), f"{p.name}: tags must be a list"
