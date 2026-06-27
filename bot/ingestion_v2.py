"""
LLM-Wiki v2 Ingestion Pipeline
==============================
Integrated pipeline: Phase 1 (MiniMax) + Phase 2 (Summarization) + Phase 3 (Dedup) + Phase 4 (Wikilinks)

Data flow:
    raw/*.md → ingest_raw_to_wiki()
        ├── ContentQualityChecker (filter low-quality)
        ├── summarize_content() (LLM: topic + tags + summary)
        ├── detect_entity_mentions() (Phase 2: extract entity names)
        ├── EntityRegistry.find_entity_match() (Phase 3: dedup check)
        ├── distill_to_markdown() (Phase 2: wiki format)
        ├── write_to_wiki() (create or merge)
        ├── WikilinkManager.add_bidirectional_links() (Phase 4)
        └── IngestionHealthCheck (post-ingest validation)

Usage:
    from bot.ingestion_v2 import ingest_raw_to_wiki, ingest_file_v2
    result = ingest_raw_to_wiki(Path('/path/to/vault'))
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from bot.entity_dedup import EntityRegistry, normalize_entity_name
from bot.llm_clients import get_llm_client, get_llm_info
from bot.llm_summarizer import summarize_content, distill_to_markdown, detect_entity_mentions, _strip_frontmatter
from bot.entity_dedup import normalize_entity_name
from bot.wikilinks import WikilinkManager

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

def extract_title(raw_path: Path, content: str, max_len: int = 80) -> str:
    """Extract a clean title from filename or content."""
    # Try first meaningful line (non-frontmatter, non-heading)
    body = _strip_frontmatter(content)
    for line in body.split("\n")[:20]:
        line = line.strip()
        if not line:
            continue
        # Skip markdown headings
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        # Skip frontmatter-like lines
        if line.startswith("---") or ":" in line or line.isupper():
            continue
        # Skip very short or very long lines
        if 5 < len(line) < max_len:
            return normalize_entity_name(line)
    
    # Fall back to filename
    name = raw_path.stem
    # Strip date prefixes
    import re
    name = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]", "", name)
    name = re.sub(r"^\d{10,}[-_]", "", name)
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
# Core Ingestion Step
# ─────────────────────────────────────────────────────────────

def ingest_file_v2(
    raw_path: Path,
    wiki_path: Path,
    *,
    skip_llm: bool = False,
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

    # 3. Detect entity mentions in body (before summarization distorts it)
    detected_entities = detect_entity_mentions(body)
    logger.debug(f"Detected entities in {raw_path.name}: {detected_entities[:5]}")

    # 4. Classify page_type BEFORE summarization (drives prompt template)
    #    Heuristic: how-to/process content → concept, named tools/companies → entity
    page_type = _classify_page_type(body)
    if skip_llm:
        summary_result = None
    else:
        summary_result = summarize_content(body, page_type=page_type)

    # 5. Distill to wiki markdown
    if summary_result:
        distilled = distill_to_markdown(summary_result, page_type=page_type)
        topic = summary_result.get("topic", "Tech-Trends-&-Insights")
        tags = summary_result.get("tags", [])
        confidence = summary_result.get("confidence", "medium")
    else:
        # Fallback: use first paragraph
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        summary_text = paras[0] if paras else body[:500]
        distilled = f"## Summary\n\n{summary_text}\n"
        topic = "Tech-Trends-&-Insights"
        tags = []
        confidence = "low"

    # 6. Build title
    title = extract_title(raw_path, content)

    # 7. Entity deduplication — find matching existing page
    registry = _get_registry(wiki_path)
    match = registry.find_entity_match(title)
    entity_slug = normalize_entity_name(title)

    # 8. Route to entities/ or concepts/ based on page_type
    #    SCHEMA: entities/ = people, products, organizations, specific named tools
    #             concepts/ = topics, methods, techniques, how-to guides
    #    page_type from _classify_page_type: "entity" or "concept"
    subfolder = "entities" if page_type == "entity" else "concepts"
    wiki_category_path = wiki_path / subfolder
    wiki_category_path.mkdir(parents=True, exist_ok=True)

    action = "unknown"
    page_path: Optional[Path] = None

    if match:
        # 8a. Merge: update existing entity page
        action = "merged"
        page_path = match
        existing_content = page_path.read_text(encoding="utf-8")
        existing_body = _strip_frontmatter(existing_content)

        # Append new distilled content to existing body
        timestamp = datetime.now().strftime("%Y-%m-%d")
        merged_body = existing_body.rstrip() + f"\n\n---\n\n## {title} ({timestamp})\n\n{distilled}\n"

        # Read full file, replace only body
        if existing_content.startswith("---"):
            parts = existing_content.split("---", 2)
            new_content = f"---\n{parts[1]}\n---\n\n{merged_body}"
        else:
            new_content = merged_body

        # Update frontmatter
        import re
        new_content = re.sub(r'^updated: .+$', f'updated: {timestamp}', new_content, flags=re.MULTILINE)

        # Add source to sources list if not already present
        raw_path_str = str(raw_path)
        if raw_path_str not in new_content:
            new_content = re.sub(
                r'(^sources:.*)$',
                r'\1\n  - ' + raw_path_str,
                new_content,
                flags=re.MULTILINE,
            )

        page_path.write_text(new_content, encoding="utf-8")
        logger.info(f"✅ MERGED {raw_path.name} → {match.relative_to(wiki_path)}")

    else:
        # 8b. Create new page
        action = "created"
        dest_name = f"{datetime.now().strftime('%Y-%m-%d')}-{entity_slug}.md"
        page_path = wiki_category_path / dest_name

        # Build frontmatter
        raw_path_str = str(raw_path)
        frontmatter = f"""---
