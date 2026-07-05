#!/usr/bin/env python3
"""
Phase B: Post-Link — Ollama Wikilink Analyzer
================================================
Runs on Mac Mini via launchd. Processes all wiki pages that need semantic
wikilinks added or refreshed, using Ollama (qwen3:8b) for bidirectional reasoning.

Design goals:
- Idempotent: safely re-run without duplicating work
- Offline-resilient: Mac Mini sleep/wake is handled gracefully
- Catch-up: syncs from GitHub on each run, processes all unprocessed pages

Usage:
    python scripts/post_link_ollama.py [--dry-run] [--limit N]

Exit Conditions:
    # Pages that had no wikilinks now have them:
    grep -c '\[\[' wiki/entities/new-page.md   # > 0

    # Older pages that should link to new ones have backlinks:
    grep 'new-page' wiki/entities/older-page.md   # Contains [[new-page]]
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────

VAULT_ROOT = Path(os.getenv("VAULT_PATH", str(Path.home() / ".personalkm/personalkm-vault")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("phase_b")


# ─────────────────────────────────────────────────────────────
# Git helpers (same pattern as bot/git_store.py)
# ─────────────────────────────────────────────────────────────

def run_git(args: list[str], cwd: Path) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "PhaseB-Wikilink"
    env["GIT_AUTHOR_EMAIL"] = "phase-b@local"
    env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
    env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]

    import subprocess
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        check=True,
        capture_output=True,
    )
    return result.stdout.strip()


# ─────────────────────────────────────────────────────────────
# YAML frontmatter helpers
# ─────────────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Split YAML frontmatter from body.
    Returns (frontmatter_dict, body_str).
    Returns ({}, content) if no frontmatter.
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1]
    body = parts[2]

    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")

    return fm, body


def has_frontmatter_key(content: str, key: str) -> bool:
    """Check if frontmatter contains a specific key."""
    if not content.startswith("---"):
        return False
    parts = content.split("---", 2)
    if len(parts) < 2:
        return False
    return any(
        line.strip().startswith(f"{key}:")
        for line in parts[1].split("\n")
    )


def get_frontmatter_value(content: str, key: str) -> Optional[str]:
    """Get a frontmatter value, or None if not present."""
    fm, _ = parse_frontmatter(content)
    return fm.get(key)


def set_frontmatter_value(content: str, key: str, value: str) -> str:
    """
    Set or update a frontmatter key=value pair.
    Creates frontmatter if missing.
    """
    if not content.startswith("---"):
        # Prepend frontmatter
        return f"""---
{key}: {value}
---

{content}"""

    parts = content.split("---", 2)
    if len(parts) < 3:
        return content

    fm_text = parts[1]
    body = parts[2]

    # Check if key already exists
    key_pattern = re.compile(rf"^{re.escape(key)}:\s*\S", re.MULTILINE)
    if key_pattern.search(fm_text):
        # Replace existing value
        fm_text = key_pattern.sub(f"{key}: {value}", fm_text)
    else:
        # Append to frontmatter
        fm_text = fm_text.rstrip() + f"\n{key}: {value}"

    return f"---\n{fm_text}\n---\n{body}"


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content, returning just the body."""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return parts[2]


def extract_title_from_frontmatter(content: str, fallback: str = "untitled") -> str:
    """Get title from frontmatter, with fallback."""
    val = get_frontmatter_value(content, "title")
    if val:
        return val
    # Try reading first meaningful heading from body
    body = strip_frontmatter(content)
    for line in body.split("\n")[:10]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


# ─────────────────────────────────────────────────────────────
# Page needs processing?
# ─────────────────────────────────────────────────────────────

