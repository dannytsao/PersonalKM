#!/usr/bin/env python3
"""
Sprint 4 — Historical Wikilink Graph Cleansing.

Scans all .md files in both vaults, finds ``[[stop-word]]`` patterns where
the slug matches a stop word AND does NOT correspond to a real wiki page,
then strips the brackets so the word stays in the text but no longer
pollutes the knowledge graph.

Usage::

    python scripts/clean_legacy_graph.py --dry-run   # preview only
    python scripts/clean_legacy_graph.py              # apply changes

Safe to re-run — already-clean files are not re-written.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load the stop-words module from the project
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from personalkm.propagate.stop_words import load_stop_words  # noqa: E402

# ── Config ─────────────────────────────────────────────────────────────────
HOME = Path.home()
TECH_VAULT = HOME / "Documents/PersonalKM/Personalkm-vault"
LIFE_VAULT = HOME / "Documents/PersonalKM/Personalkm-lifestyle-vault"
CONFIG_STOP_WORDS = (
    Path(__file__).resolve().parent.parent / "config" / "stop_words.txt"
)

WIKI_DIRS = ["wiki/concepts", "wiki/entities"]

# Regex: [[slug]] or [[slug|display text]]
# Group 1 = slug, Group 2 = display text (optional, capturing)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def _collect_existing_slugs(vault: Path) -> set[str]:
    """Build a set of known wiki page slugs (whitelist)."""
    slugs: set[str] = set()
    for wiki_dir in WIKI_DIRS:
        d = vault / wiki_dir
        if d.is_dir():
            for f in d.glob("*.md"):
                slugs.add(f.stem.lower())
    logger.debug("%s: %d existing wiki slugs", vault.name, len(slugs))
    return slugs


def clean_file(
    path: Path,
    stop_words: set[str],
    whitelist: set[str],
    dry_run: bool,
) -> int:
    """Strip [[brackets]] from stop-word links in one .md file.

    Returns number of replacements made.
    """
    original = path.read_text(encoding="utf-8")
    changed = 0

    def _replacer(m: re.Match) -> str:
        nonlocal changed
        slug = m.group(1).strip().lower()
        # Whitelist always wins
        if slug in whitelist:
            return m.group(0)  # keep as-is
        if slug in stop_words:
            changed += 1
            # Return just the display text or the slug itself, without brackets
            display = m.group(2) or m.group(1)
            return display
        return m.group(0)

    new_text = WIKILINK_RE.sub(_replacer, original)

    if changed == 0:
        return 0

    if dry_run:
        logger.info("[DRY-RUN] %s: would fix %d wikilinks", path.relative_to(Path.home()), changed)
        return changed

    path.write_text(new_text, encoding="utf-8")
    logger.info("%s: fixed %d wikilinks", path.relative_to(Path.home()), changed)
    return changed


def scan_vault(
    vault: Path,
    stop_words: set[str],
    existing_slugs: set[str],
    dry_run: bool,
) -> int:
    """Scan all .md files under wiki/ in one vault.

    Returns total replacements across the vault.
    """
    total = 0
    # Collect all existing slugs across both vaults for shared whitelist
    whitelist = existing_slugs | _collect_existing_slugs(vault)

    for wiki_dir in WIKI_DIRS:
        d = vault / wiki_dir
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            try:
                total += clean_file(f, stop_words, whitelist, dry_run)
            except Exception:
                logger.exception("Error processing %s", f)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean legacy wikilink graph noise")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    args = parser.parse_args()

    stop_words = load_stop_words(CONFIG_STOP_WORDS)
    logger.info("Loaded %d stop words", len(stop_words))

    # Build cross-vault whitelist (both vaults share the same entity universe)
    tech_slugs = _collect_existing_slugs(TECH_VAULT)
    life_slugs = _collect_existing_slugs(LIFE_VAULT)
    combined_whitelist = tech_slugs | life_slugs
    logger.info(
        "Combined whitelist: %d existing wiki slugs (tech=%d, lifestyle=%d)",
        len(combined_whitelist),
        len(tech_slugs),
        len(life_slugs),
    )

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    logger.info("=== Starting %s mode ===", mode)

    t_tech = scan_vault(TECH_VAULT, stop_words, combined_whitelist, args.dry_run)
    t_life = scan_vault(LIFE_VAULT, stop_words, combined_whitelist, args.dry_run)

    total = t_tech + t_life
    logger.info("=== Done: tech=%d, lifestyle=%d, total=%d ===", t_tech, t_life, total)

    if args.dry_run and total > 0:
        logger.info("Run without --dry-run to apply these changes.")
    elif total == 0:
        logger.info("No changes needed — graph is already clean.")


if __name__ == "__main__":
    main()