#!/usr/bin/env python3
"""
One-time backfill: run the "1 source → N pages" propagation
(P5#14, `_propagate_to_entity_pages()`) over EXISTING wiki pages
(IMPROVEMENT-BACKLOG.md P6#19).

The propagation mechanism only came online 2026-07-19, so pages created
before then never cross-pollinated: a page mentioning claude-code never
delivered its excerpt to claude-code.md's ## Captures. This script replays
the propagation for every existing entities/ + concepts/ page.

Only additive: `_propagate_to_entity_pages()` is idempotent (it skips a
target that already carries a `### <source-stem> (...)` capture heading),
so re-running is safe and existing content is never overwritten.

The excerpt is taken from the source page's body with markdown headers
dropped (a wiki page body starts with "## Summary", which would otherwise
be embedded as literal text inside the excerpt).

AGENTS.md hard rule 1: agents must never touch the vault directly. Tested
against fixtures only; run it yourself against the real vault (dry-run is
the default; --apply writes).

Usage:
    python scripts/backfill_propagation.py --vault <path> [--apply]
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from personalkm.frontmatter import split_frontmatter
from personalkm.ingest.ingestion_v2 import _propagate_to_entity_pages
from personalkm.ingest.llm_summarizer import detect_entity_mentions


def excerpt_body(body: str) -> str:
    """Body with markdown heading lines removed, for excerpt extraction."""
    return "\n".join(
        line for line in body.split("\n") if not line.lstrip().startswith("#")
    ).strip()


def plan_backfill(wiki: Path) -> list[tuple[Path, list[str], str]]:
    """Return (source_page, target_slugs, excerpt_source_body) for every
    page whose mentions resolve to at least one OTHER existing page."""
    pages = [
        f for sub in ("entities", "concepts")
        for f in sorted((wiki / sub).glob("*.md"))
        if (wiki / sub).exists()
    ]
    existing_slugs = {f.stem for f in pages}

    plan = []
    for page in pages:
        _, body = split_frontmatter(page.read_text(encoding="utf-8"))
        if not body.strip():
            continue
        detected = detect_entity_mentions(body)
        targets = [s for s in detected if s in existing_slugs and s != page.stem]
        if targets:
            plan.append((page, targets, excerpt_body(body)))
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    wiki = Path(args.vault) / "wiki"
    if not wiki.exists():
        raise SystemExit(f"No wiki/ under {args.vault}")

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")

    plan = plan_backfill(wiki)
    incoming: Counter[str] = Counter()
    for _, targets, _ in plan:
        incoming.update(targets)

    total_appends = 0
    for page, targets, clean_body in plan:
        if args.apply:
            appended = _propagate_to_entity_pages(
                wiki, page, targets, raw_path=None, body=clean_body
            )
            total_appends += appended
            if appended:
                print(f"  [APPLIED] {page.stem[:60]}: {appended} target(s)")
        else:
            print(f"  [WOULD PROPAGATE] {page.stem[:60]} → {', '.join(targets[:6])}"
                  + (" …" if len(targets) > 6 else ""))

    print(f"\nSource pages with resolvable mentions: {len(plan)}")
    print(f"Planned propagation edges: {sum(len(t) for _, t, _ in plan)}")
    if args.apply:
        print(f"Actual appends written (idempotency-filtered): {total_appends}")
    print("\nTop incoming targets (hub pages that will grow):")
    for slug, n in incoming.most_common(10):
        print(f"  {n:4d} ← {slug}")
    if not args.apply:
        print("\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
