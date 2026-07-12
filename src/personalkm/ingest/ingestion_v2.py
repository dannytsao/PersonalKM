"""
LLM-Wiki v2 Ingestion Pipeline
==============================
Integrated pipeline: Phase 1 (MiniMax) + Phase 2 (Summarization) + Phase 3 (Dedup) + Phase 4 (Wikilinks)

Data flow:
    raw/*.md → ingest_raw_to_wiki()
        ├── ContentQualityChecker (filter low-quality)
        ├── _synthesize_wiki_note() (personalkm.llm.router.route: topic + tags + summary)
        ├── detect_entity_mentions() (Phase 2: extract entity names)
        ├── EntityRegistry.find_entity_match() (Phase 3: dedup check)
        ├── distill_to_markdown() (Phase 2: wiki format)
        ├── write_to_wiki() (create or merge)
        ├── WikilinkManager.add_bidirectional_links() (Phase 4)
        └── IngestionHealthCheck (post-ingest validation)

Usage:
    from personalkm.ingest.ingestion_v2 import ingest_raw_to_wiki, ingest_file_v2
    result = ingest_raw_to_wiki(Path('/path/to/vault'))
"""

import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

from personalkm.propagate.entity_dedup import EntityRegistry, normalize_entity_name, canonical_slug_from_name
from personalkm.ingest.llm_summarizer import distill_to_markdown, detect_entity_mentions, _strip_frontmatter
from personalkm.propagate.wikilinks import WikilinkManager
from personalkm.llm.router import route

logger = logging.getLogger(__name__)

# Lazy-initialized singletons (built once per vault, reused across files)
_vault_registry: Dict[Path, EntityRegistry] = {}
_vault_wikilinks: Dict[Path, WikilinkManager] = {}


def _get_registry(wiki_path: Path) -> EntityRegistry:
    """Get or create EntityRegistry for a vault."""
    if wiki_path not in _vault_registry:
        _vault_registry[wiki_path] = EntityRegistry(wiki_path)
    return _vault_registry[wiki_path]


def _get_wikilinks(wiki_path: Path) -> WikilinkManager:
    """Get or create WikilinkManager for a vault."""
    if wiki_path not in _vault_wikilinks:
        registry = _get_registry(wiki_path)
        _vault_wikilinks[wiki_path] = WikilinkManager(wiki_path, registry)
    return _vault_wikilinks[wiki_path]


# ─────────────────────────────────────────────────────────────
# Content Quality Filtering
# ─────────────────────────────────────────────────────────────

LOW_QUALITY_PATTERNS = [
    "wait loading",
    "404",
    "page not found",
    "just a moment",
    "checking your browser",
    "enable javascript",
    "sign in to",
    "login to",
    "subscribe to",
    "subscription required",
    "paywall",
    "advertisement",
    # Fetch failure patterns — notes that tried but failed to retrieve content
    "http 40",
    "http 41",
    "http 42",
    "http 50",
    "http error",
    "failed to fetch",
    "failed to retrieve",
    "could not fetch",
    "could not retrieve",
    "unable to fetch",
    "unable to retrieve",
    "retrieval failed",
    "extraction failed",
    "website returned an error",
    "cannot be accessed",
    "content not accessible",
    "error fetching",
]


def is_low_quality(content: str) -> Tuple[bool, str]:
    """Return (True, reason) if content is low-quality."""
    lower = content.lower()
    for pattern in LOW_QUALITY_PATTERNS:
        if pattern in lower:
            return True, f"Matched low-quality pattern: {pattern!r}"
    if len(content.strip()) < 50:
        return True, "Content too short (< 50 chars)"
    return False, ""


# ─────────────────────────────────────────────────────────────
# Topic Options
# ─────────────────────────────────────────────────────────────

TOPIC_OPTIONS = [
    "AI-Agent-&-Tools",
    "Automation-Workflows",
    "PKM-&-System-Design",
    "Tech-Trends-&-Insights",
    "Personal-Interests",
]


# ─────────────────────────────────────────────────────────────
# Title Extraction
# ─────────────────────────────────────────────────────────────

