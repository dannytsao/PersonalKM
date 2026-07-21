#!/usr/bin/env python3
"""
One-time migration: reset the `sources:` field on stub pages that were
polluted with cross-references to OTHER wiki pages instead of this entity's
own raw-capture provenance (IMPROVEMENT-BACKLOG.md P6#18).

Root cause (already fixed for newly-created stubs, in
ingestion_v2.py::_auto_promote_entities() and
scripts/phase6_backfill.py::_create_missing_stubs()): "which other wiki
pages mention this term" was being written into `sources:` (semantically
wrong -- that field means "this entity's own capture provenance"). That
same cross-reference information is already correctly recorded in each
page's own `## Mentions` section, so resetting `sources:` to `[]` loses
nothing.

This only touches pages matching the exact pollution shape: a `sources:`
list whose every entry is a `wiki/...` path (not a real raw-capture
citation like `[[Archive/raw/...]]`), AND that has a `## Mentions` section
backing up the same information. Pages with any real source are left
untouched.

AGENTS.md hard rule 1: agents must never touch the vault directly. This
script is tested against tests/fixtures/ only; run it yourself against
the real vault path.

Usage:
    python scripts/fix_stub_sources_pollution.py --vault <path> [--apply]
"""

import argparse
import re
from pathlib import Path

_SOURCES_BLOCK_RE = re.compile(r"^sources:\n((?:  - .*\n)+)", re.MULTILINE)


def is_polluted(content: str) -> bool:
    """True if every `sources:` entry is a wiki/... path (not a raw capture
    citation), and a `## Mentions` section exists to back it up."""
    m = _SOURCES_BLOCK_RE.search(content)
    if not m:
        return False
    entries = [line.strip()[2:].strip() for line in m.group(1).splitlines() if line.strip()]
    if not entries:
        return False
    all_wiki_paths = all(e.strip('"').startswith("wiki/") for e in entries)
    return all_wiki_paths and "## Mentions" in content


def repair(content: str) -> str:
    return _SOURCES_BLOCK_RE.sub("sources: []\n", content, count=1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Path to the vault root (contains wiki/)")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run preview)")
    args = parser.parse_args()

    wiki_root = Path(args.vault) / "wiki"
    if not wiki_root.exists():
        raise SystemExit(f"No wiki/ directory under {args.vault}")

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")

    changed = 0
    for f in sorted((wiki_root / "entities").glob("*.md")):
        content = f.read_text(encoding="utf-8")
        if not is_polluted(content):
            continue
        new_content = repair(content)
        if new_content == content:
            continue
        changed += 1
        print(f"  [{'FIXED' if args.apply else 'WOULD FIX'}] {f.relative_to(wiki_root)}")
        if args.apply:
            f.write_text(new_content, encoding="utf-8")

    print(f"\nFiles changed: {changed}")
    if not args.apply:
        print("\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
