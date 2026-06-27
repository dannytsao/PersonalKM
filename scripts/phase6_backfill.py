#!/usr/bin/env python3
"""
Phase 6: Canonical Entity Backfill
====================================
One-time migration that:

1. Scans all existing wiki/entities/*.md and wiki/concepts/*.md
2. For each page, determines which canonical entity it belongs to
3. Creates canonical entity pages (no date prefix, e.g., entities/hermes-agent.md)
4. Aggregates content from all date-prefixed pages into the canonical page
5. Rebuilds bidirectional wikilinks for ALL pages
6. Fixes corrupted frontmatter
7. Updates index.md, log.md, knowledge-graph.md

Exit Conditions:
    - 20+ canonical entity pages exist
    - 80%+ of wiki pages have >= 1 incoming backlink
    - 0 broken wikilinks
    - All frontmatter is valid

Usage:
    python scripts/phase6_backfill.py [--vault PATH] [--dry-run]

Dry-run mode:
    python scripts/phase6_backfill.py --dry-run
    Shows what would be done without writing anything.
"""
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("phase6")

VAULT_ROOT = Path(os.getenv("VAULT_PATH", str(Path.home() / ".personalkm/PersonalKM-worker")))

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from bot.entity_dedup import (
    EntityRegistry,
    CANONICAL_ENTITIES,
    normalize_entity_name,
    canonical_slug_from_name,
    is_canonical_slug,
    parse_frontmatter,
)
from bot.llm_summarizer import detect_entity_mentions, _strip_frontmatter

# ── Entity-to-canonical mapping (which entities appear in which pages) ──

# Maps: canonical_slug → list of filename patterns that match
ENTITY_KEYWORDS: dict[str, list[str]] = {
    "hermes-agent": ["hermes-agent", "hermes os", "nous-research"],
    "claude-code": ["claude-code", "claude code", "claude"],
    "codex": ["codex"],
    "cursor": ["cursor"],
    "chatgpt": ["chatgpt", "chat-gpt", "gpt"],
    "gemini": ["gemini"],
    "cloudflare": ["cloudflare"],
    "anthropic": ["anthropic"],
    "sakana-ai": ["sakana", "fugu", "fable", "mythos"],
    "glm-5-2": ["glm-5", "glm 5", "z.ai", "zhipu"],
    "cometapi": ["cometapi", "comet-api"],
    "deepseek": ["deepseek"],
    "qwen": ["qwen"],
    "minimax-m3": ["minimax-m3", "minimax m3"],
    "siliconflow": ["siliconflow", "硅基流动"],
    "openrouter": ["openrouter"],
    "antigravity": ["antigravity", "agy"],
    "harness": ["harness"],
    "rc-astro": ["rc-astro", "rc astro", "pixinsight", "blurxterminator", "noisexterminator", "starxterminator"],
    "mistral-ai": ["mistral"],
    "openclaw": ["openclaw"],
    "anges-ai": ["anges"],
    "lushbinary": ["lushbinary"],
    "apple-silicon": ["apple-silicon", "apple silicon", "apple silicon mac", "mac ai agent", "on-device apple"],
    "motioner": ["motioner"],
    "github": ["github"],
    "poyin-chen": ["poyin-chen", "陳柏尹", "poyin chen"],
    "paul-kuo": ["paul-kuo", "paul kuo"],
    "newmobilelife": ["newmobilelife"],
    "inside": ["inside.com"],
}

# ── Frontmatter repair ──

BROKEN_FRONTMATTER_RE = re.compile(
    r'^(-{3,})\n.*?^\1',
    re.DOTALL | re.MULTILINE,
)

def safe_read_frontmatter(path: Path) -> tuple[dict, str]:
    """Read frontmatter with graceful fallback for broken YAML."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {}, f"ERROR: {e}"
    fm, body = parse_frontmatter(content)
    return fm, body


def fix_frontmatter(path: Path, dry_run: bool = False) -> bool:
    """
    Fix corrupted frontmatter in a wiki page.
    Returns True if changes were made.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return False

    original = content

    # Fix: wikilink_processed leaking into other fields
    # e.g., "title: glm-52-deepseek\nwikilink_processed:...type: entity"
    content = re.sub(
        r'(wikilink_processed: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*(\w+:)',
        r'\1\n\2',
        content,
    )

    # Fix: missing closing ---
    if content.startswith("---") and "---" in content[3:]:
        first_close = content.find("---", 3)
        if first_close > 0:
            rest = content[first_close + 3:].strip()
            if rest and not rest.startswith("---"):
                pass

    # Fix: empty title
    content = re.sub(r'^title: \s*$', 'title: untitled', content, flags=re.MULTILINE)

    if content != original:
        if not dry_run:
            path.write_text(content, encoding="utf-8")
        return True
    return False


