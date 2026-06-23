#!/usr/bin/env python3
"""
Backfill wikilinks for ALL existing wiki pages.
Uses the entity registry to find which entities each page references,
then adds outbound links AND backlinks bidirectionally.
Run once; not needed again unless schema changes.
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.entity_dedup import EntityRegistry, normalize_entity_name, append_to_body
from bot.wikilinks import WikilinkManager


def slugify(text: str) -> str:
    """Same slugify used in WikilinkManager._normalize."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


def backfill_wikilinks(wiki_root: Path, dry_run: bool = False) -> dict:
    """
    Scan every wiki page, detect entity mentions using the registry,
    and backfill bidirectional wikilinks for ALL existing pages.
    """
    registry = EntityRegistry(wiki_root)
    wm = WikilinkManager(wiki_root, registry)

    # Build slug -> canonical entity page path from registry
    all_entity_names = registry.get_all_entity_names()
    slug_to_canonical = {}
    for name in all_entity_names:
        slug = slugify(name)
        match = registry.find_entity_match(name)
        if match:
            slug_to_canonical[slug] = match

    print(f"Registry has {len(all_entity_names)} entity names, {len(slug_to_canonical)} resolvable slugs")

    all_pages = list(wiki_root.rglob('*.md'))
    all_pages = [p for p in all_pages if p.name not in ('index.md', 'log.md')]

    # Build slug -> list of pages that mention it
    slug_referrers: dict[str, list[Path]] = defaultdict(list)

    stats = {'pages': 0, 'outbound': 0, 'backlinks': 0, 'skipped': 0, 'errors': 0}

    for page in all_pages:
        try:
            content = page.read_text(encoding='utf-8')
            stats['pages'] += 1

            # Find all slugs mentioned in this page's content
            mentioned_slugs = set()
            for slug in slug_to_canonical:
                # Use word boundary to avoid substring matches
                # e.g., "docker" should not match "dockerfile"
                pattern = r'\b' + re.escape(slug) + r'\b'
                if re.search(pattern, content, re.IGNORECASE):
                    mentioned_slugs.add(slug)

            if not mentioned_slugs:
                stats['skipped'] += 1
                continue

            # For each mentioned slug, add outbound link
            new_outbound = 0
            for slug in mentioned_slugs:
                target_path = slug_to_canonical[slug]
                # Only add if not already linked
                link_text = f'[[{target_path.name}]]'
                if link_text not in content and f'[[{slug}]]' not in content:
                    if not dry_run:
                        wm._add_outbound_links(page, [slug])
                    new_outbound += 1

            # Add backlinks to the target entity pages
            new_backlinks = 0
            for slug in mentioned_slugs:
                target_path = slug_to_canonical[slug]
                # Check if backlink already exists
                target_content = target_path.read_text(encoding='utf-8')
                backlink_marker = f'[[{page.name}]]'
                if backlink_marker not in target_content:
                    if not dry_run:
                        wm._add_backlinks_to_mentioned_entities(page, [slug])
                    new_backlinks += 1

            stats['outbound'] += new_outbound
            stats['backlinks'] += new_backlinks

        except Exception as e:
            stats['errors'] += 1
            print(f"  ERROR {page.name}: {e}")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backfill wikilinks for all wiki pages')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without modifying files')
    parser.add_argument('--wiki', default='wiki', help='Wiki root path (default: wiki)')
    args = parser.parse_args()

    wiki_root = Path(args.wiki)
    if not wiki_root.exists():
        print(f"ERROR: {wiki_root} does not exist")
        sys.exit(1)

    print(f"=== Wikilink Backfill ===")
    print(f"Wiki root: {wiki_root.absolute()}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    stats = backfill_wikilinks(wiki_root, dry_run=args.dry_run)

    print()
    print("=== Results ===")
    print(f"Pages scanned:  {stats['pages']}")
    print(f"Outbound links:  {stats['outbound']} added")
    print(f"Backlinks:      {stats['backlinks']} added")
    print(f"Skipped:        {stats['skipped']} (no entities found)")
    print(f"Errors:         {stats['errors']}")
    if args.dry_run:
        print("\nRun without --dry-run to apply changes.")
