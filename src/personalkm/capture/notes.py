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

CATEGORY_DIRS = {
    "photography": "Photography",
    "food": "Food",
    "tech": "Tech",
    "general": "General",
}


@dataclass(frozen=True)
class LinkNote:
    title: str
    url: str
    summary: str
    category: str
    captured_on: date
    platform: str = "web"
    extraction_status: str = "ok"
    needs_review: bool = False
    body_markdown: str = ""
    location_city: str = ""
    log_id: str = ""
    content_type: str = ""
    needs_local_worker: bool = False
    worker_status: str = "not_required"
    worker_type: str = "none"
    worker_retry_count: int = 0
    worker_error: str = ""
    worker_processed_at: str = ""
    worker_name: str = ""

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
    log_part = f"{note.log_id}-" if note.log_id else ""
    return f"{note.captured_on.isoformat()}-{log_part}{slugify(note.title)}.md"


def note_target_dir(note: LinkNote, fallback_dir: str) -> str:
    category_dir = CATEGORY_DIRS.get(note.category, CATEGORY_DIRS["general"])
    return str(Path(fallback_dir) / category_dir)


def render_note(note: LinkNote) -> str:
    """Render a raw note as pure markdown body (no YAML frontmatter).

    YAML was previously written here but was stripped during ingestion.
    Now we write only the body — the title + content that flows into
    ingestion_v2.py which generates the real LLM-Wiki frontmatter.
    """
    log_id_section = f"## Log ID\n{note.log_id}\n\n" if note.log_id else ""
    body = note.body_markdown.strip()
    if not body:
        body = (
            "## 摘要\n"
            f"{note.summary.strip()}\n\n"
            "## 原文連結\n"
            f"{note.url}"
        )
    return (
        f"# {note.title}\n\n"
        f"{log_id_section}"
        f"{body}\n"
    )


def write_note(vault_root: Path, inbox_dir: str, note: LinkNote) -> Path:
    target_dir = vault_root / note_target_dir(note, inbox_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / note_filename(note)

    counter = 2
    while target_path.exists():
        target_path = target_dir / f"{target_path.stem}-{counter}.md"
        counter += 1

    target_path.write_text(render_note(note), encoding="utf-8")
    return target_path