title: {title}
created: {datetime.now().strftime("%Y-%m-%d")}
updated: {datetime.now().strftime("%Y-%m-%d")}
topic: {topic}
tags: {tags}
type: {page_type}
sources:
  - {raw_path_str}
confidence: {confidence}
---

{distilled}
"""
        page_path.write_text(frontmatter, encoding="utf-8")
        logger.info(f"✅ CREATED {raw_path.name} → {subfolder}/{dest_name}")

    # 9. Bidirectional wikilinks
    wm = _get_wikilinks(wiki_path)
    link_result = wm.add_bidirectional_links(page_path, detected_entities)
    outbound = link_result.get("outbound", 0)
    backlinks = link_result.get("backlinks", 0)

    # 10. Delete raw file after successful processing
    try:
        raw_path.unlink()
    except Exception as e:
        logger.warning(f"Could not delete raw file {raw_path}: {e}")

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

def ingest_raw_to_wiki(vault_path: Path) -> dict:
    """
    Main v2 ingestion: process all files in vault_path/raw/
    
    Returns:
        dict with keys: status, processed, failed, trashed, total,
                        results (list of per-file results),
                        llm_info, health_check
    """
    from bot.ingestion_health_check import IngestionHealthCheck

    raw_path = vault_path / "raw"
    wiki_path = vault_path / "wiki"

    if not raw_path.exists():
        return {
            "status": "error",
            "message": f"raw/ folder not found at {raw_path}",
            "processed": 0,
        }

    # Check LLM availability
    llm_client = get_llm_client()
    llm_info = get_llm_info()
    skip_llm = llm_info.provider == "none"

    logger.info(f"LLM provider: {llm_info.provider} | Model: {llm_info.default_model} | Skip-LLM: {skip_llm}")

    # Scan raw files
    raw_files = sorted(raw_path.glob("**/*.md"))
    logger.info(f"Found {len(raw_files)} files in raw/")

    processed = 0
    failed = 0
    trashed = 0
    results = []

    for raw_file in raw_files:
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

        success, result = ingest_file_v2(raw_file, wiki_path, skip_llm=skip_llm)
        if success:
            processed += 1
        else:
            failed += 1
        results.append({"file": raw_file.name, "status": "success" if success else "failed", **result})

    # Validate wikilinks
    wm = _get_wikilinks(wiki_path)
    broken = wm.validate_links()
    total_broken = sum(len(v) for v in broken.values())

    # Run health check
    health = IngestionHealthCheck(vault_path)
    health_report = health.run_all_checks()

    return {
        "status": "success" if failed == 0 else "partial",
        "processed": processed,
        "failed": failed,
        "trashed": trashed,
        "total": len(raw_files),
        "results": results,
        "llm_provider": llm_info.provider,
        "llm_model": llm_info.default_model,
        "skip_llm": skip_llm,
        "broken_wikilinks": total_broken,
        "health_check": health_report,
        "timestamp": datetime.now().isoformat(),
    }
