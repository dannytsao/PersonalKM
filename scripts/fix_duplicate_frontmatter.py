#!/usr/bin/env python3
"""
One-time migration: repair pages whose frontmatter got wrapped in extra
stray "---" blocks by the entity_dedup.py::_append_capture() bug fixed in
IMPROVEMENT-BACKLOG.md P7 (sources: regex + "---" body divider).

Corruption shape (confirmed on 6 real vault pages): the real frontmatter
(the block containing `title:`) ends up sandwiched behind one or more
"orphan" blocks that contain nothing but a stray `wikilink_processed:`
timestamp. Every frontmatter reader in this codebase splits content on the
first two "---" occurrences, so once this happens, `title`/`canonical`/
`sources`/`tags`/etc. silently stop being visible as metadata — they read
as plain body text instead.

Repair: find the last "---"-delimited block that contains `title:` (the
real frontmatter), take the freshest `wikilink_processed:` timestamp found
across it and every orphan block before it (Phase B kept refreshing only
the outermost orphan's timestamp every hour), and rebuild the page as a
single clean frontmatter block followed by the real body. Nothing in the
real body or other frontmatter fields is touched.

AGENTS.md hard rule 1: agents must never touch the vault directly. This
script is tested against tests/fixtures/ only; run it yourself against
the real vault path.

Usage:
    python scripts/fix_duplicate_frontmatter.py --vault <path> [--apply]
"""

import argparse
import re
from pathlib import Path

_WIKILINK_PROCESSED_RE = re.compile(r"^wikilink_processed:\s*(\S+)\s*$", re.MULTILINE)


def is_corrupted(content: str) -> bool:
    """True if the content has 3+ '---' occurrences and the first
    frontmatter-looking block doesn't contain `title:` (i.e. the real
    frontmatter has been pushed behind orphan wrapper blocks)."""
    if not content.startswith("---"):
        return False
    parts = content.split("---")
    if len(parts) < 4:  # fewer than 3 delimiters -> not this shape
        return False
    return "title:" not in parts[1]


def repair(content: str) -> str:
    """Collapse a corrupted page back to a single clean frontmatter block."""
    parts = content.split("---")
    # parts[0] is empty/whitespace before the first "---".
    # parts[1..-2] are the interior blocks; parts[-1] is the real body.
    interior = parts[1:-1]
    real_body = parts[-1]

    real_fm_idx = next(
        (i for i in range(len(interior) - 1, -1, -1) if "title:" in interior[i]),
        None,
    )
    if real_fm_idx is None:
        return content  # not actually repairable this way; leave untouched
    real_fm = interior[real_fm_idx]

    latest_ts = None
    for block in interior:
        for ts in _WIKILINK_PROCESSED_RE.findall(block):
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts

    if latest_ts is not None:
        if _WIKILINK_PROCESSED_RE.search(real_fm):
            real_fm = _WIKILINK_PROCESSED_RE.sub(
                f"wikilink_processed: {latest_ts}", real_fm, count=1
            )
        else:
            real_fm = real_fm.rstrip("\n") + f"\nwikilink_processed: {latest_ts}\n"

    return f"---\n{real_fm.strip()}\n---\n\n{real_body.lstrip(chr(10))}"


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
    for sub in ("entities", "concepts"):
        d = wiki_root / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            if not is_corrupted(content):
                continue
            new_content = repair(content)
            if new_content == content:
                continue
            changed += 1
            before_delims = content.count("---")
            after_delims = new_content.count("---")
            print(f"  [{'FIXED' if args.apply else 'WOULD FIX'}] {f.relative_to(wiki_root)}: "
                  f"{before_delims} -> {after_delims} '---' occurrences")
            if args.apply:
                f.write_text(new_content, encoding="utf-8")

    print(f"\nFiles changed: {changed}")
    if not args.apply:
        print("\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
