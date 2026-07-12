"""Resolver orchestrator: run all adapters against raw notes.

Scans ``vault/raw/`` for notes with URLs, fetches actual content,
and stores it in a ``resolved/`` mirror directory alongside ``raw/``.

Also creates stub wiki pages for content that cannot be fetched
(auth walls, dead links, or exhausted retries).

Design (SPEC.md § 第二層 Resolve):

    vault/
      raw/Tech/note.md       ← original capture (immutable)
      resolved/Tech/note.md  ← fetched content (created by this module)

Only notes with a resolved content file proceed to LLM synthesis
with full context. Notes without resolvable URLs are skipped silently.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.personalkm.resolve.adapters import (
    GitHubAdapter,
    GenericAdapter,
    JinaAdapter,
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
    JinaAdapter(),   # Threads/IG/FB via Jina AI Reader (handles JS rendering)
    GenericAdapter(),  # catch-all — must be last
]

# Frontmatter for stub wiki pages
_STUB_TEMPLATE = """---
title: {title}
created: {date}
updated: {date}
stub: true
source: {url}
status: {status}
---

## {title}

This page is a **stub** — the linked content could not be automatically fetched.

**URL:** [{url}]({url})

**Status:** {status_label}

{note}

---

*This stub was automatically created by the Resolver. If you have access to the
content, please edit this page with the relevant information.*
"""

_STUB_LABELS = {
    "auth_required": "Authentication Required",
    "dead": "Content No Longer Available",
    "failed_final": "Content Fetch Failed (retries exhausted)",
}

_STUB_NOTES = {
    "auth_required": (
        "The website requires login or blocks automated access "
        "(Instagram, Threads, paywalls, etc.). "
        "If you can access the content, paste the key information here manually."
    ),
    "dead": (
        "The URL returned a 404 or 410 response — the content no longer exists "
        "at this address. The URL and your original note are preserved for reference."
    ),
    "failed_final": (
        "The resolver exhausted all retries without successfully fetching the content. "
        "This could be a temporary network issue or a persistent problem. "
        "The URL and your original note are preserved for reference."
    ),
}


def resolve_raw_notes(
    vault_path: Path,
    max_files: Optional[int] = None,
) -> dict:
    """Scan raw/ for unresolved notes and fetch their content.

    Args:
        vault_path: Root of the vault (contains raw/, wiki/, etc.)
        max_files: If set, only process the first N unresolved files.

    Returns:
        dict with keys: status, total, resolved, skipped, stubs, errors
    """
    raw_dir = vault_path / "raw"
    resolved_dir = vault_path / "resolved"
    wiki_dir = vault_path / "wiki"
    stubs_dir = wiki_dir / "stubs"

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
        total = len(unresolved)
        # Don't slice — process all files but stop after resolving `max_files`.
        # This way we skip social media (no adapter) and actually resolve
        # GitHub/YouTube/article notes.
    else:
        total = len(unresolved)

    resolved = 0
    skipped = 0
    stubs = 0
    errors = 0
    resolve_target = max_files if max_files is not None else None

    for raw_path in unresolved:
        if resolve_target is not None and resolved >= resolve_target:
            logger.info("Reached resolve limit (%d), stopping", resolve_target)
            break
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
            logger.info("  📄 Creating stub for unresolvable URL: %s", url)
            _create_stub(stubs_dir, rel, url, "auth_required", raw_path=raw_path)
            stubs += 1
            continue

        try:
            content = adapter.fetch(url)
        except AuthWallError:
            logger.info("  🔒 Auth wall: %s (%s)", url, rel)
            _create_stub(stubs_dir, rel, url, "auth_required", raw_path=raw_path)
            stubs += 1
            continue
        except GoneError:
            logger.info("  💀 Gone: %s (%s)", url, rel)
            _create_stub(stubs_dir, rel, url, "dead", raw_path=raw_path)
            stubs += 1
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
        "stubs": stubs,
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


def _create_stub(
    stubs_dir: Path,
    rel: Path,
    url: str,
    status: str,
    raw_path: Path | None = None,
) -> None:
    """Create a stub wiki page for an unfetchable URL.

    Preserves the original raw note content in the body so the stub
    is useful even without fetched article text.

    Args:
        stubs_dir: ``wiki/stubs/`` directory
        rel: Relative path of the raw note (used for the stub filename)
        url: The URL that couldn't be fetched
        status: One of ``auth_required``, ``dead``, ``failed_final``
        raw_path: Path to the original raw note (for preserving content)
    """
    label = _STUB_LABELS.get(status, status)
    note = _STUB_NOTES.get(status, "")
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Derive a title from the raw note filename
    title = _stub_title_from_rel(rel)

    # Include original raw note content if available
    raw_content = ""
    if raw_path and raw_path.exists():
        try:
            raw_text = raw_path.read_text(encoding="utf-8")
            # Strip frontmatter for cleaner display
            import re as _re
            raw_content = _re.sub(r"^---.*?---\n*", "", raw_text, flags=_re.DOTALL).strip()
            if raw_content:
                note = f"{note}\n\n## 原始筆記 (Raw Capture)\n\n{raw_content[:2000]}"
        except Exception:
            pass

    content = _STUB_TEMPLATE.format(
        title=title,
        date=date,
        url=url,
        status=status,
        status_label=label,
        note=note,
    )

    stub_path = stubs_dir / rel
    stub_path.parent.mkdir(parents=True, exist_ok=True)
    stub_path.write_text(content, encoding="utf-8")
    logger.info("  📄 Stub created: %s (%s)", stub_path, status)


def _stub_title_from_rel(rel: Path) -> str:
    """Derive a human-readable title from a raw note relative path.

    Examples:
        ``Tech/2026-07-05-github-something.md`` → ``Github Something``
        ``Food/some-restaurant.md`` → ``Some Restaurant``
    """
    stem = rel.stem
    # Strip date prefix
    import re as _re

    stem = _re.sub(r"^\d{4}-\d{2}-\d{2}[-_]", "", stem)
    stem = _re.sub(r"^[\d_]+-", "", stem)
    # Replace separators with spaces
    stem = stem.replace("-", " ").replace("_", " ")
    # Title case
    return stem.strip().title() or "Untitled"