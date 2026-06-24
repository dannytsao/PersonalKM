#!/usr/bin/env python3
"""
Strip YAML frontmatter from all raw/ note files.

This migration complements the removal of Layer 1 YAML from notes.py render_note().
Previously raw/ files had a full frontmatter block that was stripped during
ingestion anyway — this cleans up existing files to match the new format.

New raw/ files (post-migration) will be written without frontmatter via notes.py.
Existing wiki/ files are unaffected — their frontmatter comes from ingestion_v2.py.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter block from markdown, return body only.

    Handles:
    - Standard frontmatter: --- ... --- (on their own lines)
    - Merged closers: ---# Heading (--- on same line as content)
    - Orphaned frontmatter: file starts with --- but no closer
    - Multiple consecutive blocks
    """
    lines = content.split('\n')
    n = len(lines)
    skip_indices = set()
    i = 0
    while i < n:
        stripped = lines[i].strip()
        if stripped == '---':
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                next_stripped = lines[j].strip()
                if next_stripped == '---':
                    depth -= 1
                    j += 1
                elif next_stripped.startswith('---'):
                    depth -= 1
                    j += 1
                elif depth == 1 and lines[j].startswith('---'):
                    depth -= 1
                    j += 1
                else:
                    j += 1
            for k in range(i, j):
                skip_indices.add(k)
            i = j
        else:
            i += 1

    cleaned = []
    for idx, line in enumerate(lines):
        if idx in skip_indices:
            continue
        s = line.strip()
        # Also skip orphaned key: value metadata lines (outside blocks)
        if ':' in s and not s.startswith('#') and not s.startswith('[') and s == s.strip():
            # Likely a frontmatter key:value line (no leading markdown char)
            parts = s.split(':', 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                # Looks like a frontmatter key — skip
                continue
        cleaned.append(line)

    return '\n'.join(cleaned).strip() + '\n'


def migrate_file(path: Path) -> bool:
    """Migrate a single raw/ file. Returns True if changed."""
    try:
        original = path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ⚠️  Could not read {path}: {e}")
        return False

    if not original.strip().startswith('---'):
        # No frontmatter — already clean
        return False

    # Find first non-frontmatter line
    lines = original.split('\n')
    if lines[0].strip() != '---':
        return False

    # Find closing ---
    end_idx = None
    depth = 0
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if depth == 0:
                depth = 1
            else:
                end_idx = i
                break

    if end_idx is None:
        print(f"  ⚠️  Unclosed frontmatter in {path.name} — skipping")
        return False

    # Extract body (after closing ---)
    body_lines = lines[end_idx + 1:]
    body = '\n'.join(body_lines).strip()

    if not body:
        print(f"  ⚠️  Empty body after stripping {path.name} — skipping")
        return False

    # Write back pure body
    path.write_text(body + '\n', encoding='utf-8')
    return True


def main() -> None:
    vault_path = REPO_ROOT

    if len(sys.argv) > 1:
        vault_path = Path(sys.argv[1])

    raw_path = vault_path / 'raw'
    if not raw_path.exists():
        print(f"No raw/ directory found at {raw_path}")
        sys.exit(1)

    # Find all markdown files in raw/ (any depth)
    md_files = list(raw_path.glob('**/*.md'))
    if not md_files:
        print("No .md files found in raw/")
        return

    print(f"Scanning {len(md_files)} file(s) in {raw_path}...")

    migrated = 0
    skipped = 0
    errors = 0

    for f in sorted(md_files):
        changed = migrate_file(f)
        if changed:
            print(f"  ✅ Migrated {f.relative_to(vault_path)}")
            migrated += 1
        else:
            skipped += 1

    print()
    print(f"Results: {migrated} migrated, {skipped} already clean, {errors} errors")


if __name__ == '__main__':
    main()