def extract_title(raw_path: Path, content: str, max_len: int = 120) -> str:
    """Extract a clean human-readable title from a raw capture.

    Priority:
      1. First H1 (`^#`) in the body — returned verbatim (NOT slugified here;
         slugification happens later via normalize_entity_name where needed).
         H1 is the natural title of YouTube/web/article captures.
      2. First non-section, non-frontmatter line of body (legacy fallback).
      3. Filename stem with date/log-id prefixes stripped.

    Skips:
      - YAML frontmatter (already stripped by _strip_frontmatter)
      - `## Log ID` block AND its body (always a log_id timestamp, not a title)
      - `## ` / `### ` section headers (NOT headings stripped to their text —
        these are metadata labels like `## 摘要`, `## 內含連結` and would
        pollute the title with section names)
      - Frontmatter-like `key: value` lines, all-caps noise

    Args:
        max_len: hard cap on returned length — long H1s are truncated with `…`
                 so canonical_slug_from_name can still match.
    """
    body = _strip_frontmatter(content)

    # 1) Prefer first H1 line — it's the actual page title from the source.
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            title = s.lstrip("# ").strip()
            if title:
                # Don't slugify here — keep the human-readable string for both
                # frontmatter `title:` and canonical_slug_from_name().
                if len(title) > max_len:
                    title = title[: max_len - 1].rstrip() + "…"
                return title

    # 2) Walk the body, skipping `## Log ID` + its body, skipping all
    #    `##` / `###` section headers, and any frontmatter-detect line.
    skip_until_blank = False
    for line in body.split("\n")[:40]:
        s = line.strip()
        if not s:
            skip_until_blank = False
            continue
        # H2/H3 — never a title; treat `## Log ID` as a "skip its body too" trigger.
        if s.startswith("## ") or s.startswith("### "):
            if s.lstrip("#").strip().lower() == "log id":
                skip_until_blank = True
            continue
        if skip_until_blank:
            continue
        if s.startswith("---"):
            continue
        # Skip YAML-ish `key: value` lines that survive frontmatter stripping
        # (e.g. orphaned metadata). Allow `:` inside the value, but bail on
        # a leading `key:` look.
        if re.match(r"^[A-Za-z_][\w-]*\s*:", s):
            continue
        if s.isupper() or len(s) <= 5:
            continue
        candidate = s.lstrip("#").strip()
        if 5 < len(candidate) <= max_len:
            return candidate

    # 3) Fall back to filename stem with known prefixes stripped.
    name = raw_path.stem
    name = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]", "", name)
    name = re.sub(r"^\d{10,}[-_]", "", name)
    name = re.sub(r"^\d{6,}[-_]", "", name)
    name = name.replace("-", " ").replace("_", " ")
    return name.strip() or "untitled"


# ─────────────────────────────────────────────────────────────
# Page Type Classification
# ─────────────────────────────────────────────────────────────

# Keywords that strongly indicate a CONCEPT (topic/method/how-to) page
# vs an ENTITY (named product, tool, company, person) page
_CONCEPT_KEYWORDS = [
    "how to", "tutorial", "教學", "教您", "步驟", "方法",
    "guide", "introduction to", "overview of", "what is", "什麼是",
    "comparison", "比較", "vs ", " versus ", "difference between",
    "review", "心得", "開箱", "使用心得",
    "最佳化", "優化", "設定", "配置",
    "setup", "install", "configuration", "getting started",
    "understanding", "explained", "原理", "概念",
    "攻略", "完整攻略", "新手攻略", "懶人包",
]

# Keywords that strongly indicate an ENTITY page
_ENTITY_KEYWORDS = [
    "announced", "released", "launched", "update",
    "公司", "產品", "發表", "推出", "更新",
    "version", "beta", "release notes", "changelog",
    "pricing", "價格", "收費",
    "api", "sdk", "library", "framework",
]


def _classify_page_type(body: str) -> str:
    """
    Classify whether content should be treated as 'entity' or 'concept'.

    Heuristic-based (no LLM call needed):
    - Concept: how-to, tutorials, comparisons, explainers, personal reviews
    - Entity: product launches, company news, pricing, API/tool releases

    SCHEMA:
      entities/ = people, products, organizations, specific named tools
      concepts/ = topics, methods, techniques, how-to guides
    """
    lower = body.lower()

    concept_score = sum(1 for kw in _CONCEPT_KEYWORDS if kw in lower)
    entity_score = sum(1 for kw in _ENTITY_KEYWORDS if kw in lower)

    # Concept wins if it has any signal and entity has no strong signal
    if concept_score >= 1 and entity_score <= 1:
        return "concept"

    # Entity wins if it has stronger or equal signal
    if entity_score >= 2:
        return "entity"

    # Default: entity (specific named tools/articles → entities/ is safer)
    return "entity"


# ─────────────────────────────────────────────────────────────
# LLM Prompts (router-backed: personalkm.llm.router.route)
# ─────────────────────────────────────────────────────────────
# Split across two router stages per config/models.yaml so cheap structured
# classification runs on a local/cheap model while the quality-critical
# prose synthesis runs on the primary model:
#   entity_extraction — topic / tags / entities / related concepts (JSON)
#   ingest_synthesis  — summary / key facts (JSON)

