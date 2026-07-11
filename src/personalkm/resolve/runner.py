"""Resolver orchestrator: run all adapters against raw notes.

Scans ``vault/raw/`` for notes with URLs, fetches actual content,
and stores it in a ``resolved/`` mirror directory alongside ``raw/``.

Design (SPEC.md § 第二層 Resolve):

    vault/
      raw/Tech/note.md       ← original capture (immutable)
      resolved/Tech/note.md  ← fetched content (created by this module)

Only notes with a resolved content file proceed to LLM synthesis
with full context. Notes without resolvable URLs are skipped silently.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.personalkm.resolve.adapters import (
    GitHubAdapter,
    GenericAdapter,
    YouTubeAdapter,
    classify_url,
)
from src.personalkm.resolve.adapters.base import (
    AuthWallError,
    GoneError,
)
from src.personalkm.resolve.url_extractor import extract_url

logger = logging.getLogger(__name__)

# Ordered by specificity — first match wins
_ADAPTERS = [
    YouTubeAdapter(),
    GitHubAdapter(),
    GenericAdapter(),  # catch-all — must be last
]


def resolve_raw_notes(
    vault_path: Path,
    max_files: Optional[int] = None,
) -> dict:
    """Scan raw/ for unresolved notes and fetch their content.

    Args:
        vault_path: Root of the vault (contains raw/, wiki/, etc.)
        max_files: If set, only process the first N unresolved files.

    Returns:
        dict with keys: total, resolved, skipped, errors
    """
    raw_dir = vault_path / "raw"
    resolved_dir = vault_path / "resolved"

    if not raw_dir.exists():
        return {"status": "error", "message": f"raw/ not found at {raw_dir}"}

    # Find all raw notes that don't have a resolved counterpart
    raw_files = sorted(raw_dir.glob("**/*.md"))
    unresolved = []

    for rf in raw_files:
        rel = rf.relative_to(raw_dir)
        resolved_path = resolved_dir / rel
        if not resolved_path.exists():
            unresolved.append(rf)

    logger.info(
        "Resolver: %d raw notes, %d unresolved",
        len(raw_files),
        len(unresolved),
    )

    if max_files is not None and max_files > 0:
        unresolved = unresolved[:max_files]

    total = len(unresolved)
    resolved = 0
    skipped = 0
    errors = 0

    for raw_path in unresolved:
        rel = raw_path.relative_to(raw_dir)
        resolved_path = resolved_dir / rel

        url = extract_url(raw_path)
        if not url:
            logger.debug("No URL in %s — skipping", rel)
            skipped += 1
            continue

        source_type = classify_url(url)
        logger.info("Resolving %s (%s): %s", rel, source_type, url)

        adapter = _find_adapter(url)
        if adapter is None:
            logger.warning("No adapter for %s (%s)", url, source_type)
            skipped += 1
            continue

        try:
            content = adapter.fetch(url)
        except AuthWallError:
            logger.info("  🔒 Auth wall: %s (%s)", url, rel)
            skipped += 1
            continue
        except GoneError:
            logger.info("  💀 Gone: %s (%s)", url, rel)
            skipped += 1
            continue
        except Exception:
            logger.exception("Error resolving %s: %s", rel, url)
            errors += 1
            continue

        # Save resolved content
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content.markdown, encoding="utf-8")
        resolved += 1
        logger.info(
            "  ✅ %s → %s (%d chars)",
            rel,
            content.source_type,
            len(content.markdown),
        )

    return {
        "status": "success" if errors == 0 else "partial",
        "total": total,
        "resolved": resolved,
        "skipped": skipped,
        "errors": errors,
    }


def get_resolved_content(raw_path: Path) -> str | None:
    """Return the fetched content for a raw note, if available.

    Args:
        raw_path: Path to the raw note under ``vault/raw/``.

    Returns:
        Resolved markdown content, or None if not yet resolved.
    """
    raw_dir = _find_raw_dir(raw_path)
    if raw_dir is None:
        return None

    resolved_dir = raw_dir.parent / "resolved"
    rel = raw_path.relative_to(raw_dir)
    resolved_path = resolved_dir / rel

    if resolved_path.exists():
        return resolved_path.read_text(encoding="utf-8")
    return None


def _find_adapter(url: str):
    """Return the first adapter that matches the URL, or None."""
    for adapter in _ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None


def _find_raw_dir(raw_path: Path) -> Path | None:
    """Walk up from a raw note path to find ``raw/`` directory."""
    for parent in [raw_path] + list(raw_path.parents):
        if parent.name == "raw":
            return parent
    return None