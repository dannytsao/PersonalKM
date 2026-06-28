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


# ---------------------------------------------------------------------------
# Unified tag parsing — handles every format currently found in the wiki
# ---------------------------------------------------------------------------

def parse_yaml_list(raw: Any) -> list[str]:
    """
    Parse a tag/list value from any format into a flat list of strings.

    Handles:
      - JSON array:        ``["a", "b"]``
      - Python repr:       ``['a', 'b']``  (single quotes)
      - Flow sequence:     ``[a, b]``       (bare words, no quotes)
      - Nested list:       ``[['a','b'], ['c']]``  → flattened
      - Comma-separated:   ``a, b, c``
      - Empty variants:    ``[]``, ``""``, ``''``, ``None``
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return _flatten_and_stringify(raw)

    s = str(raw).strip()
    if not s or s in ("[]", "{}", '""', "''", "None", "null"):
        return []

    # ── [...] wrapper ───────────────────────────────────────────
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []

        # Try strict JSON (double quotes)
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return _flatten_and_stringify(parsed)
        except json.JSONDecodeError:
            pass

        # Try Python repr (single quotes → double quotes)
        try:
            double = s.replace("'", '"')
            # Handle bare-word keys in flow: [a, b] → ["a", "b"]
            if not ('"' in s or "'" in s):
                double = re.sub(r'(\w[\w.-]*)', r'"\1"', inner)
                double = "[" + double + "]"
            parsed = json.loads(double)
            if isinstance(parsed, list):
                return _flatten_and_stringify(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

        # Final fallback: split on commas
        return [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]

    # ── YAML list format: "- item", "- item2" ─────────────
    # (multiline content after tags: with no brackets)
    if s.startswith("- ") or "\n- " in s:
        items = []
        for line in s.splitlines():
            line = line.strip()
            if line.startswith("- "):
                items.append(line[2:].strip().strip("'\""))
        if items:
            return items

    # ── Comma-separated bare string ─────────────────────────────
    if "," in s:
        return [t.strip() for t in s.split(",") if t.strip()]

    # ── Single value ────────────────────────────────────────────
    cleaned = s.strip().strip("'\"")
    return [cleaned] if cleaned else []


def _flatten_and_stringify(items: list) -> list[str]:
    """Recursively flatten a nested list, converting all elements to str."""
    result: list[str] = []
    for item in items:
        if isinstance(item, list):
            result.extend(_flatten_and_stringify(item))
        else:
            result.append(str(item).strip().strip("'\""))
    return result


def _needs_quoting(tag: str) -> bool:
    """Check if a tag value needs YAML quoting."""
    if not tag:
        return True
    if ":" in tag:
        return True
    if tag.startswith((" ", "-", "{", "[", "'", '"', "&", "*", "!", "|", ">", "?", "@")):
        return True
    return False


def format_yaml_tags(tags: list[str]) -> str:
    """
    Format a list of tags as a uniform indented YAML list.

    Input:  ``["docker", "kubernetes", "rag"]``
    Output::

        - docker
        - kubernetes
        - rag

    Empty list → ``[]``.
    """
    if not tags:
        return "  []"
    lines: list[str] = []
    for t in tags:
        if _needs_quoting(t):
            lines.append(f"  - {json.dumps(t, ensure_ascii=False)}")
        else:
            lines.append(f"  - {t}")
    return "\n".join(lines)


def deduplicate_frontmatter(content: str) -> str:
    """
    Remove duplicate keys in frontmatter, keeping the **last** occurrence
    (most recently written). Preserves multiline continuations (e.g., YAML
    list items after a key).  Cleans up leading blank lines inside the block.
    """
    if not content.startswith("---\n"):
        return content

    # Find closing ---
    end = content.find("\n---\n", 4)
    if end == -1:
        return content

    fm_text = content[4:end]

    # Parse into key-value blocks (a key line + its continuation lines)
    # Continuation = subsequent lines that don't contain ":" + aren't blank
    blocks: list[tuple[str, list[str]]] = []
    current_key = ""
    current_lines: list[str] = []

    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped:
            current_lines.append(line)
            continue
        if ":" in stripped and not stripped.startswith(("- ", "  -")):
            # New key: save previous block if any
            if current_key:
                blocks.append((current_key, current_lines))
            parts = stripped.split(":", 1)
            current_key = parts[0].strip()
            current_lines = [line]
        else:
            # Continuation of current key
            current_lines.append(line)

    if current_key:
        blocks.append((current_key, current_lines))

    # Deduplicate: keep the LAST block for each key
    seen: dict[str, list[str]] = {}
    for key, lines in blocks:
        seen[key] = lines  # overwrite → keeps last occurrence

    # Rebuild in original order (first occurrence of each key)
    kept_keys: set[str] = set()
    ordered_blocks: list[list[str]] = []
    for key, lines in blocks:
        if key not in kept_keys:
            ordered_blocks.append(seen[key])
            kept_keys.add(key)

    # Collapse
    cleaned_lines: list[str] = []
    for block in ordered_blocks:
        cleaned_lines.extend(block)
    cleaned = "\n".join(cleaned_lines).strip()
    return "---\n" + cleaned + "\n---\n" + content[end + 5 :]