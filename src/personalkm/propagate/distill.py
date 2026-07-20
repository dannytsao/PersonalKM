"""Entity/concept page distillation — SPEC.md "Entity Distillation Loop".

Status (2026-07-20): dry-run (preview_distillation/scan_for_candidates) plus
fold-preserve write-back (apply_distillation). Write-back is opt-in only —
scripts/distill_entities.py requires an explicit --apply flag and per-page
confirmation; nothing here writes on its own. Retention is fold-preserve
(2026-07-19 decision): the AI summary goes on top, the entire pre-existing
body is preserved untouched inside a collapsed <details> block — nothing is
ever deleted, so a bad summary can't destroy the original captures.

Trigger conditions are a simplified subset of SPEC.md's distill_trigger:
captures_threshold and max_age_days are implemented; decay_score_threshold
is intentionally omitted. The existing knowledge_decay.py freshness model
is keyed on DevOps/AI keyword categories for tech-note staleness and doesn't
map cleanly onto arbitrary entity/concept pages, so it's left as an open
follow-up rather than force-fit here.

Known simplification: if a page is distilled more than once, the new fold
wraps around a body that already contains a previous fold, so nesting depth
grows by one <details> layer per distillation cycle. Not addressed here —
in practice cycles are infrequent (captures_threshold=5 or 30 days) and this
would only matter after many repeated cycles on the same page.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from personalkm.llm.router import route

CAPTURES_THRESHOLD = 5
MAX_AGE_DAYS = 30

# Matches both capture-heading shapes actually written in production:
# "## Title (2026-07-19)" (ingestion_v2.py primary merge) and
# "### Title (2026-07-19)" (canonical merge / _add_capture_to_entity).
_CAPTURE_HEADING_RE = re.compile(r"^#{2,3}\s+.+\(\d{4}-\d{2}-\d{2}\)\s*$", re.MULTILINE)

# Splits body into one chunk per capture: from a dated heading up to the next
# dated heading (or end of string), so we can look for that capture's inline
# "Source: [[...]]" line within its own chunk only.
# NOTE: the heading portion uses [^\n]* (not '.'/DOTALL) so a greedy match
# can never swallow past its own line into the next heading — with DOTALL
# on, a plain '.+' here would happily eat all the way to the LAST "(date)$"
# in the body before backtracking, merging every capture into one "block".
_CAPTURE_BLOCK_RE = re.compile(
    r"^#{2,3}[ \t]+[^\n]*\((\d{4}-\d{2}-\d{2})\)[ \t]*$(.*?)"
    r"(?=^#{2,3}[ \t]+[^\n]*\(\d{4}-\d{2}-\d{2}\)[ \t]*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SOURCE_LINE_RE = re.compile(r"^Source:\s*(\[\[.+?\]\])\s*$", re.MULTILINE)
# Tolerates both half-width () and full-width （） parens — the prompt asks
# for half-width to match capture headings exactly, but LLMs don't always
# follow punctuation-width instructions precisely.
_FACT_TRAILING_DATE_RE = re.compile(r"[（(](\d{4}-\d{2}-\d{2})[）)]\s*$")


def extract_capture_sources(body: str) -> dict[str, str]:
    """Map each capture's date to its 'Source: [[...]]' backlink, if present.

    Only ingestion_v2.py's merge paths write an inline Source line per capture
    (added 2026-07-19 alongside this traceability feature) — captures merged
    before that change, or a page's very first capture (which has no dated
    heading at all, just the frontmatter's sources: list), won't resolve here.
    Callers must treat a missing mapping as "no backlink available", not
    an error.
    """
    sources: dict[str, str] = {}
    for date_str, block in _CAPTURE_BLOCK_RE.findall(body):
        m = _SOURCE_LINE_RE.search(block)
        if m:
            sources[date_str] = m.group(1)
    return sources


def attach_source_links(key_facts: list[str], body: str) -> list[str]:
    """Append a traceable '→ [[source]]' backlink to each fact whose trailing
    (YYYY-MM-DD) date matches a capture we can resolve back to its raw note.
    Facts with no resolvable source are returned unchanged, not dropped.
    """
    sources = extract_capture_sources(body)
    annotated = []
    for fact in key_facts:
        m = _FACT_TRAILING_DATE_RE.search(fact)
        link = sources.get(m.group(1)) if m else None
        annotated.append(f"{fact} → {link}" if link else fact)
    return annotated

DISTILL_SYSTEM_PROMPT = (
    "你是個人知識庫的整理助手。請一律使用繁體中文（台灣用語習慣）回覆，"
    "不要使用簡體字。只輸出合法 JSON，不要加任何說明文字或 markdown code fence。"
)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse frontmatter as plain key: value lines (first colon only).

    Deliberately not yaml.safe_load(): real captured titles routinely contain
    unescaped colons (e.g. "... on Instagram: \"...\"") and aren't quoted when
    written, which is invalid YAML — the same reason
    personalkm.query.query_engine._parse_frontmatter avoids a real YAML parse
    too. Every field distill.py reads (title/created/last_distilled) is a
    scalar, so this is sufficient — no need for real YAML semantics here.
    """
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm: dict = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, parts[2]


def count_captures(body: str) -> int:
    """Count '## Title (YYYY-MM-DD)' / '### Title (YYYY-MM-DD)' capture entries."""
    return len(_CAPTURE_HEADING_RE.findall(body))


@dataclass
class DistillationCheck:
    should_trigger: bool
    reason: str
    captures_count: int
    age_days: Optional[int]


