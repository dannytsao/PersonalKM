#!/usr/bin/env python3
import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


ARCHIVABLE_STATUSES = {"archived", "done"}
CATEGORY_DIRS = {"Food", "General", "Photography", "Tech"}


@dataclass(frozen=True)
class ArchiveMove:
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


def collect_archive_moves(vault_root: Path) -> list[ArchiveMove]:
    inbox_root = vault_root / "Inbox"
    archive_root = vault_root / "Archive"
    moves: list[ArchiveMove] = []

    for source in sorted(inbox_root.glob("*/*.md")):
        category = source.parent.name
        if category not in CATEGORY_DIRS:
            continue

        status = frontmatter_status(source.read_text(encoding="utf-8"))
        if status not in ARCHIVABLE_STATUSES:
            continue

        target_dir = archive_root / category
        target_dir.mkdir(parents=True, exist_ok=True)
        moves.append(ArchiveMove(source=source, target=unique_target_path(target_dir / source.name)))

    return moves


def run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def archive(vault_root: Path, dry_run: bool) -> list[ArchiveMove]:
    moves = collect_archive_moves(vault_root)
    for move in moves:
        print(f"{move.source.relative_to(vault_root)} -> {move.target.relative_to(vault_root)}")
        if not dry_run:
            run_git(["mv", str(move.source.relative_to(vault_root)), str(move.target.relative_to(vault_root))], vault_root)
    return moves


def main() -> None:
    parser = argparse.ArgumentParser(description="Move archived Inbox notes into matching Archive folders.")
    parser.add_argument("--vault", default=".", help="Vault root path. Defaults to current directory.")
    parser.add_argument("--dry-run", action="store_true", help="Show moves without changing files.")
    parser.add_argument("--commit", action="store_true", help="Commit and push moved notes.")
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    moves = archive(vault_root, args.dry_run)

    if not moves:
        print("No archived Inbox notes found.")
        return

    if args.commit and not args.dry_run:
        run_git(["commit", "-m", "Archive completed inbox notes"], vault_root)
        run_git(["push"], vault_root)


if __name__ == "__main__":
    main()
