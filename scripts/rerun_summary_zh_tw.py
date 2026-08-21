"""Re-generate Summary + Key Facts for lifestyle vault wiki pages in zh-TW.

Only the two prose sections are replaced (via the updated ingest_synthesis
prompt); frontmatter, topic/tags, and the Source section are preserved.
Each page = 1 LLM call (deepseek primary). Usage:

    python scripts/rerun_summary_zh_tw.py --vault ~/Documents/PersonalKM/Personalkm-lifestyle-vault [--limit 5]
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("rerun_summary")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from personalkm.ingest.ingestion_v2 import _SYNTHESIS_USER_PROMPT, _SYNTHESIS_SYSTEM_PROMPT
from personalkm.llm.router import route

MAX_CONTENT = 8000


def find_raw_content(vault: Path, sources: list[str]) -> str | None:
    """Locate the raw note referenced by frontmatter sources and read its body."""
    for src in sources:
        # [[Archive/raw/Food/2026-08-20-...-note]] → relative path + .md
        name = src.strip().strip("[]").strip()
        if not name:
            continue
        rel = Path(name)
        for candidate in (vault / f"{rel}.md", vault / rel / ".md"):
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8", errors="replace")
                # Strip frontmatter for clean body
                m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
                return (m.group(1) if m else text).strip()
    return None


def rewrite_sections(markdown: str, summary: str, key_facts: list[str]) -> str:
    """Replace the ## Summary / ## Key Facts blocks, keep everything else."""
    facts_block = "\n".join(f"- {f.strip()}" for f in key_facts if f.strip()) if key_facts else ""

    def replace_section(text: str, heading: str, new_body: str) -> str:
        pattern = rf"(## {heading}\n\n).*?(?=\n## |\n\*\*Source:\*\*|\Z)"
        replacement = rf"\1{new_body}\n"
        new_text, n = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
        if n == 0:
            # No existing section — append before Source if present, else at end
            new_text = text
        return new_text

    md = replace_section(markdown, "Summary", summary.strip())
    md = replace_section(md, "Key Facts", facts_block)
    return md


def is_zh_summary(markdown: str) -> bool:
    """True if the ## Summary section already contains CJK characters."""
    m = re.search(r"## Summary\n\n(.+?)(?=\n## |\n\*\*Source:\*\*|\Z)", markdown, re.DOTALL)
    if not m:
        return False
    summary = m.group(1)
    return any("\u4e00" <= ch <= "\u9fff" for ch in summary)


def process_page(vault: Path, page: Path) -> dict:
    text = page.read_text(encoding="utf-8", errors="replace")
    fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not fm_match:
        return {"path": str(page), "status": "skip", "reason": "no frontmatter"}
    frontmatter, body = fm_match.group(1), fm_match.group(2)

    # Already in Chinese — skip (avoids re-calling the LLM on re-runs)
    if is_zh_summary(body):
        return {"path": str(page), "status": "skip", "reason": "already zh-TW"}

    # Parse sources list
    sources = re.findall(r"^\s*-\s*\[\[(.+?)\]\]\s*$", frontmatter, re.MULTILINE)

    content = find_raw_content(vault, sources) or body
    content = content[:MAX_CONTENT]
    if len(content) < 50:
        return {"path": str(page), "status": "skip", "reason": f"content too short ({len(content)}c)"}

    page_type = "concept" if "/concepts/" in str(page) else "entity"
    prompt = _SYNTHESIS_USER_PROMPT.format(page_type=page_type, source_path=str(page), content=content)
    try:
        result = route("ingest_synthesis", prompt, system=_SYNTHESIS_SYSTEM_PROMPT, expect_json=True)
    except Exception as e:
        return {"path": str(page), "status": "error", "reason": f"{e.__class__.__name__}: {e}"}

    if not isinstance(result, dict) or not result.get("summary"):
        return {"path": str(page), "status": "error", "reason": f"empty result: {result!r}"}

    new_body = rewrite_sections(body, result["summary"], result.get("key_facts", []))
    if new_body == body:
        return {"path": str(page), "status": "skip", "reason": "no change"}

    # Update `updated:` date
    new_fm = re.sub(r"^updated:.*$", f"updated: {page.name[:10] if False else '2026-08-21'}", frontmatter, count=1, flags=re.MULTILINE)
    page.write_text(f"---\n{new_fm}\n---\n{new_body}", encoding="utf-8")
    return {"path": str(page), "status": "done", "summary_len": len(result["summary"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    pages = sorted(
        [p for p in (vault / "wiki" / "entities").glob("*.md")]
        + [p for p in (vault / "wiki" / "concepts").glob("*.md")]
    )
    log.info("Found %d wiki pages in %s", len(pages), vault)

    done = skipped = errors = 0
    for i, page in enumerate(pages):
        if args.limit and i >= args.limit:
            break
        r = process_page(vault, page)
        if r["status"] == "done":
            done += 1
            log.info("  ✅ %s (%s chars)", r["path"].split("/")[-1][:60], r["summary_len"])
        elif r["status"] == "error":
            errors += 1
            log.warning("  ❌ %s — %s", r["path"].split("/")[-1][:60], r["reason"])
        else:
            skipped += 1
            log.info("  ⏭️  %s — %s", r["path"].split("/")[-1][:60], r.get("reason", ""))

    log.info("DONE: %d regenerated, %d skipped, %d errors", done, skipped, errors)


if __name__ == "__main__":
    main()