# ── Content aggregation helpers ──

def extract_body_without_see_also(content: str) -> str:
    """Extract body content, stripping the '## See also' section."""
    body = _strip_frontmatter(content)
    see_also_idx = body.find("## See also")
    if see_also_idx >= 0:
        body = body[:see_also_idx].strip()
    return body


def aggregate_entity_content(pages: list[Path]) -> dict:
    """
    Aggregate content from multiple pages about the same entity.
    Returns dict with: summary, key_facts, sources, tags, topic, body_sections
    """
    summaries = []
    key_facts = []
    sources = []
    tags = set()
    topic_counts = defaultdict(int)
    body_sections = []

    for page in pages:
        content = page.read_text(encoding="utf-8")
        fm, body = safe_read_frontmatter(page)
        title = fm.get("title", page.stem)

        # Collect metadata
        if "sources" in fm:
            src = fm["sources"]
            if isinstance(src, str) and src.startswith("["):
                import json
                try:
                    sources.extend(json.loads(src))
                except (json.JSONDecodeError, TypeError):
                    sources.append(src)
            elif isinstance(src, list):
                sources.extend(src)
            else:
                sources.append(str(src))

        if "tags" in fm:
            raw = fm["tags"]
            if isinstance(raw, str) and raw.startswith("["):
                import json
                try:
                    for t in json.loads(raw):
                        tags.add(t)
                except (json.JSONDecodeError, TypeError):
                    tags.add(str(raw))
            elif isinstance(raw, list):
                for t in raw:
                    tags.add(t)

        topic = fm.get("topic", "")
        if topic:
            topic_counts[topic] += 1

        # Collect body (without See also)
        body_clean = extract_body_without_see_also(content)
        if body_clean:
            body_sections.append((title, page.stem, body_clean))

        # Extract summary from ## Summary section
        summary_match = re.search(r'## Summary\n\n(.+?)(?:\n\n|$)', body_clean, re.DOTALL)
        if summary_match:
            s = summary_match.group(1).strip()
            if s and len(s) > 20:
                summaries.append(s)

        # Extract key facts
        kf_match = re.findall(r'^- (.+)$', body_clean, re.MULTILINE)
        for kf in kf_match:
            if kf and len(kf) > 10 and kf not in key_facts:
                key_facts.append(kf)

    # Determine dominant topic
    dominant_topic = max(topic_counts, key=topic_counts.get) if topic_counts else "Tech-Trends-&-Insights"

    return {
        "summary": summaries[0] if summaries else "",
        "key_facts": key_facts[:10],
        "sources": list(dict.fromkeys(sources)),
        "tags": sorted(tags),
        "topic": dominant_topic,
        "body_sections": body_sections,
    }


def build_canonical_content(slug: str, aggregated: dict) -> str:
    """Build the markdown body for a canonical entity page."""
    lines = []
    display_name = CANONICAL_ENTITIES.get(slug, slug.replace("-", " ").title())

    lines.append(f"# {display_name}")
    lines.append("")

    if aggregated["summary"]:
        lines.append(f"{aggregated['summary']}")
        lines.append("")

    if aggregated["key_facts"]:
        lines.append("## Key Facts")
        lines.append("")
        for kf in aggregated["key_facts"]:
            lines.append(f"- {kf}")
        lines.append("")

    if aggregated["body_sections"]:
        lines.append("## Captures")
        lines.append("")
        for title, stem, body in aggregated["body_sections"]:
            lines.append(f"### {title}")
            lines.append("")
            lines.append(body)
            lines.append("")

    return "\n".join(lines)


def build_canonical_frontmatter(slug: str, aggregated: dict) -> str:
    """Build frontmatter for a canonical entity page."""
    display_name = CANONICAL_ENTITIES.get(slug, slug.replace("-", " ").title())
    today = datetime.now().strftime("%Y-%m-%d")

    sources_str = ",\n  ".join(f'"{s}"' for s in aggregated["sources"][:10]) if aggregated["sources"] else ""
    tags_str = ", ".join(aggregated["tags"][:10]) if aggregated["tags"] else ""

    return f"""---
title: {display_name}
canonical: true
created: {today}
updated: {today}
type: entity
topic: {aggregated["topic"]}
sources:
  [{sources_str}]
tags:
  [{tags_str}]
confidence: medium
---"""


# ── Main migration ──

