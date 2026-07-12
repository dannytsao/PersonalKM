#!/usr/bin/env python3
"""
Pipeline Quality Feedback Loop — Python Status Reporter
========================================================
CLI + importable module for PersonalKM pipeline health tracking.

Writes to ``~/.personalkm/status/pipeline.json`` — same location as the bash
status reporter. The two are designed to cooperate: bash writes basic phase-level
state (exit code, skip reason), Python enriches with detailed ingest results,
health checks, and blocker analysis.

CLI Usage:
    # Update status after a Phase A ingest run:
    python -m personalkm.pipeline_status ingest \\
        --processed 3 --failed 0 --skipped 7 --trashed 2 \\
        --health-status healthy

    # View current status (human-readable):
    python -m personalkm.pipeline_status check

    # View just the blockers:
    python -m personalkm.pipeline_status blockers

Python Usage:
    from personalkm.pipeline_status import (
        update_ingest_status, get_pipeline_status, get_blockers,
    )

    update_ingest_status(
        phase="A",
        processed=3, failed=0, skipped=7, trashed=2,
        health_status="healthy",
        errors=["Resolver timeout on youtube.com/xyz"],
    )
"""

from __future__ import annotations

import json
import os
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_DIR = Path(os.getenv("PERSONALKM_STATUS_DIR", Path.home() / ".personalkm" / "status"))
PIPELINE_FILE = STATUS_DIR / "pipeline.json"
HISTORY_FILE = STATUS_DIR / "run_history.jsonl"

# ──────────────────────────────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────────────────────────────

