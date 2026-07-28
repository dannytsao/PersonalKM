#!/usr/bin/env python3
"""
Phase C: Entity Distillation Loop — cron entry point
=====================================================
Non-interactive runner for the Entity Distillation Loop. Called by
``run_mac_mini_distill.sh`` via launchd. Scans wiki/entities/ and
wiki/concepts/ for pages that trigger distillation (>=5 captures or
>=30 days since last_distilled/created), generates an LLM summary, and
writes it back using fold-preserve retention (nothing is ever deleted).

P6#24 (2026-07-27): connects the dry-run-validated distill.py to the
Mac Mini cron schedule. All prerequisites met:
  - #17 over-detection fix ✅
  - #21 LLM merge routing ✅
  - #22 Phase B router migration ✅ (wikilink_analysis stage exists)
  - #23 decay_score_threshold formally omitted ✅

Design decisions:
- **Auto-apply, no per-page confirmation**: this is cron, nobody is
  watching. Fold-preserve retention makes this safe — the entire
  original body is kept verbatim in a collapsed <details> block.
- **Per-run page limit**: distillation is expensive (LLM call per page).
  Default limit=5 to keep each run under ~10 minutes. Pages that aren't
  reached this run will be picked up next run.
- **LLMError handling**: if the LLM call fails for a page (all models
  exhausted), that page is skipped for this run and logged. It will be
  retried next run. The router's alert mechanism (P0#3) handles notification.
- **Git commit + push**: distilled pages are committed with a descriptive
  message and pushed to origin/main.

Usage:
    python scripts/distill_cron.py [--vault /path/to/vault] [--limit 5] [--dry-run]
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("phase_c")


def run_git(args: list[str], cwd: Path) -> str:
    import subprocess
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "PhaseC-Distill"
    env["GIT_AUTHOR_EMAIL"] = "phase-c@local"
    env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
    env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        check=True,
        capture_output=True,
    )
    return result.stdout.strip()


def run_distill(
    vault_root: Path,
    limit: int = 5,
    dry_run: bool = False,
) -> dict:
    """
    Main Phase C entry point.

    Args:
        vault_root: Path to the vault (contains wiki/ subfolder)
        limit: Max pages to distill per run (0 = unlimited)
        dry_run: If True, scan and preview but don't write

    Returns summary dict.
    """
    start_time = time.time()
    wiki_path = vault_root / "wiki"

    logger.info("=" * 70)
    logger.info("PHASE C: Entity Distillation Loop")
    logger.info(f"VAULT: {vault_root}")
    logger.info(f"MODE: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"LIMIT: {limit if limit > 0 else 'unlimited'} pages")
    logger.info("=" * 70)

    if not wiki_path.exists():
        logger.error(f"wiki/ not found at {wiki_path}")
        return {"status": "error", "pages_distilled": 0, "message": "wiki/ not found"}

    # Step 1: Git sync (if not dry-run)
    if not dry_run:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        try:
            from personalkm.gitstate import ensure_clean_git_state
            repaired = ensure_clean_git_state(vault_root, "main")
            if repaired:
                logger.warning(f"Repaired stranded git state: {repaired}")
        except RuntimeError as e:
            logger.error(f"Vault git state stranded: {e}")
            return {"status": "error", "pages_distilled": 0,
                    "message": f"stranded git state: {e}"}
        except Exception as e:
            logger.warning(f"Git state check failed (continuing): {e}")

        try:
            logger.info("Syncing from GitHub...")
            run_git(["fetch", "origin", "main"], vault_root)
            run_git(["pull", "--ff-only", "origin", "main"], vault_root)
            logger.info("Git sync done.")
        except Exception as e:
            logger.warning(f"Git sync failed (continuing anyway): {e}")

    # Step 2: Scan for candidates
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from personalkm.propagate.distill import scan_for_candidates, apply_distillation

    logger.info("Scanning for distillation candidates...")
    previews = scan_for_candidates(wiki_path, call_llm=True)
    logger.info(f"Found {len(previews)} pages that trigger distillation.")

    if not previews:
        logger.info("Nothing to distill — all caught up!")
        return {"status": "success", "pages_distilled": 0, "duration_seconds": time.time() - start_time}

    # Step 3: Apply limit
    if limit > 0 and len(previews) > limit:
        logger.info(f"Limiting to {limit} pages (of {len(previews)} candidates)")
        previews = previews[:limit]

    # Step 4: Distill each page
    written = 0
    skipped = 0
    errors = 0

    for p in previews:
        rel_path = p.path.relative_to(vault_root)
        logger.info(f"Processing: {rel_path} (captures={p.captures_count})")

        if p.error:
            logger.warning(f"  Skipping {rel_path}: LLM error: {p.error}")
            errors += 1
            skipped += 1
            continue

        if not p.proposed_summary:
            logger.warning(f"  Skipping {rel_path}: no summary generated")
            skipped += 1
            continue

        if dry_run:
            logger.info(f"  [DRY RUN] Would distill: {p.proposed_summary[:100]}...")
            continue

        try:
            success = apply_distillation(p.path, p)
            if success:
                logger.info(f"  ✅ Distilled: {rel_path}")
                written += 1
            else:
                logger.warning(f"  ⚠️ apply_distillation returned False for {rel_path}")
                skipped += 1
        except Exception as e:
            logger.exception(f"  ❌ Failed to distill {rel_path}: {e}")
            errors += 1
            skipped += 1

    # Step 5: Git commit + push
    if not dry_run and written > 0:
        try:
            logger.info(f"Committing {written} distilled pages...")
            run_git(["add", "-A"], vault_root)
            status = run_git(["status", "--porcelain"], vault_root)
            if status:
                run_git(
                    ["commit", "-m",
                     f"Phase C: distill {written} entity/concept pages "
                     f"(fold-preserve, {errors} errors)"],
                    vault_root,
                )
                run_git(["push", "origin", "main"], vault_root)
                logger.info("✅ Phase C changes pushed to GitHub")
            else:
                logger.info("No changes to commit")
        except Exception as e:
            logger.warning(f"Git commit/push failed (non-critical): {e}")

    duration = time.time() - start_time
    logger.info("=" * 70)
    logger.info("PHASE C RESULTS")
    logger.info(f"  Pages distilled: {written}")
    logger.info(f"  Pages skipped: {skipped}")
    logger.info(f"  Errors: {errors}")
    logger.info(f"  Duration: {duration:.1f}s")
    logger.info("=" * 70)

    return {
        "status": "success",
        "pages_distilled": written,
        "pages_skipped": skipped,
        "errors": errors,
        "duration_seconds": duration,
    }


if __name__ == "__main__":
    VAULT_DEFAULT = Path(os.getenv(
        "VAULT_PATH", str(Path.home() / "Documents/PersonalKM/Personalkm-vault")
    ))

    parser = argparse.ArgumentParser(description="Phase C: Entity Distillation Loop (cron)")
    parser.add_argument("--vault", default=str(VAULT_DEFAULT), help="Vault root path")
    parser.add_argument("--limit", type=int, default=5,
                        help="Max pages to distill per run (0 = unlimited, default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan and preview but don't write changes")
    args = parser.parse_args()

    vault_root = Path(args.vault).expanduser()
    result = run_distill(vault_root, limit=args.limit, dry_run=args.dry_run)

    if result.get("status") == "error":
        sys.exit(1)
    else:
        sys.exit(0)
