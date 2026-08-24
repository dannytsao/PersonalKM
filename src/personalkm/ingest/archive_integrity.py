"""Archive ↔ wiki citation integrity check.

Every file under ``Archive/raw/`` was moved there *after* being ingested, so
each one must be cited by at least one wiki page via its
``[[Archive/raw/...]]`` source wikilink. A file that no wiki page cites means
one of:

* its wiki page was later deleted or migrated to the other vault without the
  archive copy following (tech→lifestyle migrations left these behind), or
* the file was swept into ``Archive/`` by a non-pipeline writer (Obsidian Git
  hourly backup commits) before Phase A ever synthesized a page from it,
* the same capture was fetched twice and only one copy was ingested.

All three are silent losses that the ingestion health check never caught — it
only verified ``raw/`` emptiness. This module makes the invariant checkable
and is surfaced through ``personalkm.pipeline_status`` blockers.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _wiki_corpus(vault_root: Path) -> str:
    """Concatenated text of every markdown file under wiki/."""
    parts: list[str] = []
    wiki = vault_root / "wiki"
    if wiki.exists():
        for f in sorted(wiki.rglob("*.md")):
            try:
                parts.append(_nfc(f.read_text(encoding="utf-8", errors="ignore")))
            except OSError:
                continue
    return "\n".join(parts)


def find_archive_orphans(
    vault_root: Path,
    extra_texts: list[str] | None = None,
) -> list[str]:
    """Return Archive/raw files cited by no known wiki page.

    Matching is by filename stem, so wikilinks written with or without the
    category folder prefix both count. Both sides are NFC-normalized: macOS
    may store NFD on disk while pages embed NFC, and raw byte comparison
    would then report false orphans (this exact bug hid the cross-vault
    migrated pages during the 2026-08-23 investigation).

    ``extra_texts`` folds additional corpora into the citation check — pass
    the sibling vault's wiki corpus when pages may have been migrated across
    vaults.
    """
    archive_dir = vault_root / "Archive" / "raw"
    if not archive_dir.exists():
        return []

    corpus = _wiki_corpus(vault_root)
    if extra_texts:
        corpus += "\n" + "\n".join(_nfc(t) for t in extra_texts)

    orphans: list[str] = []
    for f in sorted(archive_dir.rglob("*.md")):
        if _nfc(f.stem) not in corpus:
            orphans.append(str(f.relative_to(archive_dir).with_suffix("")))
    return orphans


if __name__ == "__main__":  # pragma: no cover - operator convenience
    import sys

    default_root = Path.home() / "Documents" / "PersonalKM" / "Personalkm-vault"
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else default_root
    found = find_archive_orphans(root)
    print(f"{root.name}: {len(found)} orphaned archive file(s)")
    for rel in found:
        print(f"  {rel}")
