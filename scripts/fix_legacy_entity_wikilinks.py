#!/usr/bin/env python3
"""
One-time migration: repair wikilinks written before the slug-normalization
fix in llm_summarizer.py::distill_to_markdown() (see IMPROVEMENT-BACKLOG.md
P6#17).

Two categories of pre-existing damage in wiki/entities/ and wiki/concepts/:

1. `[[topic-*]]` links — fabricated from arbitrary Chinese sentence
   fragments by the old detect_entity_mentions() heuristic. No page will
   ever exist for these; the link is stripped (bullet lines removed
   entirely, inline occurrences unwrapped to plain text).

2. `[[Raw LLM Name]]` links whose exact casing/spacing doesn't match any
   existing page, but whose *slug* does (e.g. "[[KIMI K3]]" when
   kimi-k3.md exists) — rewritten to "[[kimi-k3|KIMI K3]]" so the link
   actually resolves while keeping the readable name.

Links that don't resolve even after slugifying (an entity was mentioned
but never got a page) are left untouched — that's a separate, later
backlog item (entities.yaml / canonical promotion), not this fix.

AGENTS.md hard rule 1: agents must never touch the vault directly. This
script is tested against tests/fixtures/ only; run it yourself against
the real vault path from config/settings.yaml.

Usage:
    python scripts/fix_legacy_entity_wikilinks.py --vault <path> [--apply]
"""

import argparse
import re
from pathlib import Path

from personalkm.ingest.llm_summarizer import _slugify

# Bare wikilink only (no existing |alias) — don't touch already-fixed links.
_BARE_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)\]\]")


def collect_existing_slugs(wiki_root: Path) -> set[str]:
    slugs = set()
    for sub in ("entities", "concepts"):
        d = wiki_root / sub
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            slugs.add(f.stem.lower())
    return slugs


def fix_body(content: str, existing_slugs: set[str]) -> tuple[str, dict]:
    """Repair bare wikilinks in *content*. Returns (new_content, stats)."""
    stats = {"topic_removed": 0, "relinked": 0}

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        matches = list(_BARE_WIKILINK_RE.finditer(line))
        if not matches:
            new_lines.append(line)
            continue

        # A line that is only a bullet wrapping one topic-* link gets
        # dropped entirely rather than left as an empty bullet.
        stripped = line.strip()
        if (
            len(matches) == 1
            and stripped.startswith("- ")
            and stripped == f"- [[{matches[0].group(1)}]]"
            and matches[0].group(1).startswith("topic-")
        ):
            stats["topic_removed"] += 1
            continue

        def replace(m: re.Match) -> str:
            target = m.group(1)
            if target.startswith("topic-"):
                stats["topic_removed"] += 1
                return target[len("topic-"):]  # unwrap to plain text, drop the link markup
            if target.lower() in existing_slugs:
                return m.group(0)  # already resolves, leave as-is
            slug = _slugify(target)
            if slug and slug in existing_slugs:
                stats["relinked"] += 1
                if slug == target.lower():
                    return f"[[{slug}]]"
                return f"[[{slug}|{target}]]"
            return m.group(0)  # no matching page even after slugifying

        new_lines.append(_BARE_WIKILINK_RE.sub(replace, line))

    return "\n".join(new_lines), stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Path to the vault root (contains wiki/)")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run preview)")
    args = parser.parse_args()

    wiki_root = Path(args.vault) / "wiki"
    if not wiki_root.exists():
        raise SystemExit(f"No wiki/ directory under {args.vault}")

    existing_slugs = collect_existing_slugs(wiki_root)
    print(f"Loaded {len(existing_slugs)} existing entity/concept slugs")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")

    total = {"files_changed": 0, "topic_removed": 0, "relinked": 0}
    for sub in ("entities", "concepts"):
        d = wiki_root / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            new_content, stats = fix_body(content, existing_slugs)
            if new_content != content:
                total["files_changed"] += 1
                total["topic_removed"] += stats["topic_removed"]
                total["relinked"] += stats["relinked"]
                print(f"  [{'FIXED' if args.apply else 'WOULD FIX'}] {f.relative_to(wiki_root)}: "
                      f"{stats['topic_removed']} topic-* removed, {stats['relinked']} relinked")
                if args.apply:
                    f.write_text(new_content, encoding="utf-8")

    print(f"\nFiles changed: {total['files_changed']}")
    print(f"topic-* links removed: {total['topic_removed']}")
    print(f"Links relinked by slug: {total['relinked']}")
    if not args.apply:
        print("\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
