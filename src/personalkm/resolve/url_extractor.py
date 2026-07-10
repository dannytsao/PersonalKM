"""Extract URL from raw note body text or frontmatter.

Priority order:
1. Frontmatter ``url`` field (present in new-style notes).
2. "原文連結" (original link) section — the most reliable body section.
3. "內含連結" (contains links) bullet list.
4. Any ``https?://`` URL in the body as last-resort fallback.

Returns None when no URL is found.
"""

from __future__ import annotations

import re
from pathlib import Path


def extract_url(raw_path: Path) -> str | None:
    """Extract the single most important URL from a raw note file.

    Parameters
    ----------
    raw_path : Path
        Path to the raw markdown file.

    Returns
    -------
    str | None
        The extracted URL, or None if no URL was found.
    """
    text = raw_path.read_text(encoding="utf-8")

    # 1. Frontmatter ``url`` field
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if m:
        frontmatter = m.group(1)
        fm_url = re.search(r"^url:\s*(.+)$", frontmatter, re.MULTILINE)
        if fm_url:
            return fm_url.group(1).strip()

    # Only search the body (strip frontmatter if present)
    body = text
    if m:
        body = text[m.end() :]

    # 2. "原文連結" section
    m = re.search(
        r"^##\s*原文連結\s*\n(?:https?://\S+)",
        body,
        re.MULTILINE,
    )
    if m:
        return _extract_url_from_line(m.group())

    # 3. "內含連結" bullet list
    m = re.search(r"^##\s*內含連結\s*\n", body, re.MULTILINE)
    if m:
        section_end = _section_end(body, m.end())
        section = body[m.end() : section_end]
        for line in section.splitlines():
            url = _extract_url_from_line(line)
            if url:
                return url

    # 4. Any https URL as fallback
    m = re.search(r"https?://[^\s\)\]>\"']+", body)
    if m:
        return m.group(0).rstrip(".,;!?)]}>")

    return None


def extract_all_urls(raw_path: Path) -> list[str]:
    """Extract ALL URLs from a raw note body (for multi-link notes).

    Useful for notes containing multiple links (e.g. ``graphify 官网 + Github +
    Obsidian 官网`` in one note).
    """
    text = raw_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    body = text[m.end() :] if m else text
    return re.findall(r"https?://[^\s\)\]>\"']+", body)


def _extract_url_from_line(text: str) -> str | None:
    m = re.search(r"(https?://\S+)", text)
    return m.group(1).rstrip(".,;!?)>") if m else None


def _section_end(body: str, start: int) -> int:
    """Find the end of a section (next ``##`` or EOF)."""
    m = re.search(r"^##\s", body[start:], re.MULTILINE)
    return start + m.start() if m else len(body)