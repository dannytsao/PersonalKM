#!/usr/bin/env python3
"""
Migrate existing wiki pages to LLM-Wiki v2 distilled format.

Usage:
    python scripts/migrate_wiki_to_v2.py [--dry-run] [--limit N]

What it does:
    - Reads each file in wiki/entities/ and wiki/concepts/
    - Strips frontmatter (preserved as-is)
    - Replaces body with AI-distilled summary
    - Writes back to the same file

Exit conditions:
    - DRY-RUN: shows what would change without writing
    - --limit N: process only first N files (for testing)
    - Full run: processes all files

After running, wiki pages will show:
    - Short, scannable summaries (30-50 lines)
    - Original source preserved in sources: field
    - Raw files in raw/ never touched
"""

import argparse
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.llm_summarizer import summarize_content, distill_to_markdown


def extract_frontmatter(content: str) -> tuple[str, str]:
    """
    Split frontmatter from body content.
    Returns (frontmatter, body) — frontmatter includes the closing ---.
    """
    lines = content.split('\n')
    n = len(lines)
    
    if not lines or lines[0].strip() != '---':
        return '', content
    
    # Find frontmatter boundaries (handle merged ---# headings)
    fm_end = None
    i = 1
    while i < n:
        stripped = lines[i].strip()
        if stripped == '---':
            fm_end = i
            break
        elif stripped.startswith('---'):
            # Merged closer
            fm_end = i
            break
        i += 1
    
    if fm_end is None:
        return '', content
    
    # Include the closing --- in frontmatter
    fm_lines = lines[:fm_end + 1]
    body_lines = lines[fm_end + 1:]
    
    fm_text = '\n'.join(fm_lines)
    body_text = '\n'.join(body_lines).strip()
    
    return fm_text, body_text


def inject_body(frontmatter: str, distilled_body: str) -> str:
    """
    Put distilled body back into the existing frontmatter.
    Updates 'updated:' timestamp and 'confidence:' if present.
    """
    lines = frontmatter.split('\n')
    new_lines = []
    today = datetime.now().strftime('%Y-%m-%d')
    updated_set = False
    confidence_set = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('updated:'):
            new_lines.append(f'updated: {today}')
            updated_set = True
        elif stripped.startswith('confidence:'):
            new_lines.append(line)  # Keep existing confidence (AI re-distilled)
            confidence_set = True
        elif stripped == '---' and not updated_set:
            # Closing --- of frontmatter
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Add updated field if not found
    if not updated_set:
        # Insert before closing ---
        result = []
        for line in new_lines:
            result.append(line)
            if line.strip() == '---' and not updated_set:
                # Insert updated before this ---
                result.insert(-1, f'updated: {today}')
                updated_set = True
        new_lines = result
    
    fm_text = '\n'.join(new_lines)
    
    # Ensure blank line between frontmatter and body
    if not fm_text.endswith('\n'):
        fm_text += '\n'
    
    return fm_text + '\n' + distilled_body + '\n'


def migrate_file(filepath: Path, dry_run: bool = False) -> dict:
    """
    Migrate a single wiki file to v2 distilled format.
    Returns dict with migration result.
    """
    try:
        original = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return {
            'file': filepath.name,
            'status': 'error',
            'error': f'Cannot read: {e}',
            'saved': 0,
        }
    
    # Extract frontmatter and body
    frontmatter, body = extract_frontmatter(original)
    
    if not body.strip():
        return {
            'file': filepath.name,
            'status': 'skip',
            'reason': 'Empty body after frontmatter extraction',
            'saved': 0,
        }
    
    # Check if already migrated (has distilled marker)
    if '## Summary' in body and '## Key Facts' in body:
        return {
            'file': filepath.name,
            'status': 'skip',
            'reason': 'Already in v2 format',
            'saved': 0,
        }
    
    # Determine page type from frontmatter
    page_type = 'entity'
    if '/concepts/' in str(filepath):
        page_type = 'concept'
    
    # Summarize (MiniMax if available, fallback otherwise)
    result = summarize_content(original, page_type=page_type, source_path=str(filepath))
    distilled = distill_to_markdown(result, page_type=page_type)
    
    # Inject distilled body into existing frontmatter
    new_content = inject_body(frontmatter, distilled)
    
    # Calculate savings
    original_body_len = len(body)
    new_body_len = len(distilled)
    saved_chars = original_body_len - new_body_len
    
    if dry_run:
        return {
            'file': filepath.name,
            'status': 'dry-run',
            'original_body': original_body_len,
            'distilled_body': new_body_len,
            'saved': saved_chars,
            'confidence': result['confidence'],
            'summary_preview': result['summary'][:80],
        }
    
    # Write back
    try:
        filepath.write_text(new_content, encoding='utf-8')
        return {
            'file': filepath.name,
            'status': 'migrated',
            'original_body': original_body_len,
            'distilled_body': new_body_len,
            'saved': saved_chars,
            'confidence': result['confidence'],
            'summary_preview': result['summary'][:80],
        }
    except Exception as e:
        return {
            'file': filepath.name,
            'status': 'error',
            'error': str(e),
            'saved': 0,
        }


