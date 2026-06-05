#!/usr/bin/env python3
import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


ARCHIVABLE_STATUSES = {"archived", "done"}
TRASH_STATUSES = {"x"}
CATEGORY_DIRS = {"Food", "General", "Photography", "Tech"}


@dataclass(frozen=True)
class PlannedMove:
    source: Path
    target: Path


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
    inbox_root = vault_root / "Inbox"
    archive_root = vault_root / "Archive"
    trash_root = vault_root / "Trash"
    moves: list[PlannedMove] = []

    for source, category in inbox_notes(inbox_root):
        status = frontmatter_status(source.read_text(encoding="utf-8"))
        if status in ARCHIVABLE_STATUSES:
            target_dir = archive_root / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name
        elif status in TRASH_STATUSES:
            target_dir = trash_root / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target = trash_target_path(source, trash_root, category)
        else:
            continue

        moves.append(PlannedMove(source=source, target=unique_target_path(target)))

    return moves


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
