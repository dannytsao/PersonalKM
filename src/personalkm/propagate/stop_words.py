"""Stop-words filter for wikilink graph cleanup (Sprint 3, 2026-08-28).

Prevents generic/overly-common terms produced by Phase B (WikilinkAnalyzer)
from polluting the knowledge graph with meaningless ``[[node]]`` entries.

Usage::

    from personalkm.propagate.stop_words import filter_wikilinks, load_stop_words

    stop_words = load_stop_words()
    forward = filter_wikilinks(forward_links, stop_words, existing_slugs)
    backward = filter_wikilinks(backward_links, stop_words, existing_slugs)

Dual mechanism:
1. **Stop-word list** — matched slug is stripped of brackets (the word stays
   in the text, just not as a wikilink).
2. **Whitelist** — any slug that matches an existing entity/concept file is
   ALWAYS kept, regardless of stop-word membership.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_STOP_WORDS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "stop_words.txt"


def load_stop_words(path: str | Path | None = None) -> set[str]:
    """Load stop words from ``stop_words.txt``.

    Reads lines, strips comments (``#``) and whitespace, skips empty
    lines and section headers (``[...]``).

    Returns a set of lowercase stop-word slugs.
    """
    p = Path(path) if path else _DEFAULT_STOP_WORDS_PATH
    if not p.exists():
        logger.warning("stop_words.txt not found at %s — returning empty set", p)
        return set()

    words: set[str] = set()
    text = p.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        # Strip inline comments
        if "#" in line:
            line = line[: line.index("#")].strip()
        if not line:
            continue
        # Skip section headers
        if line.startswith("[") and line.endswith("]"):
            continue
        words.add(line.lower())

    logger.debug("Loaded %d stop words from %s", len(words), p)
    return words


def filter_wikilinks(
    slugs: list[str],
    stop_words: set[str],
    existing_slugs: set[str] | None = None,
) -> list[str]:
    """Filter a list of wikilink slugs.

    - Slugs matching an entry in ``existing_slugs`` (whitelist) are
      ALWAYS kept.
    - Other slugs that match a stop word are filtered out.

    Args:
        slugs: The raw slug list (e.g. ``["claude-code", "測試", "docker"]``).
        stop_words: Set of stop-word slugs from :func:`load_stop_words`.
        existing_slugs: Set of slugs that have real wiki pages. When
            provided, these are immune to stop-word filtering.

    Returns:
        Filtered slug list (order preserved).
    """
    if not slugs:
        return []

    whitelist = existing_slugs or set()
    filtered: list[str] = []
    dropped: list[str] = []

    for slug in slugs:
        slug_lower = slug.lower().strip()
        # Whitelist always wins
        if slug_lower in whitelist:
            filtered.append(slug)
        elif slug_lower in stop_words:
            dropped.append(slug)
        else:
            filtered.append(slug)

    if dropped:
        logger.debug("Filtered %d stop-word slugs: %s", len(dropped), dropped[:10])

    return filtered