def run_phase6(vault_path: Path, dry_run: bool = False) -> dict:
    """
    Execute Phase 6 backfill.
    
    Returns summary dict.
    """
    start = datetime.now()
    wiki_path = vault_path / "wiki"

    logger.info("=" * 70)
    logger.info(f"PHASE 6: Canonical Entity Backfill")
    logger.info(f"Vault: {vault_path}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 70)

    # Step 1: Scan all existing pages
    all_pages = []
    for subdir in ("entities", "concepts"):
        dir_path = wiki_path / subdir
        if not dir_path.exists():
            continue
        for f in sorted(dir_path.glob("*.md")):
            all_pages.append(f)

    logger.info(f"Total wiki pages found: {len(all_pages)}")

    # Step 2: Fix corrupted frontmatter
    fm_fixed = 0
    for page in all_pages:
        if fix_frontmatter(page, dry_run=dry_run):
            fm_fixed += 1
            logger.info(f"  Fixed frontmatter: {page.name}")

    logger.info(f"Frontmatter fixes: {fm_fixed}")

    # Step 3: Classify each page → canonical entity
    #
    # Matching priority:
    #   1. Filename stem contains canonical slug (strongest signal)
    #   2. Frontmatter title matches canonical entity
    #   3. Body contains strong keyword match (page seems primarily about the entity)
    #   4. Entity mention detection (weakest - used only for orphan prevention)
    #
    # Avoid: matching pages that MENTION an entity tangentially (e.g., an aggregate
    # page referencing "motioner" in passing). Those get wikilinks, not aggregation.
    page_to_canonical: dict[Path, Optional[str]] = {}
    canonical_to_pages: dict[str, list[Path]] = defaultdict(list)
    unclassified: list[Path] = []

    for page in all_pages:
        content = page.read_text(encoding="utf-8")
        body = _strip_frontmatter(content) if "---" in content else content
        stem = page.stem
        stem_lower = stem.lower()

        # 1. Filename matching (strongest)
        matched_slug = canonical_slug_from_name(stem)

        # 2. Frontmatter title matching
        if not matched_slug:
            fm, _ = parse_frontmatter(content)
            title = fm.get("title", "")
            if title:
                matched_slug = canonical_slug_from_name(title)

        # 3. Body keyword pattern matching (first 400 chars)
        #    Strong signal: keyword appears early in body → score 2
        #    Filename hints: keyword in filename stem → score 3 (strongest)
        if not matched_slug:
            body_start = body[:400].lower()
            head_matches = []
            for slug, keywords in ENTITY_KEYWORDS.items():
                if any(kw.lower() in stem_lower for kw in keywords):
                    head_matches.append((3, slug))
                elif any(kw.lower() in body_start for kw in keywords):
                    head_matches.append((2, slug))

            if head_matches:
                head_matches.sort(key=lambda x: -x[0])
                matched_slug = head_matches[0][1]

        # 4. Entity mention detection (weakest)
        #    Only used for canonical pages that have NO other matches
        #    to ensure we don't miss important entities
        if not matched_slug:
            entities = detect_entity_mentions(body[:500])  # Only first 500 chars
            entity_counts = {}
            for entity in entities:
                slug = canonical_slug_from_name(entity)
                if slug:
                    entity_counts[slug] = entity_counts.get(slug, 0) + 1
            # Only match if the entity is mentioned 2+ times (not just a passing reference)
            repeated = [(c, s) for s, c in entity_counts.items() if c >= 2]
            if repeated:
                repeated.sort(key=lambda x: -x[0])
                matched_slug = repeated[0][1]

        if matched_slug:
            page_to_canonical[page] = matched_slug
            canonical_to_pages[matched_slug].append(page)
        else:
            unclassified.append(page)

    logger.info(f"Pages matched to canonical entities: {len(page_to_canonical)}")
    logger.info(f"Unclassified pages (left as-is): {len(unclassified)}")
    for slug, pages in sorted(canonical_to_pages.items()):
        logger.info(f"  {slug}: {len(pages)} pages → {', '.join(p.name for p in pages)}")
    if unclassified:
        logger.info(f"  Unclassified: {', '.join(p.name for p in unclassified)}")

    # Step 4: Create/update canonical entity pages
    canonical_created = 0
    canonical_updated = 0

    for slug in sorted(CANONICAL_ENTITIES):
        pages = canonical_to_pages.get(slug, [])
        if not pages:
            continue

        display_name = CANONICAL_ENTITIES[slug]
        canonical_path = wiki_path / "entities" / f"{slug}.md"

        if not dry_run:
            if canonical_path.exists():
                logger.info(f"  Canonical page exists: {slug}.md — will not overwrite")
                canonical_updated += 1
                continue

            # Aggregate content from all matched pages
            aggregated = aggregate_entity_content(pages)
            frontmatter = build_canonical_frontmatter(slug, aggregated)
            body = build_canonical_content(slug, aggregated)
            content = frontmatter + "\n\n" + body
            canonical_path.write_text(content, encoding="utf-8")
            canonical_created += 1
            logger.info(f"  Created canonical: entities/{slug}.md ({len(pages)} pages aggregated)")
        else:
            logger.info(f"  [DRY-RUN] Would create: entities/{slug}.md ({len(pages)} pages)")

    logger.info(f"Canonical pages created: {canonical_created}, already exist: {canonical_updated}")

    # Step 5: Rebuild wikilinks for ALL pages using the canonical EntityRegistry
    if not dry_run:
        registry = EntityRegistry(wiki_path)
        from bot.wikilinks import WikilinkManager
        wm = WikilinkManager(wiki_path, registry)

        forward_total = 0
        backlink_total = 0
        orphan_count = 0
        total_with_links = 0

        for page in all_pages:
            content = page.read_text(encoding="utf-8")
            body = _strip_frontmatter(content)
            entities = detect_entity_mentions(body)

            if entities:
                result = wm.add_bidirectional_links(page, entities)
                forward_total += result.get("outbound", 0)
                backlink_total += result.get("backlinks", 0)
                if result.get("outbound", 0) > 0 or result.get("backlinks", 0) > 0:
                    total_with_links += 1
            else:
                orphan_count += 1

        # Validate
        broken = wm.validate_links()
        total_broken = sum(len(v) for v in broken.values())

        logger.info(f"Wikilinks added: {forward_total} forward, {backlink_total} backlinks")
        logger.info(f"Pages with new links: {total_with_links}")
        logger.info(f"Orphan pages (no entity mentions): {orphan_count}")
        logger.info(f"Broken wikilinks: {total_broken}")
        if broken:
            for path, links in broken.items():
                logger.warning(f"  Broken in {path}: {links}")

        # Step 6: Update knowledge-graph.md
        _update_knowledge_graph(wiki_path, registry)

        # Step 7: Update index.md
        _update_index(wiki_path, registry)

    else:
        logger.info("[DRY-RUN] Would rebuild wikilinks, knowledge-graph, and index")

    duration = (datetime.now() - start).total_seconds()
    summary = {
        "status": "success",
        "total_pages": len(all_pages),
        "canonical_pages_created": canonical_created,
        "canonical_pages_existing": canonical_updated,
        "frontmatter_fixed": fm_fixed,
        "unclassified_pages": len(unclassified),
        "duration_seconds": duration,
    }
    logger.info("=" * 70)
    logger.info("PHASE 6 COMPLETE")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 70)
    return summary