def needs_processing(page_path: Path) -> bool:
    """
    Check if a wiki page needs Phase B wikilink processing.

    Returns True if ANY of these are true:
    - No `wikilink_processed` frontmatter key exists (never processed)
    - `updated` > `wikilink_processed` (page changed since last processing)
    """
    content = page_path.read_text(encoding="utf-8")

    if not has_frontmatter_key(content, "wikilink_processed"):
        return True

    updated = get_frontmatter_value(content, "updated")
    processed = get_frontmatter_value(content, "wikilink_processed")

    if not updated or not processed:
        return True

    try:
        updated_dt = datetime.strptime(updated, "%Y-%m-%d")
        processed_dt = datetime.strptime(processed, "%Y-%m-%dT%H:%M:%S")
        return updated_dt > processed_dt
    except ValueError:
        return True


def mark_processed(page_path: Path) -> None:
    """Set wikilink_processed timestamp on a page."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    content = page_path.read_text(encoding="utf-8")
    content = set_frontmatter_value(content, "wikilink_processed", timestamp)
    page_path.write_text(content, encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# Collect existing entity names (for Ollama context)
# ─────────────────────────────────────────────────────────────

def collect_entity_names(wiki_root: Path) -> list[str]:
    """
    Collect all entity file stems from wiki/entities/ and wiki/concepts/.
    Used as the existing-knowledge-base list for Ollama prompt.
    """
    names = []
    for subdir in ("entities", "concepts"):
        dir_path = wiki_root / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob("*.md"):
            if f.name in ("index.md", "log.md"):
                continue
            names.append(f.stem)
    return names


# ─────────────────────────────────────────────────────────────
# Wikilink writing helpers
# ─────────────────────────────────────────────────────────────

def resolve_slug_to_path(wiki_root: Path, slug: str) -> Optional[Path]:
    """Resolve a slug to an actual wiki page path, if it exists."""
    slug_lower = slug.lower()
    for subdir in ("entities", "concepts"):
        dir_path = wiki_root / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob("*.md"):
            if f.stem.lower() == slug_lower:
                return f
    return None


def ensure_wikilink_in_body(content: str, target_slug: str, wiki_root: Path) -> tuple[str, bool]:
    """
    Add [[target_slug]] to content body if not already present.
    Returns (new_content, was_added).
    """
    if f"[[{target_slug}]]" in content or f"[[{target_slug}|" in content:
        return content, False

    target_path = resolve_slug_to_path(wiki_root, target_slug)
    if target_path is None:
        return content, False

    # Find a good place: after the last paragraph of the body
    body = strip_frontmatter(content)
    lines = body.rstrip().split("\n")

    # Find last non-empty, non-heading line
    insert_idx = len(lines)
    for i in reversed(range(len(lines))):
        line = lines[i].strip()
        if line and not line.startswith("#"):
            insert_idx = i + 1
            break

    new_lines = lines[:insert_idx] + [f"- Related: [[{target_slug}]]"] + lines[insert_idx:]
    new_body = "\n".join(new_lines)

    if content.startswith("---"):
        parts = content.split("---", 2)
        new_content = f"---\n{parts[1]}\n---\n{new_body}"
    else:
        new_content = new_body

    return new_content, True


def add_backlink_to_target(
    wiki_root: Path,
    target_slug: str,
    source_page_name: str,
) -> bool:
    """
    Add [[source_page_name]] backlink to the target entity's See also section.
    Returns True if backlink was added.
    """
    target_path = resolve_slug_to_path(wiki_root, target_slug)
    if target_path is None:
        logger.debug(f"Cannot add backlink: target '{target_slug}' not found")
        return False

    if target_path.stem.lower() == source_page_name.lower():
        return False  # Don't self-link

    content = target_path.read_text(encoding="utf-8")
    if f"[[{source_page_name}]]" in content:
        return False  # Already has backlink

    body = strip_frontmatter(content)
    source_link = f"[[{source_page_name}]]"

    # Append to See also section or create it
    see_also_marker = "## See also"
    if see_also_marker in body:
        # Append to existing section
        lines = body.split("\n")
        for i in reversed(range(len(lines))):
            if lines[i].strip() and not lines[i].startswith("#"):
                lines.insert(i + 1, f"- {source_link}")
                body = "\n".join(lines)
                break
    else:
        body = body.rstrip() + f"\n\n{see_also_marker}\n\n- {source_link}\n"

    if content.startswith("---"):
        parts = content.split("---", 2)
        new_content = f"---\n{parts[1]}\n---\n{body}"
    else:
        new_content = body

    target_path.write_text(new_content, encoding="utf-8")
    logger.info(f"  ← Backlink added: {target_path.stem} → {source_page_name}")
    return True


# ─────────────────────────────────────────────────────────────
# Main Phase B processor
# ─────────────────────────────────────────────────────────────

def process_page(
    page_path: Path,
    wiki_root: Path,
    analyzer,
    all_entity_names: list[str],
    dry_run: bool = False,
) -> dict:
    """
    Run Phase B analysis on a single wiki page.

    Returns dict with keys: page, title, forward_added, backlinks_added,
                           parse_success, error
    """
    try:
        content = page_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"page": page_path.stem, "error": str(e)}

    page_title = extract_title_from_frontmatter(content, fallback=page_path.stem)
    body = strip_frontmatter(content)

    logger.info(f"  Analyzing: {page_path.stem} ({len(body)} chars)")

    result = analyzer.analyze_page(
        page_title=page_title,
        page_body=body,
        existing_entity_names=all_entity_names,
    )

    forward_links = result.get("forward_links", [])
    backward_links = result.get("backward_links", [])
    parse_success = result.get("parse_success", False)

    forward_added = 0
    if not dry_run and parse_success:
        for slug in forward_links:
            new_content, was_added = ensure_wikilink_in_body(content, slug, wiki_root)
            if was_added:
                content = new_content
                forward_added += 1

        page_path.write_text(content, encoding="utf-8")

    backlinks_added = 0
    if not dry_run and parse_success:
        for slug in backward_links:
            if add_backlink_to_target(wiki_root, slug, page_path.stem):
                backlinks_added += 1

        # Mark as processed (even if Ollama failed — don't retry forever)
        mark_processed(page_path)

    return {
        "page": page_path.stem,
        "forward_added": forward_added,
        "backlinks_added": backlinks_added,
        "parse_success": parse_success,
        "raw_output_preview": result.get("raw_output", "")[:200] if result.get("raw_output") else "",
    }


def run_phase_b(
    wiki_root: Path,
    dry_run: bool = False,
    limit: int = 0,
) -> dict:
    """
    Main Phase B entry point.

    Args:
        wiki_root: Path to the vault (contains wiki/ subfolder)
        dry_run: If True, analyze but don't write any changes
        limit: Max pages to process (0 = unlimited)

    Returns summary dict.
    """
    start_time = time.time()
    vault_root = wiki_root  # for git operations

    logger.info("=" * 70)
    logger.info("PHASE B: Post-Link via Ollama (qwen3:8b)")
    logger.info(f"WIKI ROOT: {wiki_root}")
    logger.info(f"MODE: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 70)

    # Step 1: Sync from GitHub
    if not dry_run:
        try:
            logger.info("Syncing from GitHub...")
            run_git(["fetch", "origin", "main"], vault_root)
            run_git(["pull", "--ff-only", "origin", "main"], vault_root)
            logger.info("Git sync done.")
        except Exception as e:
            logger.warning(f"Git sync failed (continuing anyway): {e}")

    # Step 2: Collect all wiki pages that need processing
    wiki_dir = wiki_root / "wiki"
    if not wiki_dir.exists():
        logger.error(f"wiki/ not found at {wiki_dir}")
        return {"status": "error", "pages_processed": 0, "message": "wiki/ not found"}

    all_pages = []
    for subdir in ("entities", "concepts"):
        dir_path = wiki_dir / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob("*.md"):
            if f.name in ("index.md", "log.md"):
                continue
            if needs_processing(f):
                all_pages.append(f)

    all_pages.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    logger.info(f"Pages needing processing: {len(all_pages)}")

    if not all_pages:
        logger.info("Nothing to process — all caught up!")
        return {"status": "success", "pages_processed": 0}

    # Apply limit
    if limit > 0:
        all_pages = all_pages[:limit]
        logger.info(f"Processing limited to {limit} pages")

    # Step 3: Collect existing entity names (once, for all pages)
    all_entity_names = collect_entity_names(wiki_dir)
    logger.info(f"Existing entities in knowledge base: {len(all_entity_names)}")

    # Step 4: Import and init Ollama analyzer
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from bot.ollama_wikilink import OllamaWikilinkAnalyzer

        analyzer = OllamaWikilinkAnalyzer()
        if not analyzer.is_available():
            logger.error("Ollama is not reachable at %s", analyzer.ollama_url)
            logger.error("Start Ollama: ollama serve")
            return {
                "status": "error",
                "pages_processed": 0,
                "message": "Ollama not available",
            }
        logger.info("Ollama connected: %s", analyzer.ollama_url)
    except Exception as e:
        logger.exception(f"Failed to initialize Ollama analyzer: {e}")
        return {
            "status": "error",
            "pages_processed": 0,
            "message": f"Ollama init failed: {e}",
        }

    # Step 5: Process each page
    results = []
    stats = {"pages": 0, "forward_added": 0, "backlinks_added": 0, "errors": 0}

    for page_path in all_pages:
        logger.info(f"Processing: {page_path.relative_to(wiki_dir)}")
        result = process_page(page_path, wiki_dir, analyzer, all_entity_names, dry_run=dry_run)
        results.append(result)

        if "error" in result and result["error"]:
            stats["errors"] += 1
        else:
            stats["pages"] += 1
            stats["forward_added"] += result.get("forward_added", 0)
            stats["backlinks_added"] += result.get("backlinks_added", 0)

    # Step 6: Git commit + push
    if not dry_run and (stats["forward_added"] > 0 or stats["backlinks_added"] > 0):
        try:
            logger.info("Committing Phase B changes...")
            run_git(["add", "-A"], vault_root)
            status = run_git(["status", "--porcelain"], vault_root)
            if status:
                run_git(["commit", "-m", f"Phase B: add wikilinks via Ollama ({stats['forward_added']} forward, {stats['backlinks_added']} backward)"], vault_root)
                run_git(["push", "origin", "main"], vault_root)
                logger.info("✅ Phase B changes pushed to GitHub")
            else:
                logger.info("No changes to commit")
        except Exception as e:
            logger.warning(f"Git commit/push failed (non-critical): {e}")

    duration = time.time() - start_time

    logger.info("=" * 70)
    logger.info("PHASE B RESULTS")
    logger.info(f"  Pages processed: {stats['pages']}")
    logger.info(f"  Forward links added: {stats['forward_added']}")
    logger.info(f"  Backlinks added: {stats['backlinks_added']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"  Duration: {duration:.1f}s")
    logger.info("=" * 70)

    return {
        "status": "success",
        "pages_processed": stats["pages"],
        "forward_added": stats["forward_added"],
        "backlinks_added": stats["backlinks_added"],
        "errors": stats["errors"],
        "duration_seconds": duration,
        "results": results,
    }


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase B: Ollama wikilink post-link processor")
    parser.add_argument("--dry-run", action="store_true", help="Analyze but don't write changes")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process (0 = all)")
    parser.add_argument("--wiki", default=str(VAULT_ROOT), help=f"Vault root path (default: {VAULT_ROOT})")
    args = parser.parse_args()

    wiki_root = Path(args.wiki)
    result = run_phase_b(wiki_root, dry_run=args.dry_run, limit=args.limit)

    if result.get("status") == "error":
        sys.exit(1)
    else:
        sys.exit(0)
