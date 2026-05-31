import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path


CATEGORY_TAGS = {
    "photography": "攝影景點",
    "food": "美食",
    "tech": "技術",
    "general": "待分類",
}


@dataclass(frozen=True)
class LinkNote:
    title: str
    url: str
    summary: str
    category: str
    captured_on: date

    @property
    def tag(self) -> str:
        return CATEGORY_TAGS.get(self.category, CATEGORY_TAGS["general"])


def slugify(value: str, max_length: int = 60) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"[\\/:*?\"<>|#^\[\]]+", "-", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized[:max_length].strip("-") or "untitled"


def note_filename(note: LinkNote) -> str:
    return f"{note.captured_on.isoformat()}-{slugify(note.title)}.md"


def render_note(note: LinkNote) -> str:
    safe_summary = note.summary.replace("\n", " ").strip()
    return (
        "---\n"
        f"tags: [{note.tag}]\n"
        "source: LINE\n"
        f"date: {note.captured_on.isoformat()}\n"
        f"url: {note.url}\n"
        f"summary: {safe_summary}\n"
        "status: unread\n"
        "---\n\n"
        f"# {note.title}\n\n"
        "## 摘要\n"
        f"{note.summary.strip()}\n\n"
        "## 原文連結\n"
        f"{note.url}\n"
    )


def write_note(vault_root: Path, inbox_dir: str, note: LinkNote) -> Path:
    target_dir = vault_root / inbox_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / note_filename(note)

    counter = 2
    while target_path.exists():
        target_path = target_dir / f"{target_path.stem}-{counter}.md"
        counter += 1

    target_path.write_text(render_note(note), encoding="utf-8")
    return target_path