def _update_knowledge_graph(wiki_path: Path, registry: EntityRegistry) -> None:
    """Update knowledge-graph.md with Mermaid visualization + node index."""
    from bot.knowledge_graph import build_knowledge_graph
    md = build_knowledge_graph(wiki_path)
    (wiki_path / "knowledge-graph.md").write_text(md, encoding="utf-8")
    logger.info("Updated knowledge-graph.md (Mermaid)")


def _update_index(wiki_path: Path, registry: EntityRegistry) -> None:
    """Update index.md with canonical entity index."""
    entities_dir = wiki_path / "entities"
    concepts_dir = wiki_path / "concepts"

    all_entity_files = sorted(entities_dir.glob("*.md"))
    all_concept_files = sorted(concepts_dir.glob("*.md"))

    lines = ["# Wiki Index", "", f"Last updated: {datetime.now().isoformat()}", ""]

    lines.append("## Canonical Entities")
    lines.append("")
    for slug in sorted(CANONICAL_ENTITIES):
        path = entities_dir / f"{slug}.md"
        if path.exists():
            display = CANONICAL_ENTITIES[slug]
            lines.append(f"- [[{slug}|{display}]]")
    lines.append("")

    entities_no_canon = [f for f in all_entity_files if not is_canonical_slug(f.stem)]
    if entities_no_canon:
        lines.append(f"## Other Entities ({len(entities_no_canon)})")
        lines.append("")
        for f in entities_no_canon:
            lines.append(f"- [[{f.stem}]]")
        lines.append("")

    lines.append(f"## Concepts ({len(all_concept_files)})")
    lines.append("")
    for f in all_concept_files:
        lines.append(f"- [[{f.stem}]]")
    lines.append("")

    lines.append("---")
    lines.append(f"Total pages: {len(all_entity_files) + len(all_concept_files)}")

    (wiki_path / "index.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Updated index.md")


# ── CLI entry point ──

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 6: Canonical Entity Backfill")
    parser.add_argument("--vault", default=str(VAULT_ROOT), help="Vault root path")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing")
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        logger.error(f"Vault not found: {vault_path}")
        sys.exit(1)

    result = run_phase6(vault_path, dry_run=args.dry_run)
    if result.get("status") != "success":
        sys.exit(1)
    sys.exit(0)
