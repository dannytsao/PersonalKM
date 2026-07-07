"""Pre-ingestion raw note quality check.

Scans raw/ notes before the weekly ingestion run and flags quality issues
that would produce poor wiki output. This is a *detect-only* step — the actual
repair happens during the ingestion pipeline.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from personalkm.llm.router import route

log = logging.getLogger(__name__)

# ── Issue classification ──────────────────────────────────────────────────


@dataclass
class RawNoteIssue:
    severity: str       # "HIGH" | "MEDIUM" | "LOW"
    category: str       # machine-readable key
    description: str    # human-readable message
    auto_repairable: bool = True


@dataclass
class RawNoteReport:
    path: str
    issues: list[RawNoteIssue] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return len(self.issues) == 0

    @property
    def summary(self) -> str:
        counts = {}
        for i in self.issues:
            counts.setdefault(i.severity, 0)
            counts[i.severity] += 1
        parts = [f"{k}={v}" for k, v in sorted(counts.items())]
        return f"{'✅' if self.healthy else '⚠️'}  {len(self.issues)} issue(s)" + (f" [{', '.join(parts)}]" if parts else "")


# ── Detectors ──────────────────────────────────────────────────────────────

_GENERIC_PATTERNS = [
    "此連結標題", "本影片介紹", "本文介紹",
    "This link title", "This video introduces",
    "generic summary", "placeholder",
]

_PLATFORM_BLOCKED = ["instagram", "tiktok", "facebook.com/share"]


def _check_frontmatter(path: Path, content: str) -> list[RawNoteIssue]:
    """Parse YAML-like frontmatter and detect quality problems."""
    issues: list[RawNoteIssue] = []

    if not content.startswith("---"):
        return [RawNoteIssue("HIGH", "missing_frontmatter", "No frontmatter block found")]

    close = content.find("---", 3)
    if close == -1:
        return [RawNoteIssue("HIGH", "broken_frontmatter", "Frontmatter delimiter not closed")]

    fm = content[3:close]

    # extraction_status
    if (m := re.search(r"extraction_status:\s*(\S+)", fm)):
        status = m.group(1)
        if status in ("partial", "error"):
            issues.append(RawNoteIssue("HIGH", f"extraction_{status}", f"Extraction status is '{status}'"))
        elif status == "blocked":
            issues.append(RawNoteIssue("LOW", "platform_blocked", "Platform blocked — needs manual review", auto_repairable=False))

    # summary quality
    if (m := re.search(r"summary:\s*(.*)", fm)):
        raw_summary = m.group(1).strip().strip('"').strip("'")
        if not raw_summary:
            issues.append(RawNoteIssue("HIGH", "empty_summary", "Summary is empty"))
        elif any(p in raw_summary for p in _GENERIC_PATTERNS):
            issues.append(RawNoteIssue("MEDIUM", "generic_summary", "Summary appears generic/placeholder"))

    # tags
    tags_line = re.search(r"tags:\s*(\[.*?\]|)", fm)
    if tags_line:
        tag_str = tags_line.group(1).strip()
        if tag_str in ("[]", ""):
            issues.append(RawNoteIssue("MEDIUM", "missing_tags", "No tags assigned"))

    return issues


def _check_url_platform(path: Path, content: str) -> list[RawNoteIssue]:
    """Check if the note's URL is from a blocked platform."""
    issues: list[RawNoteIssue] = []
    url_match = re.search(r"url:\s*(https?://\S+)", content)
    if url_match:
        url = url_match.group(1)
        for blocked in _PLATFORM_BLOCKED:
            if blocked in url.lower():
                issues.append(RawNoteIssue("LOW", "platform_blocked", f"URL is from {blocked} — may not auto-extract", auto_repairable=False))
    return issues


# ── Main scanner ────────────────────────────────────────────────────────────


def scan_raw_notes(vault_path: str | Path) -> dict[str, Any]:
    """Scan every .md file under *vault_path*/raw/ and return a quality report.

    Returns a dict matching the style of IngestionHealthCheck.run_all_checks()
    so the caller can merge results cleanly.
    """
    vault = Path(vault_path)
    raw_dir = vault / "raw"

    if not raw_dir.is_dir():
        return {"status": "skipped", "reason": f"raw/ directory not found at {raw_dir}", "notes": []}

    all_reports: list[dict] = []
    total_healthy = 0
    total_issues = 0

    for note_file in sorted(raw_dir.rglob("*.md")):
        rel = note_file.relative_to(vault)
        content = note_file.read_text(encoding="utf-8", errors="replace")

        issues: list[RawNoteIssue] = []
        issues.extend(_check_frontmatter(note_file, content))
        issues.extend(_check_url_platform(note_file, content))

        report = {
            "path": str(rel),
            "healthy": len(issues) == 0,
            "issues": [{"severity": i.severity, "category": i.category, "description": i.description, "auto_repairable": i.auto_repairable} for i in issues],
        }
        all_reports.append(report)

        if report["healthy"]:
            total_healthy += 1
        else:
            total_issues += 1

    high = sum(1 for r in all_reports for i in r["issues"] if i["severity"] == "HIGH")
    medium = sum(1 for r in all_reports for i in r["issues"] if i["severity"] == "MEDIUM")
    low = sum(1 for r in all_reports for i in r["issues"] if i["severity"] == "LOW")

    result = {
        "status": "healthy" if total_issues == 0 else "issues_found",
        "timestamp": datetime.now().isoformat(),
        "total_notes": len(all_reports),
        "healthy_notes": total_healthy,
        "notes_with_issues": total_issues,
        "issue_counts": {"HIGH": high, "MEDIUM": medium, "LOW": low},
        "notes": all_reports,
    }
    return result


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable health check summary to the log."""
    if report.get("status") == "skipped":
        log.info("⏭️  Raw note health check skipped: %s", report.get("reason"))
        return

    log.info("─" * 60)
    log.info("📋  PRE-INGESTION RAW NOTE QUALITY CHECK")
    log.info("─" * 60)
    log.info("  Total notes:   %d", report.get("total_notes", 0))
    log.info("  Healthy:       %d ✅", report.get("healthy_notes", 0))
    log.info("  Has issues:    %d ⚠️", report.get("notes_with_issues", 0))

    counts = report.get("issue_counts", {})
    if any(counts.values()):
        log.info("")
        log.info("  Issue breakdown:")
        for sev in ("HIGH", "MEDIUM", "LOW"):
            if counts.get(sev, 0):
                log.info("    %s  %s: %d", {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[sev], sev, counts[sev])

        problem_notes = [n for n in report.get("notes", []) if not n["healthy"]]
        log.info("")
        log.info("  Notes with issues:")
        for n in problem_notes[:10]:
            cats = ", ".join(i["category"] for i in n["issues"])
            log.info("    ⚠️  %s  [%s]", n["path"], cats)

        if len(problem_notes) > 10:
            log.info("    ... and %d more", len(problem_notes) - 10)

    log.info("─" * 60)