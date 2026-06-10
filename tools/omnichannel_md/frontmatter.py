from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


FRONTMATTER_BOUNDARY = "---"


@dataclass(frozen=True)
class MarkdownDocument:
    frontmatter: dict[str, Any]
    frontmatter_lines: list[str]
    body: str


def parse_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", stripped):
        return int(stripped)
    if len(stripped) >= 2 and stripped[0] == stripped[-1] == '"':
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped[1:-1]
    return stripped


def parse_markdown(markdown: str) -> MarkdownDocument:
    if not markdown.startswith("---\n"):
        return MarkdownDocument({}, [], markdown)

    end = markdown.find("\n---\n", 4)
    if end == -1:
        return MarkdownDocument({}, [], markdown)

    frontmatter_text = markdown[4:end]
    body = markdown[end + 5 :]
    frontmatter: dict[str, Any] = {}
    lines = frontmatter_text.splitlines()
    for line in lines:
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            frontmatter[key] = parse_scalar(value)
    return MarkdownDocument(frontmatter, lines, body)


def format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    if "\n" in text or text.startswith((" ", "-", "{", "[")) or ": " in text:
        return json.dumps(text, ensure_ascii=False)
    return text


def update_frontmatter(markdown: str, updates: dict[str, Any]) -> str:
    document = parse_markdown(markdown)
    lines = list(document.frontmatter_lines)
    seen: set[str] = set()
    updated_lines: list[str] = []

    for line in lines:
        if ":" not in line or line.lstrip().startswith("#"):
            updated_lines.append(line)
            continue
        key, _ = line.split(":", 1)
        key = key.strip()
        if key in updates:
            updated_lines.append(f"{key}: {format_scalar(updates[key])}")
            seen.add(key)
        else:
            updated_lines.append(line)

    for key, value in updates.items():
        if key not in seen:
            updated_lines.append(f"{key}: {format_scalar(value)}")

    return "---\n" + "\n".join(updated_lines).rstrip() + "\n---\n" + document.body
