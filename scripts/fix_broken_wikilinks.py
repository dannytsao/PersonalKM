#!/usr/bin/env python3
"""
Fix broken wikilinks created by Phase 2 summarizer.

Problem: Phase 2 migration added ## Related Entities sections with wikilinks
to entity names (e.g. [[claude-code]], [[anthropic]]) but those entity pages
don't exist as standalone files. This creates 2,137 broken links across 215 files.

Fix: Remove the ## Related Entities sections (these are placeholders that will
be regenerated correctly in Phase 5 when entity dedup is wired in).

Usage:
    python scripts/fix_broken_wikilinks.py [--dry-run]
"""

import argparse
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def fix_file(filepath: Path, dry_run: bool = False) -> dict:
    """Remove ## Related Entities section from a file body."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return {'file': filepath.name, 'status': 'error', 'error': str(e)}
    
    original = content
    
    # Split frontmatter
    if not content.startswith('---'):
        return {'file': filepath.name, 'status': 'skip', 'reason': 'No frontmatter'}

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {'file': filepath.name, 'status': 'skip', 'reason': 'No body'}
    fm = parts[1]
    body = parts[2]

    # Remove ## Related Entities section and everything after it
    related_idx = body.find('## Related Entities')
    if related_idx == -1:
        return {'file': filepath.name, 'status': 'unchanged', 'related_sections_removed': 0}
    
    body_before = body[:related_idx].rstrip()
    
    # Rebuild: frontmatter + body_before
    new_content = '---\n' + fm + '\n---\n\n' + body_before + '\n'
    
    if new_content != original:
        result = {
            'file': filepath.name,
            'status': 'modified',
            'related_sections_removed': 1,
            'saved_chars': len(original) - len(new_content),
        }
        if not dry_run:
            filepath.write_text(new_content, encoding='utf-8')
        return result
    else:
        return {'file': filepath.name, 'status': 'unchanged', 'related_sections_removed': 0}


def main():
    parser = argparse.ArgumentParser(description='Fix broken wikilinks from Phase 2 migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    parser.add_argument('--limit', type=int, default=0, help='Limit to N files')
    args = parser.parse_args()

    wiki_root = Path(__file__).parent.parent / 'wiki'
    files = []
    for subdir in ['entities', 'concepts']:
        d = wiki_root / subdir
        if d.exists():
            files.extend(d.glob('*.md'))

    files = sorted(files)
    if args.limit > 0:
        files = files[:args.limit]

    print(f"Found {len(files)} wiki files")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE FIX'}")
    print()

    modified = 0
    unchanged = 0
    errors = 0
    total_saved = 0

    def do_fix(f):
        return fix_file(f, dry_run=args.dry_run)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(do_fix, f): f for f in files}
        for future in as_completed(futures):
            result = future.result()
            if result['status'] == 'modified':
                modified += 1
                total_saved += result['saved_chars']
                print(f"  [FIXED] {result['file']} (-{result['saved_chars']} chars)")
            elif result['status'] == 'unchanged':
                unchanged += 1
            elif result['status'] == 'error':
                errors += 1
                print(f"  [ERROR] {result['file']}: {result['error']}")

    print()
    print(f"Modified: {modified}")
    print(f"Unchanged: {unchanged}")
    print(f"Errors: {errors}")
    print(f"Chars saved: {total_saved:,}")
    
    if args.dry_run:
        print()
        print("Run without --dry-run to apply.")


if __name__ == '__main__':
    main()