_EXTRACTION_SYSTEM_PROMPT = """You are an entity and tag classifier for a personal wiki.

RULES:
- Classify the PRIMARY topic from these 5 options ONLY:
  AI-Agent-&-Tools | Automation-Workflows | PKM-&-System-Design | Tech-Trends-&-Insights | Personal-Interests
- tags: cross-topic attributes (tools, techniques, technologies, years, action
  states, e.g. docker, claude, llm, 2025, to-read) — never a second topic label.
  0 tags is fine if nothing cross-topic applies.
- Use English, lowercase-hyphenated entity/concept names.
- OUTPUT JSON ONLY — no markdown code fences, no explanations."""

_EXTRACTION_ENTITY_PROMPT = """Classify this entity note.

CONTENT:
{content}

Respond ONLY with this JSON (no markdown, no code fences):
{{
  "topic": "AI-Agent-&-Tools | Automation-Workflows | PKM-&-System-Design | Tech-Trends-&-Insights | Personal-Interests",
  "entities_mentioned": ["entity-name-1", "entity-name-2"],
  "related_concepts": ["concept-name-1"],
  "tags": ["relevant", "cross-topic", "tags"]
}}"""

_EXTRACTION_CONCEPT_PROMPT = """Classify this concept/guide note.

CONTENT:
{content}

Respond ONLY with this JSON (no markdown, no code fences):
{{
  "topic": "AI-Agent-&-Tools | Automation-Workflows | PKM-&-System-Design | Tech-Trends-&-Insights | Personal-Interests",
  "prerequisites": ["prereq-concept-1"],
  "related_tools": ["tool-name-1"],
  "tags": ["relevant", "cross-topic", "tags"]
}}"""

_SYNTHESIS_SYSTEM_PROMPT = """You are a knowledge curator for a personal wiki.
Your task is to distill raw notes into a concise, structured wiki summary.

RULES:
- Extract key facts only — no fluff, no repetition
- Use English for entity names (e.g., "Claude Code" not "克勞德代碼")
- Keep summaries to 3-5 sentences max
- Key facts should be specific (versions, commands, configurations — not generic)
- OUTPUT JSON ONLY — no markdown code fences, no explanations."""

_SYNTHESIS_USER_PROMPT = """Distill this {page_type} note into a wiki entry.

SOURCE FILE: {source_path}

CONTENT:
{content}

Respond ONLY with this JSON (no markdown, no code fences):
{{
  "summary": "3-5 sentence summary in English",
  "key_facts": [
    "{{fact 1 — specific and concrete}}",
    "{{fact 2 — specific and concrete}}",
    "{{fact 3}}"
  ],
  "confidence": "high|medium|low"
}}"""

# API token limit — matches the previous llm_summarizer truncation.
_MAX_CONTENT_CHARS = 8000


def _synthesize_wiki_note(body: str, *, page_type: str, source_path: str) -> Dict[str, Any]:
    """Synthesize a wiki note via the LLM router (two cost-tiered stages).

    No skip_llm fallback: if every candidate model for a stage is exhausted,
    `route()` raises LLMError and it propagates unchanged (AGENTS.md rule 3 /
    MIGRATION.md step 3) — the raw note stays pending and is retried next run.
    """
    content = body[:_MAX_CONTENT_CHARS]

    extraction_prompt = (
        _EXTRACTION_ENTITY_PROMPT if page_type == "entity" else _EXTRACTION_CONCEPT_PROMPT
    ).format(content=content)
    extraction = route(
        "entity_extraction", extraction_prompt,
        system=_EXTRACTION_SYSTEM_PROMPT, expect_json=True,
    )

    synthesis_prompt = _SYNTHESIS_USER_PROMPT.format(
        page_type=page_type, source_path=source_path, content=content,
    )
    synthesis = route(
        "ingest_synthesis", synthesis_prompt,
        system=_SYNTHESIS_SYSTEM_PROMPT, expect_json=True,
    )

    result: Dict[str, Any] = {}
    result.update(extraction if isinstance(extraction, dict) else {})
    result.update(synthesis if isinstance(synthesis, dict) else {})
    result.setdefault("tags", [])
    result.setdefault("confidence", "medium")
    result["raw_content"] = content
    return result


# ─────────────────────────────────────────────────────────────
# Core Ingestion Step
# ─────────────────────────────────────────────────────────────