def check_trigger(fm: dict, body: str, today: Optional[date] = None) -> DistillationCheck:
    today = today or date.today()
    captures_count = count_captures(body)
    if captures_count >= CAPTURES_THRESHOLD:
        return DistillationCheck(
            True, f"captures_count {captures_count} >= {CAPTURES_THRESHOLD}",
            captures_count, None,
        )

    anchor_str = fm.get("last_distilled") or fm.get("created")
    age_days = None
    if anchor_str:
        try:
            anchor = datetime.fromisoformat(str(anchor_str)[:10]).date()
            age_days = (today - anchor).days
            if age_days >= MAX_AGE_DAYS:
                return DistillationCheck(
                    True, f"age_days {age_days} >= {MAX_AGE_DAYS}",
                    captures_count, age_days,
                )
        except ValueError:
            pass

    return DistillationCheck(False, "no trigger condition met", captures_count, age_days)


def build_distillation_prompt(title: str, body: str) -> str:
    return f"""這是個人知識庫裡「{title}」這個主題累積的所有 capture 全文。
請把這些內容濃縮成一段更新後的知識摘要，供之後快速回顧使用。

規則：
- 所有具體日期、數字、URL、專有名詞必須逐字保留，不可意譯或省略
- 摘要要能涵蓋目前累積的所有重點，不是只挑一則 capture
- key_facts 每一條的結尾都必須附上該筆重點來源 capture 的日期，格式為半形括號 (YYYY-MM-DD)，不可用全形括號、不可省略日期
- 只用 JSON 格式輸出，欄位為 summary（一段文字）與 key_facts（字串陣列）

原始內容：
{body}

輸出 JSON："""


@dataclass
class DistillationPreview:
    path: Path
    title: str
    triggered: bool
    reason: str
    captures_count: int
    proposed_summary: Optional[str] = None
    proposed_key_facts: Optional[list] = None
    error: Optional[str] = None


def preview_distillation(path: Path, call_llm: bool = True) -> DistillationPreview:
    """Compute whether *path* would trigger distillation, and preview the
    LLM's proposed summary. Never writes anything back to *path*."""
    content = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(content)
    title = fm.get("title", path.stem)
    check = check_trigger(fm, body)

    preview = DistillationPreview(
        path=path, title=title, triggered=check.should_trigger,
        reason=check.reason, captures_count=check.captures_count,
    )
    if check.should_trigger and call_llm:
        try:
            result = route(
                "entity_distillation",
                build_distillation_prompt(title, body),
                system=DISTILL_SYSTEM_PROMPT,
                expect_json=True,
            )
            preview.proposed_summary = result.get("summary")
            key_facts = result.get("key_facts") or []
            preview.proposed_key_facts = attach_source_links(key_facts, body)
        except Exception as e:
            preview.error = str(e)
    return preview


def scan_for_candidates(wiki_path: Path, call_llm: bool = True) -> list[DistillationPreview]:
    """Scan wiki/entities/ + wiki/concepts/ for pages that trigger distillation."""
    previews = []
    for subdir in ("entities", "concepts"):
        dir_path = wiki_path / subdir
        if not dir_path.exists():
            continue
        for fpath in sorted(dir_path.glob("*.md")):
            preview = preview_distillation(fpath, call_llm=call_llm)
            if preview.triggered:
                previews.append(preview)
    return previews


def _get_int_field(fm_text: str, key: str) -> int:
    m = re.search(rf"^{re.escape(key)}:\s*(\d+)\s*$", fm_text, re.MULTILINE)
    return int(m.group(1)) if m else 0


def _set_field(fm_text: str, key: str, value: str) -> str:
    """Set `key: value` in a frontmatter block, appending if the key is
    missing. Only touches this one field's line — deliberately not a full
    reparse/rebuild of the frontmatter, because distill.py's own
    _parse_frontmatter() drops multi-line YAML values (sources:/tags: lists)
    when it reads line-by-line; rebuilding from that dict would silently
    delete them. Same lesson as the post_link_ollama.py regex fix: match the
    whole line (`.*$`), never just part of it.
    """
    pattern = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
    if pattern.search(fm_text):
        return pattern.sub(f"{key}: {value}", fm_text, count=1)
    return fm_text.rstrip("\n") + f"\n{key}: {value}"


def apply_distillation(path: Path, preview: DistillationPreview) -> bool:
    """Write preview's proposed summary back to *path*, fold-preserve style:
    the summary goes on top, the entire existing body is kept verbatim
    inside a collapsed <details> block. Returns True if written.

    Only meaningful when preview.triggered and preview.proposed_summary is
    set (i.e. the LLM call in preview_distillation() succeeded) — callers
    should check preview.error first and skip pages where it's set.
    """
    if not preview.triggered or not preview.proposed_summary:
        return False

    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    fm_text, body = parts[1], parts[2]

    today = date.today().isoformat()
    distill_count = _get_int_field(fm_text, "distill_count") + 1

    fm_text = _set_field(fm_text, "last_distilled", today)
    fm_text = _set_field(fm_text, "distill_count", str(distill_count))
    fm_text = _set_field(fm_text, "captures_count", str(preview.captures_count))
    fm_text = _set_field(fm_text, "active_captures", "0")
    fm_text = _set_field(fm_text, "updated", today)

    key_facts = preview.proposed_key_facts or []
    key_facts_md = "\n".join(f"- {fact}" for fact in key_facts)
    summary_section = f"## 濃縮摘要（{today}）\n\n{preview.proposed_summary}\n"
    if key_facts_md:
        summary_section += f"\n{key_facts_md}\n"

    folded = (
        f"<details>\n"
        f"<summary>原始 Captures（點擊展開，共 {preview.captures_count} 筆，"
        f"最後濃縮於 {today}）</summary>\n\n"
        f"{body.strip()}\n\n"
        f"</details>\n"
    )

    new_content = f"---{fm_text}---\n\n{summary_section}\n{folded}"
    path.write_text(new_content, encoding="utf-8")
    return True
