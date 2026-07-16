#!/usr/bin/env python3
import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ARCHIVABLE_STATUSES = {"archived", "done"}
TRASH_STATUSES = {"x"}
CATEGORY_DIRS = {"Food", "General", "Photography", "Tech"}


@dataclass(frozen=True)
class PlannedMove:
    source: Path
    target: Path
    status: str = ""
    reason: str = ""


@dataclass(frozen=True)
class SkippedNote:
    source: Path
    reason: str


@dataclass(frozen=True)
class HousekeepingReport:
    moves: list[PlannedMove]
    skipped: list[SkippedNote]

    @property
    def archive_count(self) -> int:
        return sum(1 for move in self.moves if "Archive" in move.target.parts)

    @property
    def trash_count(self) -> int:
        return sum(1 for move in self.moves if "Trash" in move.target.parts)


def frontmatter_status(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return ""

    end = markdown.find("\n---", 4)
    if end == -1:
        return ""

    for line in markdown[4:end].splitlines():
        if line.lower().startswith("status:"):
            return line.split(":", 1)[1].strip().strip("\"'").lower()
    return ""


def status_reason(markdown: str) -> tuple[str, str]:
    if not markdown.startswith("---\n"):
        return "", "missing_frontmatter"

    end = markdown.find("\n---", 4)
    if end == -1:
        return "", "broken_frontmatter"

    status = frontmatter_status(markdown)
    if not status:
        return "", "missing_status"
    if status not in ARCHIVABLE_STATUSES and status not in TRASH_STATUSES:
        return status, "active_or_unsupported_status"
    return status, "actionable"


def unique_target_path(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def trash_target_path(source: Path, trash_root: Path, category: str) -> Path:
    trashed_name = f"{source.name}.trash"
    return trash_root / category / trashed_name


def inbox_notes(inbox_root: Path) -> list[tuple[Path, str]]:
    notes: list[tuple[Path, str]] = []

    for source in sorted(inbox_root.glob("*.md")):
        notes.append((source, "General"))

    for source in sorted(inbox_root.glob("*/*.md")):
        category = source.parent.name
        if category in CATEGORY_DIRS:
            notes.append((source, category))

    return notes


def collect_moves(vault_root: Path) -> list[PlannedMove]:
    return collect_housekeeping_report(vault_root).moves


def collect_housekeeping_report(vault_root: Path) -> HousekeepingReport:
    inbox_root = vault_root / "Inbox"
    archive_root = vault_root / "Archive"
    trash_root = vault_root / "Trash"
    moves: list[PlannedMove] = []
    skipped: list[SkippedNote] = []

    for source, category in inbox_notes(inbox_root):
        status, reason = status_reason(source.read_text(encoding="utf-8"))
        if status in ARCHIVABLE_STATUSES:
            target_dir = archive_root / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name
            move_reason = "archive_completed_note"
        elif status in TRASH_STATUSES:
            target_dir = trash_root / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target = trash_target_path(source, trash_root, category)
            move_reason = "trash_rejected_note"
        else:
            skipped.append(SkippedNote(source=source, reason=reason))
            continue

        moves.append(PlannedMove(
            source=source,
            target=unique_target_path(target),
            status=status,
            reason=move_reason,
        ))

    return HousekeepingReport(moves=moves, skipped=skipped)


def collect_archive_moves(vault_root: Path) -> list[PlannedMove]:
    return [move for move in collect_moves(vault_root) if "Archive" in move.target.parts]


def run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def archive(vault_root: Path, dry_run: bool) -> list[PlannedMove]:
    moves = collect_moves(vault_root)
    for move in moves:
        print(f"{move.source.relative_to(vault_root)} -> {move.target.relative_to(vault_root)}")
        if not dry_run:
            run_git(["mv", str(move.source.relative_to(vault_root)), str(move.target.relative_to(vault_root))], vault_root)
    return moves


def housekeeping_report_markdown(vault_root: Path, report: HousekeepingReport) -> str:
    lines = [
        "# PersonalKM Housekeeping Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary",
        f"- Archive moves: {report.archive_count}",
        f"- Trash moves: {report.trash_count}",
        f"- Skipped notes: {len(report.skipped)}",
        "",
        "## Moves",
    ]
    if report.moves:
        for move in report.moves:
            lines.append(
                f"- `{move.source.relative_to(vault_root)}` -> "
                f"`{move.target.relative_to(vault_root)}` ({move.reason})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Skipped"])
    if report.skipped:
        for skipped in report.skipped:
            lines.append(f"- `{skipped.source.relative_to(vault_root)}`: {skipped.reason}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Move completed or trashed Inbox notes out of Inbox.")
    parser.add_argument("--vault", default=".", help="Vault root path. Defaults to current directory.")
    parser.add_argument("--dry-run", action="store_true", help="Show moves without changing files.")
    parser.add_argument("--commit", action="store_true", help="Commit and push moved notes.")
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    moves = archive(vault_root, args.dry_run)

    if not moves:
        print("No completed or trashed Inbox notes found.")
        return

    if args.commit and not args.dry_run:
        run_git(["commit", "-m", "Process completed inbox notes"], vault_root)
        run_git(["push"], vault_root)


if __name__ == "__main__":
    main()
