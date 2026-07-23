#!/usr/bin/env python3
"""
Move saved Obsidian Copilot conversation exports into raw/ so the normal
Phase A pipeline (ingest_wiki.py) picks them up and synthesizes wiki pages
from them.

Copilot (the Obsidian plugin) saves each chat as
`copilot/copilot-conversations/<topic>@<YYYYMMDD>_<HHMMSS>.md` with a
`**user**:` / `**ai**:` transcript body — already full content, no URL to
resolve. `ingest_file_v2` doesn't require a URL (it falls back to the raw
body when there's no resolved/ counterpart), so dropping a renamed copy
into raw/<Category>/ is enough to get it synthesized on the next run.

Renaming to `<date>-<log_id>-<slug>.md` matches the convention every other
raw capture uses (see personalkm.capture.notes). The file is MOVED, not
copied — a re-run is naturally idempotent, since once a conversation lands
in raw/ it's gone from copilot/copilot-conversations/ and won't be
considered again.

AGENTS.md hard rule 1: agents must never touch the vault directly. This
script is tested against tmp_path fixtures only; run it yourself against
the real vault path (or wire it into cron — see launchd/).

Usage:
    python scripts/ingest_copilot_conversations.py --vault <path> [--category Tech] [--apply]
"""

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import yaml

from personalkm.capture.notes import slugify
from personalkm.frontmatter import split_frontmatter

# Copilot's own export naming: "<topic>@<YYYYMMDD>_<HHMMSS>.md"
_FILENAME_RE = re.compile(r"^(?P<topic>.+)@(?P<date>\d{8})_(?P<time>\d{6})$")

# Copilot's AI title-generation sometimes fails and dumps the raw,
# unparsed JSON response as the title instead — both the filename and the
# `topic:` frontmatter end up as a mangled `` ```json___title_<real title>``
# stub. The real title survives (underscored) after that marker.
_JSON_TITLE_STUB_RE = re.compile(r"^`*json_*title_+", re.IGNORECASE)


def _humanize_filename_topic(raw: str) -> str:
    cleaned = _JSON_TITLE_STUB_RE.sub("", raw)
    cleaned = cleaned.replace("_", " ").strip(" ,")
    return cleaned or raw


def resolve_topic(fm_topic: str, filename_topic: str, captured_at: datetime) -> str:
    """Pick a usable title, working around Copilot's JSON-title-gen bug.

    Prefers the frontmatter `topic:` field, but falls back to a cleaned-up
    filename topic (or a generic label) when that field itself is a
    malformed JSON stub — see `_JSON_TITLE_STUB_RE`.
    """
    fm_topic = (fm_topic or "").strip()
    if fm_topic and not fm_topic.startswith("```"):
        return fm_topic
    humanized = _humanize_filename_topic(filename_topic)
    if humanized and not humanized.startswith("```"):
        return humanized
    return f"Copilot Conversation {captured_at.date().isoformat()}"


def parse_conversation_filename(stem: str) -> Optional[Tuple[str, datetime]]:
    """Extract (topic, captured_at) from a Copilot conversation filename stem.

    Returns None if the stem doesn't match Copilot's `<topic>@<date>_<time>`
    convention (e.g. an unrelated file dropped into the same folder).
    """
    m = _FILENAME_RE.match(stem)
    if not m:
        return None
    try:
        captured_at = datetime.strptime(
            f"{m.group('date')}_{m.group('time')}", "%Y%m%d_%H%M%S"
        )
    except ValueError:
        return None
    topic = m.group("topic").strip() or "untitled-conversation"
    return topic, captured_at


def build_raw_note(
    topic: str, captured_at: datetime, model_key: str, transcript: str
) -> Tuple[str, str]:
    """Return (filename, content) shaped like any other raw capture."""
    log_id = f"{captured_at.strftime('%Y%m%d%H%M')}_00001"
    filename = f"{captured_at.date().isoformat()}-{log_id}-{slugify(topic)}.md"
    model_line = f"Model: {model_key}\n" if model_key else ""
    content = (
        f"# {topic}\n\n"
        f"## Log ID\n{log_id}\n\n"
        f"## Source\nObsidian Copilot conversation, captured {captured_at.isoformat()}\n"
        f"{model_line}\n"
        f"## Conversation\n{transcript.strip()}\n"
    )
    return filename, content


def unique_path(path: Path) -> Path:
    """Avoid clobbering an existing raw file that generated the same name."""
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_stem(f"{path.stem}-{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--vault", required=True, help="Path to the vault root (contains copilot/, raw/)"
    )
    parser.add_argument(
        "--category", default="Tech", help="raw/<Category>/ to move files into (default: Tech)"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Move files (default: dry-run preview)"
    )
    args = parser.parse_args()

    vault_root = Path(args.vault)
    source_dir = vault_root / "copilot" / "copilot-conversations"
    target_dir = vault_root / "raw" / args.category

    if not source_dir.exists():
        raise SystemExit(f"No copilot/copilot-conversations/ under {args.vault}")

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")

    processed = 0
    skipped = 0
    for f in sorted(source_dir.glob("*.md")):
        parsed = parse_conversation_filename(f.stem)
        if parsed is None:
            print(f"  [SKIP] {f.name} (doesn't match Copilot's <topic>@<date>_<time> filename)")
            skipped += 1
            continue
        filename_topic, captured_at = parsed

        raw_text = f.read_text(encoding="utf-8")
        fm_text, body = split_frontmatter(raw_text)
        fm = (yaml.safe_load(fm_text) or {}) if fm_text else {}
        model_key = fm.get("modelKey", "")
        topic = resolve_topic(fm.get("topic", ""), filename_topic, captured_at)

        filename, content = build_raw_note(topic, captured_at, model_key, body)
        dest = unique_path(target_dir / filename)

        print(f"  [{'MOVED' if args.apply else 'WOULD MOVE'}] {f.name} -> raw/{args.category}/{dest.name}")
        if args.apply:
            target_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            f.unlink()
        processed += 1

    print(f"\nConversations processed: {processed} | skipped: {skipped}")
    if not args.apply:
        print("\nRun with --apply to move files into raw/.")


if __name__ == "__main__":
    main()
