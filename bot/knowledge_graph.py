"""
Knowledge Graph Generator for PersonalKM
========================================
Generates `wiki/knowledge-graph.md` with a Mermaid flowchart visualization
plus a text node index below.

Usage:
    from bot.knowledge_graph import build_knowledge_graph

    md = build_knowledge_graph(Path('wiki'))
    (Path('wiki') / 'knowledge-graph.md').write_text(md)
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from bot.entity_dedup import CANONICAL_ENTITIES, is_canonical_slug

logger = logging.getLogger(__name__)

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _safe_id(slug: str) -> str:
    safe = slug.replace("-", "_").replace(".", "_")
    if safe and safe[0].isdigit():
        return f"p_{safe}"
    return safe if safe else "node"


def _display_name(slug: str) -> str:
    return CANONICAL_ENTITIES.get(slug, slug)


def _resolve_wikilink_target(raw: str) -> Optional[str]:
    target = raw.split("|")[0].split("#")[0].strip()
    if not target:
        return None
    return target


def _scan_pages(wiki_path: Path):
    entities_dir = wiki_path / "entities"
    concepts_dir = wiki_path / "concepts"

    pages = {}
    entity_duplicates = set()
    if entities_dir.exists():
        for f in sorted(entities_dir.glob("*.md")):
            pages[f.stem] = {"type": "entity", "label": _display_name(f.stem), "path": f}
    if concepts_dir.exists():
        for f in sorted(concepts_dir.glob("*.md")):
            if f.stem in pages:
                entity_duplicates.add(f.stem)
            else:
                pages[f.stem] = {"type": "concept", "label": f.stem, "path": f}
    if entity_duplicates:
        logger.warning("Pages in both entities/ and concepts/: %s", entity_duplicates)
    return pages


def _collect_edges(pages: dict) -> set:
    edges = set()
    page_ids = set(pages.keys())
    for slug, info in pages.items():
        try:
            content = info["path"].read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in WIKILINK_RE.finditer(content):
            target = _resolve_wikilink_target(match.group(1))
            if target and target in page_ids and target != slug:
                edges.add((_safe_id(slug), _safe_id(target)))
    return edges


def _build_mermaid(pages: dict, edges: set) -> str:
    entity_slugs = sorted(s for s, i in pages.items() if i["type"] == "entity")
    concept_slugs = sorted(s for s, i in pages.items() if i["type"] == "concept")

    lines = [
        "```mermaid",
        "flowchart LR",
        '    classDef entity fill:#e1f5fe,stroke:#01579b,stroke-width:2px;',
        '    classDef concept fill:#fff3e0,stroke:#e65100,stroke-width:1px;',
        "",
        "    subgraph Entities",
    ]

    for slug in entity_slugs:
        nid = _safe_id(slug)
        label = pages[slug]["label"]
        label_escaped = label.replace('"', "'")
        lines.append(f'        {nid}["{label_escaped}"]')
        lines.append(f"        class {nid} entity")

    lines.append("    end")
    lines.append("")

    lines.append("    subgraph Concepts")
    for slug in concept_slugs:
        nid = _safe_id(slug)
        label = pages[slug]["label"]
        label_escaped = label.replace('"', "'")
        lines.append(f'        {nid}["{label_escaped}"]')
        lines.append(f"        class {nid} concept")
    lines.append("    end")
    lines.append("")

    for src, dst in sorted(edges):
        lines.append(f"    {src} --> {dst}")

    lines.append("```")
    return "\n".join(lines)


def _build_index(pages: dict) -> str:
    lines = []

    canon = sorted(s for s, i in pages.items() if i["type"] == "entity" and is_canonical_slug(s))
    other = sorted(s for s, i in pages.items() if i["type"] == "entity" and not is_canonical_slug(s))
    concepts = sorted(s for s, i in pages.items() if i["type"] == "concept")

    if canon:
        lines.append("## Canonical Entities")
        lines.append("")
        for slug in canon:
            label = _display_name(slug)
            lines.append(f"- [[{slug}|{label}]]")
        lines.append("")

    if other:
        lines.append(f"## Other Entity Pages ({len(other)})")
        lines.append("")
        for slug in other:
            lines.append(f"- [[{slug}]]")
        lines.append("")

    if concepts:
        lines.append(f"## Concepts ({len(concepts)})")
        lines.append("")
        for slug in concepts:
            lines.append(f"- [[{slug}]]")
        lines.append("")

    return "\n".join(lines)


def build_knowledge_graph(wiki_path: Path, title: str = "Knowledge Graph") -> str:
    pages = _scan_pages(wiki_path)
    edges = _collect_edges(pages)

    lines = [
        f"# {title}",
        "",
        f"Last updated: {datetime.now().isoformat()}",
        "",
        "> Mermaid flowchart — entities are blue, concepts are orange. Edges represent wikilink references.",
        "",
    ]

    mermaid_block = _build_mermaid(pages, edges)
    lines.append(mermaid_block)
    lines.append("")

    index_block = _build_index(pages)
    lines.append(index_block)

    lines.append("---")
    total = sum(1 for s, i in pages.items() if i["type"] == "entity" or i["type"] == "concept")
    lines.append(f"Total pages: {total} | Edges: {len(edges)}")

    result = "\n".join(lines)
    logger.info(
        "Knowledge graph built: %d pages, %d edges",
        total,
        len(edges),
    )
    return result
