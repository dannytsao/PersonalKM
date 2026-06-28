#!/usr/bin/env python3
"""
Sanity Check & Repair for the PersonalKM Vault
===============================================
Repair-first: fixes frontmatter issues, flattens tags, cleans sources,
normalises paths.  Warns about structural issues but never deletes files.

Usage:
    python scripts/sanity_check.py                          # full scan + repair
    python scripts/sanity_check.py --check-only              # don't repair
    python scripts/sanity_check.py --vault /path/to/vault    # custom vault path
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("sanity_check")
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
    stream=sys.stderr,
)

VAULT_DEFAULT = Path(os.getenv("VAULT_PATH", str(Path.home() / "Documents/PersonalKM")))

# ── helpers ────────────────────────────────────────────────────────────────


def _parse_frontmatter(text: str) -> Tuple[Optional[str], str, List[str]]:
    """
    Attempt to split *text* into (raw_frontmatter, body, errors).
    Returns (fm, body, errors) where *errors* lists what went wrong.
    """
    errors: List[str] = []
    stripped = text.lstrip("\n")  # blank lines before frontmatter

    if stripped.startswith("---"):
        # Standard delimited frontmatter
        end = stripped.find("\n---", 3)
        if end == -1:
            errors.append("Opening --- found but no closing ---")
            return (None, text, errors)
        fm = stripped[3:end].strip()
        body = stripped[end + 4 :]
        return (fm, body, errors)

    # No opening ---: check if the file LOOKS like it has undelimited frontmatter
    # (starts with key: value lines that could be YAML)
    lines = stripped.split("\n")
    fm_lines: List[str] = []
    body_lines: List[str] = []
    in_fm = False
    seen_key_value = False

    for line in lines:
        if re.match(r"^\w[\w-]*\s*:", line):
            if not in_fm:
                in_fm = True
            fm_lines.append(line)
            seen_key_value = True
        elif in_fm and line.strip() == "":
            fm_lines.append(line)
        elif in_fm and (line.startswith(" ") or line.startswith("\t")):
            fm_lines.append(line)
        elif in_fm and line.strip().startswith("["):
            fm_lines.append(line)
        elif line.strip() == "---":
            body_lines.append(line)
            in_fm = False
        elif in_fm:
            fm_lines.append(line)
        else:
            body_lines.append(line)

    if fm_lines and seen_key_value:
        errors.append("Missing opening --- delimiter (frontmatter present but undelimited)")
        fm = "\n".join(fm_lines)
        body = "\n".join(body_lines)
        return (fm, body, errors)

    return (None, text, errors)


def _add_frontmatter_delimiter(text: str) -> str:
    """Prepend ``---\\n`` if the file has undelimited frontmatter."""
    stripped = text.lstrip("\n")
    if stripped.startswith("---"):
        return text  # already delimited
    # Check if it looks like frontmatter (has YAML key: value before a --- line)
    if re.search(r"^\w[\w-]*\s*:", stripped, re.MULTILINE):
        # Add --- at the very start
        return "---\n" + stripped
    return text


def _flatten_nested_tags(fm_text: str) -> (str, bool):
    """Replace nested tags like ``[['a','b'], ['c','d']]`` with proper YAML list."""
    changed = False

    def _extract_list_items(raw: str) -> list[str]:
        """Extract all string items from a YAML-ish list representation."""
        items = []
        for m in re.finditer(r"'([^']*)'|\"([^\"]*)\"|([a-zA-Z0-9_/-]+)", raw):
            items.append(m.group(1) or m.group(2) or m.group(3))
        return items

    def _replace_tags(m: re.Match) -> str:
        nonlocal changed
        lead = m.group(1)
        indent = m.group(2)
        raw = m.group(3)
        items = _extract_list_items(raw)
        seen = set()
        deduped = []
        for item in items:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        if not deduped:
            return m.group(0)
        changed = True
        rest = "tags:\n" + "\n".join(f"{indent}  - {item}" for item in deduped)
        return lead + indent + rest

    # Match: tags:\n  [[...], [...]]   or   tags: [[...], [...]]
    fm_text = re.sub(
        r"(^|\n)(\s*)tags:\s*(\[(?:\[[^\]]*\],?\s*)+\])\s*$",
        _replace_tags,
        fm_text,
        count=1,
        flags=re.MULTILINE,
    )

    return fm_text, changed


def _clean_sources(fm_text: str) -> (str, bool):
    """Remove empty-string entries from sources, and fix absolute paths to relative."""
    changed = False

    def _parse_inline_list(text: str, indent: str) -> (str, bool):
        """Convert ``[\\"a\\", \\"b\\"]`` into proper YAML list items."""
        items = re.findall(r'"([^"]*)"', text)
        items = [it for it in items if it.strip()]
        if not items:
            return f"{indent}sources: []", bool(re.findall(r'"([^"]*)"', text))
        return f"{indent}sources:\n" + "\n".join(f'{indent}  - "{it}"' for it in items), True

    lines = fm_text.split("\n")
    new_lines: List[str] = []
    in_sources = False
    source_indent = ""

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("sources:"):
            in_sources = True
            source_indent = line[: len(line) - len(line.lstrip())]

            # Inline sources:  sources: [""] or sources: ["a", "b"]
            inline_m = re.match(r"(\s*)sources:\s*(\[.*\])\s*", line)
            if inline_m:
                replacement, ch = _parse_inline_list(stripped, source_indent)
                new_lines.append(replacement)
                if ch:
                    changed = True
                in_sources = False
                continue

            new_lines.append(line)
            continue

        if in_sources:
            # Indented bracket list:   [""]  or  ["a", "b"]
            if stripped.startswith("[") and stripped.endswith("]"):
                replacement, ch = _parse_inline_list(stripped, source_indent)
                new_lines.append(replacement)
                if ch:
                    changed = True
                in_sources = False
                continue

            # Standard YAML list item:  - "value"
            if stripped.startswith("-"):
                m = re.match(r'\s*-\s*"([^"]*)"', line)
                if m:
                    val = m.group(1).strip()
                    if val == "":
                        changed = True
                        continue  # skip empty
                    fixed = _fix_source_path(val, source_indent)
                    if fixed != val:
                        changed = True
                        new_lines.append(f'{source_indent}  - "{fixed}"')
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
                continue

            # End of sources block (non-empty, non-indented line)
            if stripped and not stripped.startswith("#"):
                in_sources = False
                new_lines.append(line)
                continue

            new_lines.append(line)
            continue

        new_lines.append(line)

    # Ensure sources key exists
    result = "\n".join(new_lines)
    if not re.search(r"^sources:", result, re.MULTILINE):
        result = result.rstrip("\n") + f"\nsources: []"
        changed = True

    return result, changed


def _fix_source_path(val: str, indent: str) -> str:
    """Convert absolute paths to relative raw/ paths."""
    # /Users/dannytsao/.../raw/... → raw/...
    # /tmp/personal-km-vault/raw/... → raw/...
    m = re.search(r"/(?:raw|wiki)/", val)
    if m:
        idx = m.start() + 1  # +1 to include the leading /
        return val[idx:]
    return val


def _clean_extra_fields(fm_text: str) -> (str, bool):
    """Remove non-schema fields like ``wikilink_processed``."""
    changed = False
    lines = fm_text.split("\n")
    new_lines: List[str] = []
    for line in lines:
        if re.match(r"\s*wikilink_processed\s*:", line):
            changed = True
            continue
        new_lines.append(line)
    return "\n".join(new_lines), changed


def _ensure_date_fields(fm_text: str, filename_stem: str) -> (str, bool):
    """Add ``created`` / ``updated`` if missing."""
    changed = False
    today = datetime.now().strftime("%Y-%m-%d")

    if not re.search(r"^created:\s*\d{4}-\d{2}-\d{2}", fm_text, re.MULTILINE):
        # Try to infer from filename YYYY-MM-DD prefix
        m = re.match(r"(\d{4}-\d{2}-\d{2})", filename_stem)
        date_str = m.group(1) if m else today
        fm_text = fm_text.rstrip("\n") + f"\ncreated: {date_str}"
        changed = True

    if not re.search(r"^updated:\s*\d{4}-\d{2}-\d{2}", fm_text, re.MULTILINE):
        fm_text = fm_text.rstrip("\n") + f"\nupdated: {today}"
        changed = True

    return fm_text, changed


def _ensure_type(fm_text: str, subfolder: str) -> (str, bool):
    """Add ``type`` if missing; log mismatch as warning (handled by caller)."""
    if re.search(r"^type:\s*\w+", fm_text, re.MULTILINE):
        return fm_text, False
    inferred = subfolder.rstrip("s")  # entities → entity, concepts → concept
    # But the schema uses "entity" and "concept"
    subfolder_map = {"entities": "entity", "concepts": "concept"}
    typ = subfolder_map.get(subfolder, "concept")
    fm_text = fm_text.rstrip("\n") + f"\ntype: {typ}"
    return fm_text, True


# ── per-file logic ─────────────────────────────────────────────────────────


def check_and_repair(page: Path, check_only: bool = False) -> dict:
    """
    Inspect a single wiki page.  Returns dict with status, fixes, warnings.
    """
    result = {
        "path": str(page.relative_to(page.parents[2])),  # relative to vault root
        "status": "ok",
        "fixes": [],
        "warnings": [],
    }

    text = page.read_text(encoding="utf-8")
    orig_text = text
    subfolder = page.parent.name  # "entities" or "concepts"

    # ── 1. Fix missing --- delimiter ──
    fixed = _add_frontmatter_delimiter(text)
    if fixed != text:
        result["fixes"].append("Added missing opening --- frontmatter delimiter")
        text = fixed

    # ── 2. Re-parse frontmatter ──
    fm, body, parse_errors = _parse_frontmatter(text)
    if fm is None:
        result["status"] = "cannot-parse"
        for e in parse_errors:
            result["warnings"].append(f"Frontmatter parse error: {e}")
        return result

    for e in parse_errors:
        result["warnings"].append(e)

    # ── 3. Repair tags (nested brackets) ──
    fm, tags_changed = _flatten_nested_tags(fm)
    if tags_changed:
        result["fixes"].append("Flattened nested bracket tags → proper YAML list")

    # ── 4. Clean sources ──
    fm, sources_changed = _clean_sources(fm)
    if sources_changed:
        result["fixes"].append("Cleaned empty sources entries")

    # ── 5. Remove extra non-schema fields ──
    fm, extra_changed = _clean_extra_fields(fm)
    if extra_changed:
        result["fixes"].append("Removed non-schema field: wikilink_processed")

    # ── 6. Ensure required date fields ──
    fm, dates_changed = _ensure_date_fields(fm, page.stem)
    if dates_changed:
        result["fixes"].append("Added missing created/updated date field(s)")

    # ── 7. Ensure type field ──
    fm, type_changed = _ensure_type(fm, subfolder)
    if type_changed:
        result["fixes"].append(f"Added missing type field (inferred: {subfolder})")

    # ── 8. Type/directory mismatch (warn only) ──
    type_match = re.search(r"^type:\s*(\w+)", fm, re.MULTILINE)
    if type_match:
        declared_type = type_match.group(1)
        expected = {"entities": "entity", "concepts": "concept"}.get(subfolder, "")
        if expected and declared_type != expected:
            result["warnings"].append(
                f"Type mismatch: declared '{declared_type}' but file lives in '{subfolder}/'"
            )

    # ── 9. Auto-promoted stub detection (warn only) ──
    if "## Mentions" in body and "## Key Facts" not in body and "## Captures" not in body:
        result["warnings"].append("Auto-promoted stub — has ## Mentions but no ## Key Facts or ## Captures")

    # ── 10. Sources point to wiki pages not raw files (warn only) ──
    src_refs = re.findall(r'^\s+-\s+"([^"]*)"', fm, re.MULTILINE)
    for src in src_refs:
        if src.startswith("wiki/") or src.startswith("/tmp/"):
            result["warnings"].append(f"Source points to '{src}' — expected 'raw/...' path")
            break  # one warning per file is enough

    # ── apply fixes ──
    if result["fixes"] and not check_only:
        # Reconstruct the file: frontmatter block + body
        new_text = f"---\n{fm.strip()}\n---\n{body}"
        page.write_text(new_text, encoding="utf-8")

    if result["fixes"]:
        result["status"] = "repaired"
    if result["warnings"] and result["status"] == "ok":
        result["status"] = "warnings"

    return result


# ── main ───────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sanity check & repair for PersonalKM vault")
    parser.add_argument("--vault", default=str(VAULT_DEFAULT), help="Vault root path")
    parser.add_argument("--check-only", action="store_true", help="Only check, don't repair")
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    if not vault.exists():
        logger.error(f"Vault not found: {vault}")
        sys.exit(1)

    pages: List[Path] = []
    for sub in ("entities", "concepts"):
        path = vault / "wiki" / sub
        if path.exists():
            pages.extend(sorted(path.glob("*.md")))

    if not pages:
        logger.info("No wiki pages found")
        return

    totals = {"ok": 0, "repaired": 0, "warnings": 0, "cannot-parse": 0}
    all_warnings: List[str] = []
    all_fixes: List[str] = []

    for p in pages:
        r = check_and_repair(p, check_only=args.check_only)
        totals[r["status"]] = totals.get(r["status"], 0) + 1
        for w in r["warnings"]:
            all_warnings.append(f"  ⚠  {r['path']}: {w}")
        for f in r["fixes"]:
            all_fixes.append(f"  ✓  {r['path']}: {f}")

    # ── report ──
    mode = "CHECK ONLY" if args.check_only else "REPAIR"
    logger.info("=" * 70)
    logger.info(f"SANITY CHECK ({mode}) — {len(pages)} pages")
    logger.info("=" * 70)

    if all_fixes:
        logger.info(f"\nFixes applied ({len(all_fixes)}):")
        for line in all_fixes:
            logger.info(line)

    if all_warnings:
        logger.info(f"\nWarnings ({len(all_warnings)}):")
        for line in all_warnings:
            logger.info(line)

    logger.info("\nSummary:")
    logger.info(f"  OK:             {totals['ok']}")
    logger.info(f"  Repaired:       {totals['repaired']}")
    logger.info(f"  Warnings:       {totals['warnings']}")
    logger.info(f"  Cannot parse:   {totals['cannot-parse']}")

    if totals["cannot-parse"] > 0:
        logger.warning("\n⚠  Some pages could not be parsed — manual review needed")

    return totals["cannot-parse"] + totals["repaired"]


if __name__ == "__main__":
    # Ensure the 'bot' package is importable
    repo_root = Path(__file__).parent.parent.resolve()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    sys.exit(main())