def main():
    parser = argparse.ArgumentParser(description='Migrate wiki pages to LLM-Wiki v2')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without writing')
    parser.add_argument('--limit', type=int, default=0, help='Limit to N files (for testing)')
    parser.add_argument('--workers', type=int, default=4, help='Parallel workers')
    args = parser.parse_args()

    wiki_root = Path(__file__).parent.parent / 'wiki'
    entities_dir = wiki_root / 'entities'
    concepts_dir = wiki_root / 'concepts'
    
    # Collect all wiki files
    files = []
    if entities_dir.exists():
        files.extend(entities_dir.glob('*.md'))
    if concepts_dir.exists():
        files.extend(concepts_dir.glob('*.md'))
    
    files = sorted(files)
    
    if args.limit > 0:
        files = files[:args.limit]
    
    print(f"Found {len(files)} wiki files")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print(f"Workers: {args.workers}")
    print()
    
    if args.dry_run:
        print(f"{'File':<50} {'Orig':>6} {'New':>6} {'Saved':>7} {'Conf':<6} {'Summary'}")
        print('-' * 110)
    
    results = []
    migrated = 0
    skipped = 0
    errors = 0
    total_saved = 0
    
    def do_migrate(f):
        return migrate_file(f, dry_run=args.dry_run)
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(do_migrate, f): f for f in files}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            if args.dry_run:
                if result['status'] == 'dry-run':
                    saved_pct = f"{result['saved']:>6}" if result['saved'] >= 0 else f"({-result['saved']:>5})"
                    print(f"{result['file'][:48]:<50} {result['original_body']:>6} {result['distilled_body']:>6} {saved_pct:>7} {result['confidence']:<6} {result['summary_preview'][:40]}")
                elif result['status'] == 'skip':
                    print(f"{result['file'][:48]:<50} {'SKIP':>6} {result['reason'][:50]}")
                elif result['status'] == 'error':
                    print(f"{result['file'][:48]:<50} {'ERROR':>6} {result['error'][:50]}")
            else:
                if result['status'] == 'migrated':
                    migrated += 1
                    total_saved += result['saved']
                    if migrated <= 10 or migrated % 20 == 0:
                        print(f"  [{migrated}] {result['file'][:60]} (-{result['saved']} chars)")
                elif result['status'] == 'skip':
                    skipped += 1
                elif result['status'] == 'error':
                    errors += 1
                    print(f"  ERROR: {result['file']} — {result['error']}")
    
    print()
    print('=' * 60)
    print(f"{'DRY RUN' if args.dry_run else 'MIGRATION'} COMPLETE")
    print(f"  Total files:   {len(files)}")
    if args.dry_run:
        dry_migrated = sum(1 for r in results if r['status'] == 'dry-run')
        dry_skipped = sum(1 for r in results if r['status'] == 'skip')
        dry_saved = sum(r['saved'] for r in results if r['status'] == 'dry-run')
        print(f"  Would migrate:  {dry_migrated}")
        print(f"  Would skip:    {dry_skipped}")
        print(f"  Chars saved:   {dry_saved:,}")
    else:
        print(f"  Migrated:      {migrated}")
        print(f"  Skipped:       {skipped}")
        print(f"  Errors:        {errors}")
        print(f"  Total saved:   {total_saved:,} chars")
    
    # Exit code
    if errors > 0:
        sys.exit(1)
    elif args.dry_run:
        print()
        print("Run without --dry-run to apply changes.")
    else:
        print()
        print("Migration complete. Raw files in raw/ are untouched.")


if __name__ == '__main__':
    main()
