#!/usr/bin/env python3
"""
Migrate existing wiki pages to the new topic + tags schema.

Adds 'topic' field, resets 'tags' to [], and sets 'type' based on topic.

Usage:
    python scripts/migrate_wiki_topic_tags.py --vault . --structural
    python scripts/migrate_wiki_topic_tags.py --vault . --dry-run --structural
    python scripts/migrate_wiki_topic_tags.py --vault . --llm   # LLM-backed
"""
import argparse
import re
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

TOPIC_OPTIONS = {
    "AI-Agent-&-Tools",
    "Automation-Workflows",
    "PKM-&-System-Design",
    "Tech-Trends-&-Insights",
    "Personal-Interests",
}
TOPIC_ENTITIES = {"AI-Agent-&-Tools", "Automation-Workflows"}
DEFAULT_TOPIC = "Tech-Trends-&-Insights"


def validate_topic(topic: str) -> str:
    return topic if topic in TOPIC_OPTIONS else DEFAULT_TOPIC


def has_topic_field(content: str) -> bool:
    if not content.startswith("---"):
        return False
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    return bool(re.search(r"^topic:\s*\S", parts[1], re.MULTILINE))


def extract_body(content: str) -> str:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content


def migrate_frontmatter(content: str, topic: str = DEFAULT_TOPIC) -> str:
    """
    Replace tags + type blocks with topic + clean tags + subfolder-based type.
    Uses a multi-line regex to strip the entire tags: [...] block safely.
    """
    # Handle files that start with a bare \n instead of ---\n
    fm_start = content.find("\ntitle:")
    if fm_start == -1:
        return content
    body_start = content.find("\n---\n", fm_start)
    if body_start == -1:
        return content

    fm = content[fm_start + 1:body_start]
    body = content[body_start + 5:]

    subfolder = "entities" if topic in TOPIC_ENTITIES else "concepts"
    page_type = subfolder.rstrip("s")

    # ── Remove entire tags: [...] block (single-line OR multi-line YAML list) ──
    fm = re.sub(
        r'^tags:\s*\[.*?\](\n(?:  - .+?\n)*)',
        r'tags: []\n',
        fm,
        flags=re.MULTILINE | re.DOTALL,
    )
    fm = re.sub(r'^tags: \[.*?\]', 'tags: []', fm, flags=re.MULTILINE)
    fm = re.sub(
        r'^tags:\n((?:  - [^\n]*\n)+)',
        r'tags: []\n',
        fm,
        flags=re.MULTILINE,
    )

    # ── Remove existing type: line ──
    fm = re.sub(r'^type: .*$', '', fm, flags=re.MULTILINE)

    # ── Insert topic after 'updated:' line ──
    fm = re.sub(
        r'^(updated: .+)$',
        r'\1\ntopic: ' + topic,
        fm,
        flags=re.MULTILINE,
    )

    # ── Insert type after 'tags: []' ──
    fm = re.sub(
        r'^(tags: \[\])$',
        r'\1\ntype: ' + page_type,
        fm,
        flags=re.MULTILINE,
    )

    # ── Clean up orphaned list items ──
    fm = re.sub(
        r'^(tags: \[\])$\n((?:  - [^\n]*\n)+)',
        r'\1\n',
        fm,
        flags=re.MULTILINE,
    )

    # Clean up empty lines
    fm = re.sub(r'\n\n\n+', '\n\n', fm)

    # ── Fix orphaned sources: ──
    fm = re.sub(r'^sources:\s*$\n((?:  - [^\n]*\n)*)', r'sources:\1', fm, flags=re.MULTILINE)
    fm = re.sub(r'^sources:\s*$', '', fm, flags=re.MULTILINE)

    return fm.strip() + "\n---\n\n" + body


def migrate_with_llm(content: str, vault_path: Path) -> str:
    """Use LLM to determine topic + tags, then apply structural migration."""
    from bot.llm_summarizer import summarize_content

    body = extract_body(content)
    if not body or len(body.strip()) < 50:
        return migrate_frontmatter(content)

    try:
        result = summarize_content(body, page_type="entity", source_path="migration")
        topic = validate_topic(result.get("topic", DEFAULT_TOPIC))
    except Exception as e:
        logger.warning(f"  LLM failed ({e}), using structural fallback")
        return migrate_frontmatter(content)

    return migrate_frontmatter(content, topic=topic)


def migrate_page(page_path: Path, dry_run: bool, llm: bool, vault_path: Path) -> dict:
    try:
        content = page_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"status": "error", "reason": str(e)}

    if has_topic_field(content):
        return {"status": "skip", "reason": "already has topic field"}

    old_tags = re.search(r'^tags:\s*(\[.*?\]|\n(?:  - .+?\n)*)', content, re.MULTILINE | re.DOTALL)

    new_content = migrate_with_llm(content, vault_path) if llm else migrate_frontmatter(content)

    new_topic = re.search(r'^topic:\s*(.+)', new_content, re.MULTILINE)

    change = f"tags: (old) → topic: {new_topic.group(1).strip() if new_topic else '?'}"

    if not dry_run:
        page_path.write_text(new_content, encoding="utf-8")

    return {"status": "migrated", "change": change}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--structural", action="store_true")
    args = parser.parse_args()

    if not args.vault.exists():
        logger.error(f"Vault not found: {args.vault}")
        sys.exit(1)
    if args.llm and args.structural:
        logger.error("--llm and --structural are mutually exclusive")
        sys.exit(1)
    if not args.llm and not args.structural:
        logger.error("Use --llm or --structural")
        sys.exit(1)

    wiki_path = args.vault / "wiki"
    if not wiki_path.exists():
        logger.error(f"wiki/ not found in {args.vault}")
        sys.exit(1)

    if args.llm:
        sys.path.insert(0, str(args.vault))

    mode = "LLM" if args.llm else "structural"
    logger.info(f"[{mode} migration] vault={args.vault}")
    logger.info(f"[{'DRY RUN' if args.dry_run else 'WRITE'}]")

    all_pages = sorted(
        list((wiki_path / "entities").glob("*.md")) +
        list((wiki_path / "concepts").glob("*.md"))
    )

    migrated = skipped = errors = 0
    changes = []

    for page in all_pages:
        result = migrate_page(page, dry_run=args.dry_run, llm=args.llm, vault_path=args.vault)
        if result["status"] == "migrated":
            migrated += 1
            changes.append(f"  ✅ {page.name}: {result['change']}")
        elif result["status"] == "skip":
            skipped += 1
        else:
            errors += 1
            logger.error(f"  ❌ {page.name}: {result['reason']}")

    for c in changes:
        logger.info(c)

    logger.info(f"\nResults: {migrated} migrated, {skipped} skipped, {errors} errors")
    if args.dry_run:
        logger.info("\n[DRY RUN] No files were written.")


if __name__ == "__main__":
    main()
