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


# ─────────────────────────────────────────────────────────────
# Main Phase A logic
# ─────────────────────────────────────────────────────────────

def run_phase_a(vault_path: Path) -> dict:
    """
    Pull latest from GitHub, run ingest_raw_to_wiki, push wiki/ changes.
    Returns a result dict.
    """
    # Add repo root to sys.path so 'bot' package is importable
    repo_root = Path(__file__).parent.parent.resolve()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Pull latest so we have all raw files that Render/Render cron pushed
    try:
        run_git(["pull", "--rebase", "origin", "main"], vault_path)
        logger.info("Pulled latest from GitHub")
    except Exception as e:
        logger.warning(f"git pull failed (may be up-to-date): {e}")

    # Run ingestion
    from bot.ingestion_v2 import ingest_raw_to_wiki
    result = ingest_raw_to_wiki(vault_path)

    processed = result.get("processed", 0)
    failed = result.get("failed", 0)
    status = result.get("status", "unknown")

    logger.info(f"Phase A complete: status={status}, processed={processed}, failed={failed}")

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
    result = run_phase_a(vault_path)
    logger.info(f"Result: {result}")