def _read_pipeline() -> dict[str, Any]:
    """Read current pipeline status JSON, returning {} if missing/corrupt."""
    if not PIPELINE_FILE.exists():
        return {}
    try:
        return json.loads(PIPELINE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_pipeline(data: dict[str, Any]) -> None:
    """Write pipeline status JSON atomically."""
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    PIPELINE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _append_history(entry: dict[str, Any]) -> None:
    """Append a JSONL line to the run history."""
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────────────────────────────
# Vault state analysis
# ──────────────────────────────────────────────────────────────────────

def _analyze_vault(vault_root: Path | None = None) -> dict[str, Any]:
    """Gather vault/repo health metrics."""
    if vault_root is None:
        vault_root = Path.home() / "Documents" / "PersonalKM" / "Personalkm-vault"

    state: dict[str, Any] = {
        "raw_unprocessed": 0,
        "raw_oldest_days": 0,
        "raw_breakdown": {"resolvable": 0, "threads": 0, "facebook": 0, "instagram": 0},
        "resolved_count": 0,
        "archive_count": 0,
        "dirty": False,
        "uncommitted_files": 0,
        "last_commit": "",
        "wiki_entities": 0,
        "wiki_concepts": 0,
    }

    if not vault_root.exists():
        return state

    # Git state
    git_dir = vault_root / ".git"
    if git_dir.exists():
        try:
            import subprocess

            def _git(*args: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(vault_root), *args],
                    capture_output=True, text=True, timeout=10,
                ).stdout.strip()

            state["last_commit"] = _git("log", "--oneline", "-1")
            status_out = _git("status", "--porcelain")
            if status_out:
                state["dirty"] = True
                state["uncommitted_files"] = len([l for l in status_out.split("\n") if l.strip()])
        except Exception:
            pass

    # Raw file analysis
    raw_dir = vault_root / "raw"
    if raw_dir.exists():
        raw_files = sorted(raw_dir.rglob("*.md"))
        state["raw_unprocessed"] = len(raw_files)
        for f in raw_files:
            name = f.name.lower()
            if "on-threads" in name or "threads" in name:
                state["raw_breakdown"]["threads"] += 1
            elif "facebook" in name or "fb.com" in name:
                state["raw_breakdown"]["facebook"] += 1
            elif "on-instagram" in name or "instagram" in name:
                state["raw_breakdown"]["instagram"] += 1
            else:
                state["raw_breakdown"]["resolvable"] += 1

        # Oldest file age
        if raw_files:
            try:
                oldest = min(f.stat().st_mtime for f in raw_files)
                state["raw_oldest_days"] = int((datetime.now().timestamp() - oldest) // 86400)
            except OSError:
                pass

    # Resolved
    resolved_dir = vault_root / "resolved"
    if resolved_dir.exists():
        state["resolved_count"] = len(list(resolved_dir.rglob("*.md")))

    # Archive
    archive_dir = vault_root / "Archive"
    if archive_dir.exists():
        state["archive_count"] = len(list(archive_dir.rglob("*.md")))

    # Wiki stats
    wiki_dir = vault_root / "wiki"
    if wiki_dir.exists():
        entities_dir = wiki_dir / "entities"
        concepts_dir = wiki_dir / "concepts"
        if entities_dir.exists():
            state["wiki_entities"] = len(list(entities_dir.glob("*.md")))
        if concepts_dir.exists():
            state["wiki_concepts"] = len(list(concepts_dir.glob("*.md")))

    return state


# ──────────────────────────────────────────────────────────────────────
# Blocker analysis
# ──────────────────────────────────────────────────────────────────────

def _analyze_blockers(pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive human-readable blockers from pipeline state."""
    blockers: list[dict[str, Any]] = []

    vault = pipeline.get("vault", {})
    phase_a = pipeline.get("phase_a", {})
    phase_b = pipeline.get("phase_b", {})

    # Vault dirty
    if vault.get("dirty"):
        n = vault.get("uncommitted_files", 0)
        blockers.append({
            "severity": "high",
            "phase": "all",
            "reason": f"Vault repo has {n} uncommitted change(s) — both phases will skip on next cron tick",
            "fix": "cd ~/Documents/PersonalKM/Personalkm-vault && git add --all && git commit -m 'chore: checkpoint' && git push",
        })

    # Phase A failures (not skip)
    if phase_a.get("status") in ("failed", "error"):
        detail = phase_a.get("detail", "")
        blockers.append({
            "severity": "high",
            "phase": "A",
            "reason": f"Phase A last run failed: {detail}",
            "fix": "Check ~/Library/Logs/PersonalKM/phase-a.err.log",
        })

    # Phase B failures
    if phase_b.get("status") in ("failed", "error"):
        detail = phase_b.get("detail", "")
        blockers.append({
            "severity": "high",
            "phase": "B",
            "reason": f"Phase B last run failed: {detail}",
            "fix": "Check ~/Library/Logs/PersonalKM/phase-b.err.log",
        })

    # Phase B skipped (vault dirty) but maybe it wasn't always running
    if phase_b.get("status") == "skipped" and phase_a.get("status") == "success":
        reason = phase_b.get("detail", "unknown")
        # If vault is the cause, don't double-report
        if "Ollama" in reason and not vault.get("dirty"):
            blockers.append({
                "severity": "high",
                "phase": "B",
                "reason": f"Phase B skipped: {reason}",
                "fix": "Run: ollama serve",
            })

    # Stale raw files
    raw_count = vault.get("raw_unprocessed", 0)
    raw_resolvable = vault.get("raw_breakdown", {}).get("resolvable", 0)
    raw_oldest = vault.get("raw_oldest_days", 0)
    if raw_resolvable > 0 and raw_oldest > 7:
        blockers.append({
            "severity": "medium",
            "phase": "A",
            "reason": f"{raw_resolvable} resolvable raw files have been unprocessed for {raw_oldest} days (out of {raw_count} total raw)",
            "fix": "Resolve vault dirty state first, then next cron tick will process them",
        })

    return blockers


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def get_pipeline_status() -> dict[str, Any]:
    """Return the full pipeline status dict."""
    return _read_pipeline()


def get_blockers() -> list[dict[str, Any]]:
    """Return derived blockers list (re-analyzes fresh)."""
    pipeline = _read_pipeline()
    return _analyze_blockers(pipeline)


def update_ingest_status(
    *,
    phase: str = "A",
    exit_code: int = 0,
    processed: int = 0,
    failed: int = 0,
    skipped: int = 0,
    trashed: int = 0,
    health_status: str = "unknown",
    errors: list[str] | None = None,
    detail: str = "",
) -> dict[str, Any]:
    """
    Update pipeline.json with detailed ingest results.

    Called from Python runners (ingest_wiki.py, post_link_ollama.py) after
    each run. Complements the bash-level status (exit code, skip reason) with
    per-run statistics.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    errors = errors or []

    # Determine overall status
    if exit_code != 0:
        status = "failed"
    elif failed > 0:
        status = "partial"
    elif processed > 0:
        status = "success"
    else:
        status = "idle"

    phase_key = f"phase_{phase.lower()}"

    pipeline = _read_pipeline()

    # Update phase-specific data
    pipeline[phase_key] = {
        "last_run": now,
        "exit_code": exit_code,
        "status": status,
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "trashed": trashed,
        "health_status": health_status,
        "errors": errors,
        "detail": detail,
    }

    # Update vault state
    vault_root = Path(os.getenv(
        "PERSONALKM_VAULT_ROOT",
        str(Path.home() / "Documents/PersonalKM/Personalkm-vault"),
    ))
    pipeline["vault"] = _analyze_vault(vault_root)

    # Analyze blockers
    pipeline["blockers"] = _analyze_blockers(pipeline)

    # Summary line
    parts = [f"Phase {phase}"]
    if processed:
        parts.append(f"{processed} processed")
    if failed:
        parts.append(f"{failed} failed")
    if skipped:
        parts.append(f"{skipped} skipped")
    if trashed:
        parts.append(f"{trashed} trashed")
    pipeline["summary"] = f"{status.upper()}: {' | '.join(parts)}"
    pipeline["overall_status"] = _overall_health(pipeline)
    pipeline["last_updated"] = now

    _write_pipeline(pipeline)

    # Append to history
    _append_history({
        "timestamp": now,
        "phase": phase_key,
        "exit_code": exit_code,
        "status": status,
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "blockers": pipeline["blockers"],
        "vault_dirty": pipeline.get("vault", {}).get("dirty", False),
    })

    return pipeline


def _overall_health(pipeline: dict[str, Any]) -> str:
    """Derive overall health from pipeline state."""
    blockers = pipeline.get("blockers", [])
    if any(b.get("severity") == "high" for b in blockers):
        return "degraded"
    if blockers:
        return "warning"
    return "healthy"


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

def _cmd_ingest(args: Namespace) -> None:
    """CLI: python -m personalkm.pipeline_status ingest ..."""
    result = update_ingest_status(
        phase=args.phase,
        exit_code=args.exit_code,
        processed=args.processed,
        failed=args.failed,
        skipped=args.skipped,
        trashed=args.trashed,
        health_status=args.health_status,
        errors=args.errors.split(",") if args.errors else [],
    )
    print(result.get("summary", "OK"))
    if result.get("blockers"):
        print(f"  ⚠️  {len(result['blockers'])} blocker(s)")
        for b in result["blockers"]:
            print(f"     [{b['severity']}] {b['reason']}")


def _cmd_check(_args: Namespace) -> None:
    """CLI: python -m personalkm.pipeline_status check"""
    pipeline = _read_pipeline()
    if not pipeline:
        print("📭 No pipeline status recorded yet")
        return

    overall = pipeline.get("overall_status", "unknown")
    icons = {"healthy": "✅", "warning": "⚠️", "degraded": "❌"}
    print(f"{icons.get(overall, '❓')} Pipeline: {overall.upper()}")
    print(f"   Last updated: {pipeline.get('last_updated', '?')}")
    print(f"   {pipeline.get('summary', '')}")
    print()

    # Phase details
    for pkey, pname in [("phase_a", "Phase A (Ingest)"), ("phase_b", "Phase B (Wikilinks)")]:
        pdata = pipeline.get(pkey, {})
        if not pdata:
            print(f"   ⬜ {pname}: no data")
            continue
        status = pdata.get("status", "?")
        icon = {"success": "✅", "partial": "⚠️", "skipped": "⏭️", "failed": "❌", "error": "❌"}.get(status, "❓")
        detail = pdata.get("detail", "")
        proc = pdata.get("processed", 0)
        fail = pdata.get("failed", 0)
        skip = pdata.get("skipped", 0)
        print(f"   {icon} {pname}: {status} (exit={pdata.get('exit_code', '?')})")
        if proc or fail or skip:
            print(f"       processed={proc} failed={fail} skipped={skip}")
        if detail:
            print(f"       {detail[:120]}")
        if pdata.get("errors"):
            for e in pdata["errors"][:3]:
                print(f"       ⚠️  {e[:120]}")
        print()

    # Vault state
    vault = pipeline.get("vault", {})
    if vault:
        dirty_icon = "🔴" if vault.get("dirty") else "🟢"
        print(f"   {dirty_icon} Vault: {'DIRTY' if vault.get('dirty') else 'clean'}")
        if vault.get("dirty"):
            print(f"       {vault.get('uncommitted_files', 0)} uncommitted file(s)")
        raw = vault.get("raw_unprocessed", 0)
        raw_r = vault.get("raw_breakdown", {}).get("resolvable", 0)
        print(f"       Raw: {raw} total ({raw_r} resolvable, {vault.get('raw_oldest_days', 0)} days oldest)")
        print(f"       Entities: {vault.get('wiki_entities', 0)} | Concepts: {vault.get('wiki_concepts', 0)}")
        print()

    # Blockers
    blockers = pipeline.get("blockers", [])
    if blockers:
        print(f"   ⚠️  {len(blockers)} Blocker(s):")
        for b in blockers:
            sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(b.get("severity", "low"), "⚪")
            print(f"       {sev} [{b['phase']}] {b['reason']}")
            fix = b.get("fix", "")
            if fix:
                print(f"          → {fix}")
        print()


def _cmd_blockers(_args: Namespace) -> None:
    """CLI: python -m personalkm.pipeline_status blockers"""
    pipeline = _read_pipeline()
    blockers = _analyze_blockers(pipeline)
    if not blockers:
        print("✅ No blockers — pipeline is healthy")
        return
    for b in blockers:
        sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(b.get("severity", "low"), "⚪")
        print(f"{sev} [{b['phase'].upper()}] {b['reason']}")
        fix = b.get("fix", "")
        if fix:
            print(f"   → {fix}")
    print(f"\n{len(blockers)} blocker(s)")


def _cmd_summary(_args: Namespace) -> None:
    """CLI: python -m personalkm.pipeline_status summary — one-liner for shell prompt."""
    pipeline = _read_pipeline()
    if not pipeline:
        print("no data")
        return
    overall = pipeline.get("overall_status", "?")
    n_blockers = len(pipeline.get("blockers", []))
    raw = pipeline.get("vault", {}).get("raw_unprocessed", 0)
    print(f"{overall} | {n_blockers} blockers | {raw} raw")


# ──────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = ArgumentParser(description="PersonalKM Pipeline Status Reporter")
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest — update status after a run
    p_ingest = sub.add_parser("ingest", help="Update status after a pipeline run")
    p_ingest.add_argument("--phase", default="A", choices=["A", "B"])
    p_ingest.add_argument("--exit-code", type=int, default=0)
    p_ingest.add_argument("--processed", type=int, default=0)
    p_ingest.add_argument("--failed", type=int, default=0)
    p_ingest.add_argument("--skipped", type=int, default=0)
    p_ingest.add_argument("--trashed", type=int, default=0)
    p_ingest.add_argument("--health-status", default="unknown")
    p_ingest.add_argument("--errors", default="")

    # check — human-readable view
    sub.add_parser("check", help="Show human-readable pipeline status")

    # blockers — just blockers
    sub.add_parser("blockers", help="Show current blockers")

    # summary — one-liner for shell prompt
    sub.add_parser("summary", help="Short one-line summary")

    args = parser.parse_args()

    handlers = {
        "ingest": _cmd_ingest,
        "check": _cmd_check,
        "blockers": _cmd_blockers,
        "summary": _cmd_summary,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()