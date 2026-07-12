#!/usr/bin/env python3
"""
Phase A: Ingest Raw → Wiki Entities
=====================================
Runs on Mac Mini via launchd. Processes all files in vault_path/raw/ that
haven't been ingested yet, extracts topics/tags/summaries using the LLM,
writes wiki/entities/ or wiki/concepts/ pages, and pushes to GitHub.

Design goals:
- Idempotent: safely re-run without duplicating work
- Offline-resilient: Mac Mini sleep/wake is handled gracefully
- Catch-up: syncs from GitHub on each run, processes all unprocessed raw files

Usage:
    python scripts/ingest_wiki.py [--dry-run] [--limit N]

Exit Conditions:
    # New wiki entity created:
    ls wiki/entities/ | grep <topic-from-raw-filename>

    # GitHub has a new commit with wiki/ changes:
    git log --oneline -1  # message: "🤖 Auto: ingest raw → wiki entities"
"""
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────

VAULT_ROOT = Path(os.getenv("VAULT_PATH", str(Path.home() / "Documents/PersonalKM/Personalkm-vault")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("phase_a")


# ─────────────────────────────────────────────────────────────
# Git helpers (same pattern as bot/git_store.py)
# ─────────────────────────────────────────────────────────────

def run_git(args: list[str], cwd: Path) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "PhaseA-Ingest"
    env["GIT_AUTHOR_EMAIL"] = "phase-a@local"
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


def _commit_and_push_wiki(vault_path: Path) -> None:
    """
    Commit and push any wiki/ changes created by ingest_raw_to_wiki().
    """
    wiki_path = vault_path / "wiki"

    # Check if there are any changes in wiki/
    status = run_git(["status", "--porcelain", "wiki/"], vault_path)
    if not status.strip():
        logger.debug("No wiki changes to commit")
        return

    run_git(["add", "--all"], vault_path)
    run_git(["commit", "-m", "🤖 Auto: ingest raw → wiki entities"], vault_path)
    run_git(["push", "origin", "main"], vault_path)
    logger.info("Pushed wiki/ changes to GitHub")


def _append_to_log(
    vault_path: Path,
    *,
    resolver_resolved: int = 0,
    resolver_skipped: int = 0,
    resolver_stubs: int = 0,
    resolver_errors: int = 0,
    processed: int = 0,
    failed: int = 0,
    status: str = "unknown",
    results: list | None = None,  # per-file results from ingest
) -> None:
    """Append a Phase A run summary to vault/wiki/log.md."""
    from datetime import datetime, timezone

    log_path = vault_path / "wiki" / "log.md"
    now = datetime.now(timezone.utc).astimezone()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    # Build the log entry
    parts = [
        f"\n## [{date_str} {time_str}] phase-a | Resolver + Ingest run",
        f"- Resolver: {resolver_resolved} resolved, {resolver_stubs} stubs, {resolver_errors} errors, {resolver_skipped} skipped",
        f"- Ingest: {processed} processed, {failed} failed",
        f"- Status: {status}",
    ]

    # Add per-file details
    if results:
        parts.append("")
        for r in results:
            fname = r.get("file", "?")
            rstatus = r.get("status", "?")
            action = r.get("action", "")
            if rstatus == "success":
                page = r.get("page_path", "")
                parts.append(f"  ✅ {fname} → {page}")
            elif rstatus == "skipped":
                reason = r.get("reason", "")
                parts.append(f"  ⏭️ {fname} ({reason})")
            elif rstatus == "trashed":
                reason = r.get("reason", "")
                parts.append(f"  🗑️ {fname} ({reason})")
            else:
                parts.append(f"  ❌ {fname} ({rstatus})")
        parts.append("")

    entry = "\n".join(parts) + "\n"

    # Ensure log file exists with header
    if not log_path.exists():
        log_path.write_text(
            f"# Wiki Log\n\n"
            f"> Chronological record of all wiki actions. Append-only.\n"
            f"> Format: `## [YYYY-MM-DD] action | subject`\n"
            f"> Actions: ingest, update, query, lint, create, archive, delete\n"
            f"> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.\n"
            f"{entry}",
            encoding="utf-8",
        )
    else:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)

    logger.info("Appended run summary to wiki/log.md")


# ─────────────────────────────────────────────────────────────
# Main Phase A logic
# ─────────────────────────────────────────────────────────────

def run_phase_a(vault_path: Path, max_files: Optional[int] = None, dry_run: bool = False) -> dict:
    """
    Pull latest from GitHub, run ingest_raw_to_wiki, push wiki/ changes.

    Args:
        vault_path: root of the vault
        max_files: if set and > 0, only process the first N raw files
        dry_run: if True, list what would be processed and exit without
                 calling the LLM, writing files, or pushing.
    Returns a result dict.
    """
    # Add repo root and src/ to sys.path (Mac Mini uses /usr/bin/python3, no editable install)
    repo_root = Path(__file__).parent.parent.resolve()
    for p in [str(repo_root), str(repo_root / "src")]:
        if p not in sys.path:
            sys.path.insert(0, p)

    # Dry run: just enumerate the raw files that would be processed.
    if dry_run:
        raw_files = sorted((vault_path / "raw").glob("**/*.md"))
        if max_files is not None and max_files > 0:
            raw_files = raw_files[:max_files]
        logger.info(f"DRY RUN: would process {len(raw_files)} raw file(s):")
        for f in raw_files:
            logger.info(f"  - {f.relative_to(vault_path)}")
        return {"status": "dry_run", "would_process": len(raw_files),
                "files": [str(f.relative_to(vault_path)) for f in raw_files]}

    # Pull latest so we have all raw files that Render/Render cron pushed
    try:
        run_git(["pull", "--rebase", "origin", "main"], vault_path)
        logger.info("Pulled latest from GitHub")
    except Exception as e:
        logger.warning(f"git pull failed (may be up-to-date): {e}")

    # Step 0: Resolver — fetch external content for raw notes with URLs
    # Runs before ingest so LLM gets full article content, not just snippets.
    logger.info("🚀 Resolver: Fetching external content...")
    try:
        from personalkm.resolve import resolve_raw_notes

        resolver_result = resolve_raw_notes(vault_path, max_files=max_files)
        resolver_status = resolver_result.get("status", "error")
        resolver_resolved = resolver_result.get("resolved", 0)
        logger.info(
            "Resolver complete: status=%s, resolved=%d",
            resolver_status,
            resolver_resolved,
        )
    except Exception as e:
        logger.warning(f"Resolver step failed (non-fatal): {e}")

    # Run ingestion
    from bot.ingestion_v2 import ingest_raw_to_wiki
    result = ingest_raw_to_wiki(vault_path, max_files=max_files)

    processed = result.get("processed", 0)
    failed = result.get("failed", 0)
    status = result.get("status", "unknown")

    logger.info(f"Phase A complete: status={status}, processed={processed}, failed={failed}")

    # Append run summary to vault/wiki/log.md
    try:
        resolver_resolved = locals().get("resolver_result", {}).get("resolved", 0)
        resolver_skipped = locals().get("resolver_result", {}).get("skipped", 0)
        resolver_stubs = locals().get("resolver_result", {}).get("stubs", 0)
        resolver_errors = locals().get("resolver_result", {}).get("errors", 0)
        _append_to_log(
            vault_path,
            resolver_resolved=resolver_resolved,
            resolver_skipped=resolver_skipped,
            resolver_stubs=resolver_stubs,
            resolver_errors=resolver_errors,
            processed=processed,
            failed=failed,
            status=status,
            results=result.get("results", []),
        )
    except Exception as e:
        logger.warning(f"Failed to append to log: {e}")

    # Push wiki entities if any were created
    if processed > 0:
        try:
            _commit_and_push_wiki(vault_path)
        except Exception as e:
            logger.warning(f"Phase A: failed to push wiki changes: {e}")

    return result


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase A: Ingest raw files into wiki/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--limit", type=int, default=0, help="Max files to process (0 = all)")
    parser.add_argument("--vault", default=str(VAULT_ROOT), help=f"Vault root (default: {VAULT_ROOT})")
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()

    if not vault_path.exists():
        logger.error(f"Vault does not exist: {vault_path}")
        sys.exit(1)

    logger.info(f"Starting Phase A ingestion for vault: {vault_path}")
    result = run_phase_a(vault_path, max_files=args.limit or None, dry_run=args.dry_run)
    logger.info(f"Result: {result}")