def ingest_file_v2(
    raw_path: Path,
    wiki_path: Path,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Process a single raw file through the v2 pipeline.
    
    Returns (success, result_dict).
    result_dict keys: action, page_path, entity, merged, outbound_links, backlinks
    """
    try:
        content = raw_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, {"error": f"Cannot read file: {e}"}

    # 1. Quality filter
    low_quality, reason = is_low_quality(content)
    if low_quality:
        return False, {"error": f"Low-quality content: {reason}"}

    # 2. Strip frontmatter for clean body
    body = _strip_frontmatter(content)

    # 2a. Prefer resolved content if available (from resolver/ runner).
    #     Resolved content is the full article/transcript/README, not just
    #     the LINE snippet. This gives the LLM real substance to summarize.
    try:
        from personalkm.resolve import get_resolved_content

        resolved = get_resolved_content(raw_path)
        if resolved and len(resolved.strip()) > 50:
            logger.info(
                "Using resolved content for %s (%d chars)",
                raw_path.name,
                len(resolved),
            )
            body = resolved
        else:
            logger.debug("No resolved content for %s, using raw body", raw_path.name)
    except Exception:
        logger.debug("Resolver not available, using raw body for %s", raw_path.name)

    # 3. Detect entity mentions in body (before summarization distorts it)
    detected_entities = detect_entity_mentions(body)
    logger.debug(f"Detected entities in {raw_path.name}: {detected_entities[:5]}")

    # 4. Classify page_type BEFORE summarization (drives prompt template)
    #    Heuristic: how-to/process content → concept, named tools/companies → entity
    page_type = _classify_page_type(body)

    # 5. Synthesize wiki note + extract entities/tags via the LLM router.
    #    Raises LLMError if every candidate model is exhausted — this is
    #    intentional and must propagate (no skip_llm fallback, AGENTS.md rule 3).
    summary_result = _synthesize_wiki_note(
        body, page_type=page_type, source_path=str(raw_path)
    )
    distilled = distill_to_markdown(summary_result, page_type=page_type)
    topic = summary_result.get("topic", "Tech-Trends-&-Insights")
    tags = summary_result.get("tags", [])
    confidence = summary_result.get("confidence", "medium")

    # 6. Build title
    title = extract_title(raw_path, content)

    # 7. Entity deduplication — find matching existing page
    registry = _get_registry(wiki_path)
    match = registry.find_entity_match(title)
    entity_slug = normalize_entity_name(title)

    # Phase 6: Check if this should be a canonical entity page
    canonical_slug = canonical_slug_from_name(title)
    use_canonical = canonical_slug is not None

    # 8. Route to entities/ or concepts/ based on page_type
    #    SCHEMA: entities/ = people, products, organizations, specific named tools
    #             concepts/ = topics, methods, techniques, how-to guides
    #    page_type from _classify_page_type: "entity" or "concept"
    # Canonical entities always belong in entities/, regardless of heuristic page_type.
    # Phase 6 design: a canonical entity page is the single source of truth for that entity.
    if use_canonical:
        subfolder = "entities"
    else:
        subfolder = "entities" if page_type == "entity" else "concepts"
    wiki_category_path = wiki_path / subfolder
    wiki_category_path.mkdir(parents=True, exist_ok=True)

    action = "unknown"
    page_path: Optional[Path] = None
    timestamp = datetime.now().strftime("%Y-%m-%d")
    # Store Obsidian-clickable wikilink pointing back to the archived raw file.
    # Archive lives at vault_root/archive/raw/<subfolder>/<file>.md (kept OUT of
    # raw/ so the recursive glob in ingest_raw_to_wiki never re-ingests it).
    vault_root = raw_path.parent  # climb to vault root
    while vault_root.name != "raw" and vault_root.parent != vault_root:
        vault_root = vault_root.parent
    vault_root = vault_root.parent
    archive_dir = vault_root / "Archive" / "raw"
    rel_under_raw = raw_path.relative_to(vault_root / "raw")
    raw_archive_path = archive_dir / rel_under_raw
    # Wikilink path is relative to the vault root (Obsidian-resolvable).
    # Capital-A matches the existing git-tracked Archive/ directory so paths
    # stay valid on case-sensitive filesystems (e.g. Render's Linux).
    archive_rel = Path("Archive/raw") / rel_under_raw
    raw_path_str = f"[[{archive_rel.with_suffix('')}]]"

    if match:
        # 8a. Merge: update existing entity page
        action = "merged"
        page_path = match
        existing_content = page_path.read_text(encoding="utf-8")
        existing_body = _strip_frontmatter(existing_content)

        merged_body = existing_body.rstrip() + f"\n\n---\n\n## {title} ({timestamp})\n\n{distilled}\n"

        if existing_content.startswith("---"):
            parts = existing_content.split("---", 2)
            new_content = f"---\n{parts[1]}\n---\n\n{merged_body}"
            try:
                existing_fm = yaml.safe_load(parts[1])
                existing_tags = existing_fm.get("tags", [])
                if not isinstance(existing_tags, list):
                    existing_tags = [existing_tags] if existing_tags else []
                flat_existing = []
                for t in existing_tags:
                    if isinstance(t, list):
                        flat_existing.extend(str(x) for x in t)
                    elif isinstance(t, str):
                        flat_existing.append(t)
                merged_tags = list(dict.fromkeys(flat_existing + tags))
                tags_yaml = yaml.dump(merged_tags, default_flow_style=True).strip()
                new_content = re.sub(
                    r'^tags:.*(\n\s+.*)*',
                    f'tags: {tags_yaml}',
                    new_content,
                    count=1,
                    flags=re.MULTILINE,
                )
            except Exception as e:
                logger.warning(f"Could not merge tags for {page_path.name}: {e}")
        else:
            new_content = merged_body

        new_content = re.sub(r'^updated: .+$', f'updated: {timestamp}', new_content, flags=re.MULTILINE)

        if raw_path_str not in new_content:
            try:
                existing_fm = yaml.safe_load(parts[1])
                existing_sources = existing_fm.get("sources", [])
                if not isinstance(existing_sources, list):
                    existing_sources = [existing_sources] if existing_sources else []
                if raw_path_str not in existing_sources:
                    existing_sources.append(raw_path_str)
                sources_str = "\n".join(f'  - "{s}"' for s in existing_sources)
                new_content = re.sub(
                    r'^sources:.*(\n\s+.*)*',
                    f"sources:\n{sources_str}",
                    new_content,
                    count=1,
                    flags=re.MULTILINE,
                )
            except Exception:
                new_content = re.sub(
                    r'(^sources:.*)$',
                    r'\1\n  - ' + raw_path_str,
                    new_content,
                    flags=re.MULTILINE,
                )

        page_path.write_text(new_content, encoding="utf-8")
        logger.info(f"✅ MERGED {raw_path.name} → {match.relative_to(wiki_path)}")

    elif use_canonical:
        # Phase 6: Create new canonical entity page (no date prefix)
        action = "created"
        page_path = wiki_category_path / f"{canonical_slug}.md"
        if not page_path.exists():
            tags_yaml = yaml.dump(tags, default_flow_style=True).strip()
            text = f"""---
title: {title}
canonical: true
created: {timestamp}
updated: {timestamp}
topic: {topic}
tags: {tags_yaml}
type: {page_type}
sources:
  - {raw_path_str}
confidence: {confidence}
---

{distilled}
"""
            page_path.write_text(text, encoding="utf-8")
            logger.info(f"✅ CANONICAL CREATED {raw_path.name} → {subfolder}/{canonical_slug}.md")
        else:
            # Merge into existing canonical page
            action = "merged"
            existing = page_path.read_text(encoding="utf-8")
            body = _strip_frontmatter(existing)
            merged = body.rstrip() + f"\n\n---\n\n### {title} ({timestamp})\n\n{distilled}\n"
            if existing.startswith("---"):
                parts = existing.split("---", 2)
                new_content = f"---\n{parts[1]}\n---\n\n{merged}"
            else:
                new_content = merged
            new_content = re.sub(r'^updated: .+$', f'updated: {timestamp}', new_content, flags=re.MULTILINE)
            if raw_path_str not in new_content:
                try:
                    existing_fm = yaml.safe_load(parts[1])
                    existing_sources = existing_fm.get("sources", [])
                    if not isinstance(existing_sources, list):
                        existing_sources = [existing_sources] if existing_sources else []
                    if raw_path_str not in existing_sources:
                        existing_sources.append(raw_path_str)
                    sources_str = "\n".join(f'  - "{s}"' for s in existing_sources)
                    new_content = re.sub(
                        r'^sources:.*(\n\s+.*)*',
                        f"sources:\n{sources_str}",
                        new_content,
                        count=1,
                        flags=re.MULTILINE,
                    )
                except Exception as e:
                    logger.warning(f"Could not merge sources for {page_path.name}: {e}")
                    if raw_path_str not in new_content:
                        new_content = re.sub(
                            r'^sources:\s*.*$',
                            lambda m: m.group(0).rstrip(']') + f', "{raw_path_str}"]' if m.group(0).strip().endswith(']') else m.group(0) + f'\n  - {raw_path_str}',
                            new_content,
                            flags=re.MULTILINE,
                        )
            try:
                existing_fm = yaml.safe_load(parts[1])
                existing_tags = existing_fm.get("tags", [])
                if not isinstance(existing_tags, list):
                    existing_tags = [existing_tags] if existing_tags else []
                flat_existing = []
                for t in existing_tags:
                    if isinstance(t, list):
                        flat_existing.extend(str(x) for x in t)
                    elif isinstance(t, str):
                        flat_existing.append(t)
                merged_tags = list(dict.fromkeys(flat_existing + tags))
                tags_yaml = yaml.dump(merged_tags, default_flow_style=True).strip()
                new_content = re.sub(
                    r'^tags:.*(\n\s+.*)*',
                    f'tags: {tags_yaml}',
                    new_content,
                    count=1,
                    flags=re.MULTILINE,
                )
            except Exception as e:
                logger.warning(f"Could not merge tags for {page_path.name}: {e}")
            page_path.write_text(new_content, encoding="utf-8")
            logger.info(f"✅ CANONICAL MERGED {raw_path.name} → {subfolder}/{canonical_slug}.md")

    else:
        # 8b. Create new date-prefixed page (legacy behavior)
        action = "created"
        dest_name = f"{timestamp}-{entity_slug}.md"
        page_path = wiki_category_path / dest_name

        tags_yaml = yaml.dump(tags, default_flow_style=True).strip()
        frontmatter = f"""---
title: {title}
created: {timestamp}
updated: {timestamp}
topic: {topic}
tags: {tags_yaml}
type: {page_type}
sources:
  - {raw_path_str}
confidence: {confidence}
---

{distilled}
"""
        page_path.write_text(frontmatter, encoding="utf-8")
        logger.info(f"✅ CREATED {raw_path.name} → {subfolder}/{dest_name}")

    # 9. Bidirectional wikilinks (Phase B: LLM-detected entities)
    wm = _get_wikilinks(wiki_path)
    link_result = wm.add_bidirectional_links(page_path, detected_entities)
    outbound = link_result.get("outbound", 0)
    backlinks = link_result.get("backlinks", 0)

    # 10. Direct scan for canonical entity mentions in body (supplement)
    _add_canonical_body_links(wiki_path, page_path, body)

    # 10a. Propagate capture excerpt to each mentioned canonical entity page
    propagated = _propagate_to_entity_pages(wiki_path, page_path, detected_entities, raw_path, body)
    if propagated:
        logger.info(f"  → Propagated to {propagated} entity pages")

    # 11. Move raw file to raw/archive/ so raw/ stays clean but sources stay clickable
    try:
        archive_dir.mkdir(parents=True, exist_ok=True)
        raw_archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(raw_path), str(raw_archive_path))
        logger.info(f"  → Archived raw file to {raw_archive_path.relative_to(vault_root)}")
    except Exception as e:
        logger.warning(f"Could not archive raw file {raw_path}: {e}")

    return True, {
        "action": action,
        "page_path": str(page_path.relative_to(wiki_path)) if page_path else None,
        "entity": entity_slug,
        "confidence": confidence,
        "outbound_links": outbound,
        "backlinks": backlinks,
        "detected_entities": detected_entities[:10],
    }


# ─────────────────────────────────────────────────────────────
# Batch Ingestion
# ─────────────────────────────────────────────────────────────

def _should_skip_unresolvable(raw_file: Path, vault_path: Path) -> str | None:
    """Return a reason string if this raw note should be skipped (no resolvable content).

    Checks:
    1. If the note has a URL classified as threads/instagram → skip (no adapter)
    2. If the note has no URL at all → don't skip (plain text message)
    3. If the note has a URL that has an adapter → don't skip
    """
    try:
        from personalkm.resolve.url_extractor import extract_url
        from personalkm.resolve.adapters.base import classify_url

        url = extract_url(raw_file)
        if not url:
            return None  # no URL = plain text message, still ingest

        source_type = classify_url(url)
        # Known unresolvable source types
        if source_type in ("threads", "instagram"):
            return f"unresolvable source type: {source_type}"
        # Also skip if the URL is clearly a Facebook share link (generic but FB blocks)
        if "facebook.com" in url or "fb.com" in url:
            return "unresolvable source type: facebook"

        return None  # resolvable or generic — proceed
    except Exception:
        return None  # on error, proceed anyway


def ingest_raw_to_wiki(vault_path: Path, max_files: Optional[int] = None) -> dict:
    """
    Main v2 ingestion: process all files in vault_path/raw/

    Args:
        vault_path: root of the vault (contains raw/ and wiki/)
        max_files: if set and > 0, only process the first N raw files
                   (deterministic, sorted by path). None = process all.

    Returns:
        dict with keys: status, processed, failed, trashed, total,
                        results (list of per-file results),
                        llm_info, health_check
    """
    from personalkm.ingest.ingestion_health_check import IngestionHealthCheck

    raw_path = vault_path / "raw"
    wiki_path = vault_path / "wiki"

    if not raw_path.exists():
        return {
            "status": "error",
            "message": f"raw/ folder not found at {raw_path}",
            "processed": 0,
        }

    # Scan raw files
    raw_files = sorted(raw_path.glob("**/*.md"))
    ingest_target = max_files  # process up to N files successfully
    if max_files is not None and max_files > 0:
        logger.info(f"Found {len(raw_files)} files in raw/ (will process up to {max_files})")
    else:
        logger.info(f"Found {len(raw_files)} files in raw/")

    processed = 0
    failed = 0
    trashed = 0
    results = []

    for raw_file in raw_files:
        if ingest_target is not None and processed >= ingest_target:
            logger.info("Reached ingest limit (%d), stopping", ingest_target)
            break
        # Quick quality check before reading full content
        try:
            content_preview = raw_file.read_text(encoding="utf-8", errors="ignore")[:500].lower()
        except Exception:
            content_preview = ""

        low_quality, reason = is_low_quality(content_preview)
        if low_quality:
            # Archive instead of delete
            rel_path = raw_file.relative_to(raw_path)
            archive_path = vault_path / "archive" / rel_path
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                raw_file.rename(archive_path)
            except Exception:
                pass
            trashed += 1
            results.append({"file": str(rel_path), "status": "trashed", "reason": reason})
            continue

        # Skip notes with no resolvable content (Threads, Instagram, etc.)
        # Only count toward the max_files limit when we actually process them.
        _skip_unresolvable = _should_skip_unresolvable(raw_file, vault_path)
        if _skip_unresolvable:
            skipped = _skip_unresolvable
            results.append({"file": raw_file.name, "status": "skipped", "reason": skipped})
            continue

        success, result = ingest_file_v2(raw_file, wiki_path)
        if success:
            processed += 1
        else:
            failed += 1
        results.append({"file": raw_file.name, "status": "success" if success else "failed", **result})

    # Validate wikilinks
    wm = _get_wikilinks(wiki_path)
    broken = wm.validate_links()
    total_broken = sum(len(v) for v in broken.values())

    # Regenerate knowledge graph with Mermaid visualization
    try:
        from personalkm.propagate.knowledge_graph import build_knowledge_graph as _build_kg
        kg_content = _build_kg(wiki_path)
        (wiki_path / "knowledge-graph.md").write_text(kg_content, encoding="utf-8")
        logger.info("Knowledge graph regenerated (Mermaid)")
    except Exception as e:
        logger.warning("Knowledge graph regeneration skipped: %s", e)

    # Run health check
    health = IngestionHealthCheck(vault_path)
    health_report = health.run_all_checks()

    # Auto-promote entities mentioned ≥3 times to stub pages
    stubs_promoted = 0
    try:
        stubs_promoted = _auto_promote_entities(wiki_path)
        if stubs_promoted > 0:
            logger.info(f"Auto-promoted {stubs_promoted} entities to stub pages")
    except Exception as e:
        logger.warning("Auto-promotion skipped: %s", e)

    return {
        "status": "success" if failed == 0 else "partial",
        "processed": processed,
        "failed": failed,
        "trashed": trashed,
        "total": len(raw_files),
        "results": results,
        "broken_wikilinks": total_broken,
        "health_check": health_report,
        "stubs_auto_promoted": stubs_promoted,
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Capture propagation & canonical body-link scanning & entity auto-promotion
# ─────────────────────────────────────────────────────────────


def _add_capture_to_entity(
    entity_path: Path,
    capture_stem: str,
    timestamp: str,
    excerpt: str,
    source_wikilink: str,
) -> None:
    """Add a capture section under ``## Captures`` in an entity page."""
    content = entity_path.read_text(encoding="utf-8")

    capture_entry = (
        f"\n\n### {capture_stem} ({timestamp})\n\n"
        f"{excerpt}\n\n"
        f"Source: {source_wikilink}"
    )

    # Insert under existing ## Captures, or create it
    m = re.search(r"^##\s+Captures\s*$", content, re.MULTILINE)
    if m:
        pos = m.end()
        content = content[:pos] + capture_entry + content[pos:]
    else:
        content = content.rstrip("\n") + "\n\n## Captures\n" + capture_entry + "\n"

    # Bump frontmatter updated date
    content = re.sub(
        r"^updated: \d{4}-\d{2}-\d{2}",
        f"updated: {timestamp}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    entity_path.write_text(content, encoding="utf-8")


def _propagate_to_entity_pages(
    wiki_path: Path,
    page_path: Path,
    detected_entities: List[str],
    raw_path: Optional[Path],
    body: str,
) -> int:
    """Append a capture excerpt to each canonical entity page mentioned in *body*."""
    from personalkm.propagate.entity_dedup import CANONICAL_ENTITIES

    if not body or not body.strip():
        return 0

    entities_dir = wiki_path / "entities"
    if not entities_dir.exists():
        return 0

    updated = 0
    timestamp = datetime.now().strftime("%Y-%m-%d")
    page_stem = page_path.stem

    excerpt = body.strip()[:300].replace("\n", " ").strip()
    if len(body.strip()) > 300:
        excerpt += "…"

    raw_path_str = str(raw_path) if raw_path else ""

    for slug in detected_entities:
        if slug not in CANONICAL_ENTITIES:
            continue

        entity_path = entities_dir / f"{slug}.md"
        if not entity_path.exists():
            continue

        # Idempotent: skip if this capture is already present
        existing = entity_path.read_text(encoding="utf-8")
        if raw_path_str and raw_path_str in existing:
            continue
        if re.search(rf"^###\s+{re.escape(page_stem)}\s*\(", existing, re.MULTILINE):
            continue

        _add_capture_to_entity(
            entity_path,
            capture_stem=page_stem,
            timestamp=timestamp,
            excerpt=excerpt,
            source_wikilink=f"[[{page_stem}]]",
        )
        updated += 1

    return updated


def _add_canonical_body_links(wiki_path: Path, page_path: Path, body: str) -> int:
    """Add [[wikilinks]] for canonical entity slugs found directly in body."""
    from personalkm.propagate.entity_dedup import CANONICAL_ENTITIES, is_canonical_slug

    if not body:
        return 0

    content = page_path.read_text(encoding="utf-8")
    added = 0
    own_slug = page_path.stem

    for slug, display_name in CANONICAL_ENTITIES.items():
        if slug == own_slug:
            continue
        entity_page = wiki_path / "entities" / f"{slug}.md"
        if not entity_page.exists():
            continue

        link_text = f"[[{slug}]]"
        if link_text in content:
            continue

        # Check if slug or display name appears in the body
        if slug.lower() in body.lower() or display_name.lower() in body.lower():
            content = content.rstrip() + f"\n{link_text}\n"
            added += 1

    if added > 0:
        page_path.write_text(content, encoding="utf-8")
        logger.info(f"Added {added} canonical body links to {page_path.name}")

    return added


def _auto_promote_entities(wiki_path: Path, min_mentions: int = 3) -> int:
    """Auto-create stub pages for canonical entities mentioned >= min_mentions times."""
    from personalkm.propagate.entity_dedup import CANONICAL_ENTITIES, is_canonical_slug
    from collections import defaultdict

    entities_dir = wiki_path / "entities"
    if not entities_dir.exists():
        return 0

    existing = {f.stem for f in entities_dir.glob("*.md") if is_canonical_slug(f.stem)}
    candidate_slugs = [s for s in CANONICAL_ENTITIES if s not in existing]

    mention_count: dict[str, int] = defaultdict(int)
    mention_sources: dict[str, list[Path]] = defaultdict(list)

    for slug in candidate_slugs:
        display = CANONICAL_ENTITIES[slug]
        for f in sorted((wiki_path / "entities").glob("*.md")) + sorted((wiki_path / "concepts").glob("*.md")):
            if is_canonical_slug(f.stem):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore").lower()
                if slug.lower() in text or display.lower() in text:
                    mention_count[slug] += 1
                    mention_sources[slug].append(f)
            except Exception:
                continue

    today = datetime.now().strftime("%Y-%m-%d")
    created = 0

    for slug in candidate_slugs:
        count = mention_count[slug]
        if count < min_mentions:
            continue

        sources = mention_sources[slug]
        context = ""
        for src in sources[:3]:
            try:
                body = src.read_text(encoding="utf-8", errors="ignore")
                import re as _re
                body_clean = _re.sub(r'^---.*?---\n*', '', body, flags=_re.DOTALL).strip()
                paras = [p.strip() for p in body_clean.split('\n\n') if p.strip() and len(p.strip()) > 20]
                if paras:
                    context = paras[0][:300]
                    break
            except Exception:
                continue

        if not context:
            context = f"Mentioned in {count} pages"

        display = CANONICAL_ENTITIES[slug]
        source_yaml = "\n".join(f'  - "{s.name}"' for s in sources[:5])

        stub = f"""---
title: {display}
canonical: true
created: {today}
updated: {today}
type: entity
topic: Tech-Trends-&-Insights
sources:
{source_yaml}
tags: []
confidence: medium
---

# {display}

{context}

## Mentions

"""
        for src in sources:
            stub += f"- Mentioned in [[{src.stem}]]\n"

        (entities_dir / f"{slug}.md").write_text(stub, encoding="utf-8")
        created += 1
        logger.info(f"[AUTO] Promoted {slug} → entities/{slug}.md ({count} mentions)")

    return created
