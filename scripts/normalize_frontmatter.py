#!/usr/bin/env python3
"""
normalize_frontmatter.py — One-time migration to fix all wiki frontmatter issues.

What it does:
1. Normalises tags to uniform indented YAML list format
2. Removes duplicate frontmatter keys (keeps last occurrence)
3. Cleans up leading blank lines inside frontmatter block
4. Reports stats on what was changed

Usage:
    python scripts/normalize_frontmatter.py [--vault PATH] [--dry-run]

Dry-run:
    python scripts/normalize_frontmatter.py --dry-run
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
_HERE = Path(__file__).resolve().parent
_PROJECT = _HERE.parent
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))

from tools.omnichannel_md.frontmatter import (
    parse_yaml_list,
    format_yaml_tags,
    deduplicate_frontmatter,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("normalize_fm")

# ---------------------------------------------------------------------------
# YAML frontmatter extraction (standalone, no external deps)
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\n(?P<fm>.*?)\n---\n?", re.DOTALL)


def _parse_fm_text(content: str) -> tuple[dict[str, str], str]:
    """Minimal key:value parser returning {key: raw_value_string}."""
    m = _FM_RE.match(content)
    if not m:
        return {}, content
    fm_text = m.group("fm")
    body = content[m.end() :]
    raw: dict[str, str] = {}
    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        raw[key.strip()] = val.strip()
    return raw, body


def _extract_tags_raw(fm_text: str) -> str:
    """
    Extract the raw tag value(s) following a ``tags:`` key in frontmatter.

    Handles both:
      - Single line:  ``tags: [a, b, c]``
      - Multiline:    ``tags:\n  [a, b, c]`` or ``tags:\n  - a\n  - b``

    Returns the raw text after ``tags:`` (stripped), or empty string.
    """
    lines = fm_text.strip().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("tags:") or stripped.startswith("tags "):
            prefix, _, rest = stripped.partition(":")
            rest = rest.strip()
            if rest:
                # Single-line: tags: [a, b]
                return rest
            # Multiline: look at next lines
            tag_lines: list[str] = []
            for j in range(i + 1, len(lines)):
                nxt = lines[j]
                if not nxt.strip() or ":" in nxt.strip():
                    break
                tag_lines.append(nxt)
            return "\n".join(tag_lines).strip()
    return ""


def _replace_tags_section(fm_text: str, new_tags_yaml: str) -> str:
    """
    Replace the entire ``tags:`` section (single or multiline) with the normalized version.
    """
    lines = fm_text.splitlines()
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("tags:") or stripped.startswith("tags "):
            # Skip current tags: line
            i += 1
            # Skip any subsequent lines that are continuations of tags
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt or ":" in nxt:
                    break
                i += 1
            # Insert normalized tags block
            new_lines.append("tags:")
            for tag_line in new_tags_yaml.splitlines():
                new_lines.append(tag_line)
            continue
        new_lines.append(lines[i])
        i += 1
    return "\n".join(new_lines)


def rebuild_content(content: str) -> str:
    """
    Rebuild a wiki file with normalised frontmatter.

    1. Deduplicate keys
    2. Parse tags -> unified YAML list format
    3. Clean leading blank lines inside frontmatter
    """
    # First pass: deduplicate keys
    content = deduplicate_frontmatter(content)

    m = _FM_RE.match(content)
    if not m:
        return content

    fm_text = m.group("fm")
    body = content[m.end() :]

    # Extract and normalize tags if present
    raw_tags = _extract_tags_raw(fm_text)
    if raw_tags:
        parsed = parse_yaml_list(raw_tags)
        formatted = format_yaml_tags(parsed)
        fm_text = _replace_tags_section(fm_text, formatted)

    # Trim leading blank lines from body
    body = body.lstrip("\n")

    return "---\n" + fm_text.strip() + "\n---\n" + body


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(vault_path: Path, dry_run: bool) -> dict:
    wiki_path = vault_path / "wiki"
    if not wiki_path.exists():
        logger.error("wiki/ not found in %s", vault_path)
        return {"status": "error", "error": "wiki/ not found"}

    stats = {
        "scanned": 0,
        "changed": 0,
        "tag_format_fixed": 0,
        "dedup_fixed": 0,
        "errors": 0,
        "files": [],
    }

    for subdir in ("entities", "concepts"):
        dir_path = wiki_path / subdir
        if not dir_path.exists():
            continue
        for fp in sorted(dir_path.glob("*.md")):
            stats["scanned"] += 1
            try:
                original = fp.read_text(encoding="utf-8")
                normalized = rebuild_content(original)

                if normalized != original:
                    stats["changed"] += 1
                    stats["files"].append(str(fp.relative_to(vault_path)))

                    # Roughly determine what changed
                    orig_fm, _ = _parse_fm_text(original)
                    norm_fm, _ = _parse_fm_text(normalized)
                    orig_tags = orig_fm.get("tags", "")
                    if "[" in orig_tags or "," in orig_tags:
                        stats["tag_format_fixed"] += 1

                    if not dry_run:
                        fp.write_text(normalized, encoding="utf-8")
                        logger.info("  Fixed: %s", fp.relative_to(vault_path))

            except Exception as e:
                stats["errors"] += 1
                logger.error("  Error processing %s: %s", fp.name, e)

    stats["dedup_fixed"] = stats["changed"] - stats["tag_format_fixed"]
    if stats["dedup_fixed"] < 0:
        stats["dedup_fixed"] = 0

    return stats


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Normalise wiki frontmatter")
    parser.add_argument("--vault", default=str(Path.home() / ".personalkm/PersonalKM-worker"))
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    logger.info("Scanning vault: %s", vault)
    logger.info("Mode: %s", "DRY RUN" if args.dry_run else "LIVE")

    stats = run(vault, dry_run=args.dry_run)

    print()
    print("=" * 50)
    print("FRONTMATTER NORMALISATION COMPLETE")
    print("=" * 50)
    print("  Vault:          %s" % vault)
    print("  Scanned:        %s files" % stats["scanned"])
    print("  Changed:        %s files" % stats["changed"])
    print("  Tag format fix: %s" % stats["tag_format_fixed"])
    print("  Dedup fix:      %s" % stats["dedup_fixed"])
    print("  Errors:         %s" % stats["errors"])
    if stats["files"]:
        print("  Modified files:")
        for f in stats["files"]:
            print("    - %s" % f)
    print("=" * 50)

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())