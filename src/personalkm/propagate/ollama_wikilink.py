"""
Wikilink Analyzer — Phase B (Post-Link)
=======================================
Analyzes wiki page body text and produces bidirectional wikilink suggestions
using XML tag parsing.

P6#22 (2026-07-27): migrated from direct Ollama HTTP calls to
``personalkm.llm.router.route()``. This fixes the AGENTS.md hard rule 2
violation (no provider names outside ``src/personalkm/llm/``). The router
provides automatic fallback (Ollama → MiniMax → ...) and LLMError alerts.

Why XML tags instead of JSON:
  qwen2.5/qwen3:8b do NOT reliably output structured JSON with format:json.
  XML tags are plain text and parse robustly with regex at 8B scale.

Usage:
    from personalkm.propagate.ollama_wikilink import WikilinkAnalyzer

    analyzer = WikilinkAnalyzer()
    result = analyzer.analyze_page(page_title, page_body, existing_entity_names)
    # result = {forward_links: [...], backward_links: [...]}

Exit Condition:
    # A page that previously had no wikilinks:
    grep -c '\\[\\[' wiki/entities/example.md   # Was 0, now > 0
    # An older entity that now links back:
    grep 'example' wiki/entities/older-entity.md   # Has [[example]] now
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Legacy env vars kept for backward compatibility — the router now resolves
# the model/URL from config/models.yaml, but these are still read by the
# old is_available() health check and by tests that don't load the full config.


def _entity_mentioned_in_body(entity_slug: str, body_lower: str) -> bool:
    """Check if an entity slug is mentioned in the body text.

    Handles both exact matches and normalized forms (hyphens → spaces).
    """
    # Exact match (e.g. "claude-code" in "claude-code is great")
    if entity_slug in body_lower:
        return True
    # Normalized match (e.g. "claude code" matches "Claude Code")
    normalized = entity_slug.replace("-", " ")
    if len(normalized) >= 4 and normalized in body_lower:
        return True
    return False
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────────────────────────

_WIKILINK_SYSTEM_PROMPT = """你是知識庫關聯織網專家。你的任務是分析一個維基頁面的內容，對照現有的知識庫實體清單，找出所有合理的雙向連結。

Karpathy 目標：每個頁面應該有 10-15 個雙向連結。不要漏掉任何相關性，寧可多連也不要少連。

規則：
- 只輸出真實存在於知識庫清單中的實體，不要發明新的 page name
- 積極尋找間接關聯（主題相近、技術互補、同領域、相關概念），不限於字面名稱出現
- 正向連結：新頁面內容中提及、相關、或可補充的主題
- 反向連結：清單中的實體若主題與此新頁面高度相關，應從該實體連結回此頁面
- 最少要給出 3 個正向和 3 個反向連結（除非實體清單太小）
- 不要包含任何 Markdown 裝飾或前言
- 嚴格使用以下 XML 標籤格式輸出"""

_WIKILINK_USER_PROMPT_TEMPLATE = """現有知識庫實體清單：
{entity_list}

新傳入的維基頁面標題：{page_title}

新傳入的維基頁面內容：
{page_body}

請嚴格按照以下格式輸出（只輸出標籤區塊，不要任何其他文字）：

<FORWARD_LINKS>
- [[實體檔名1]]
- [[實體檔名2]]
</FORWARD_LINKS>

<BACKWARD_LINKS>
- [[實體檔名3]]  # 在實體檔名3的頁面中新增一條指向此新頁面的連結
- [[實體檔名4]]  # 在實體檔名4的頁面中新增一條指向此新頁面的連結
</BACKWARD_LINKS>

如果沒有正向連結，輸出：
<FORWARD_LINKS>
</FORWARD_LINKS>

如果沒有反向連結，輸出：
<BACKWARD_LINKS>
</BACKWARD_LINKS>
"""


# ─────────────────────────────────────────────────────────────────────────────
# XML Tag Parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_wikilink_output(raw_output: str) -> tuple[list[str], list[str]]:
    """
    Parse XML-tagged output and extract forward/backward link lists.

    Returns (forward_links, backward_links) where each is a list of
    bare wikilink slugs (without brackets).

    Handles:
    - Malformed tags (e.g., <FORWARD_LINKS> without closing newline)
    - Empty sections
    - Extra whitespace
    - Lines with trailing comments
    """
    # Extract FORWARD_LINKS block
    forward_section = _extract_tag(raw_output, "FORWARD_LINKS")
    forward_links = _extract_wikilinks(forward_section)

    # Extract BACKWARD_LINKS block
    backward_section = _extract_tag(raw_output, "BACKWARD_LINKS")
    backward_links = _extract_wikilinks(backward_section)

    return forward_links, backward_links


def _extract_tag(text: str, tag_name: str) -> str:
    """Extract content between <TAG_NAME> and </TAG_NAME>."""
    pattern = re.compile(
        rf"<{re.escape(tag_name)}>(.*?)</{re.escape(tag_name)}>",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return ""


def _extract_wikilinks(section: str) -> list[str]:
    """
    Extract wikilink slugs from a parsed section.

    Input: "- [[claude-code]]\\n- [[docker]]  # comment"
    Output: ["claude-code", "docker"]
    """
    if not section:
        return []

    slugs = []
    for line in section.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip leading dash/bullet
        line = re.sub(r"^[-*]\s*", "", line)
        # Strip trailing comment
        line = re.sub(r"\s*#.*$", "", line)
        # Extract [[slug]]
        matches = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", line)
        slugs.extend(matches)

    return [s.strip().lower() for s in slugs if s.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Main Analyzer (uses personalkm.llm.router)
# ─────────────────────────────────────────────────────────────────────────────

class WikilinkAnalyzer:
    """
    Phase B: Semantic wikilink analyzer.

    Reads a wiki page's body, queries the LLM router (``wikilink_analysis``
    stage) with semantic context, and returns bidirectional link suggestions
    parsed from XML-tagged output.

    The router handles model fallback (Ollama → cloud) and raises ``LLMError``
    if all candidates fail. Callers should catch ``LLMError`` and treat the
    page as unprocessable for this cycle (do NOT silently skip — log it).
    """

    def __init__(self, stage: str = "wikilink_analysis"):
        self.stage = stage

    def analyze_page(
        self,
        page_title: str,
        page_body: str,
        existing_entity_names: list[str],
    ) -> dict:
        """
        Analyze a wiki page and return bidirectional link suggestions.

        Args:
            page_title: Title of the new/updated page
            page_body: Raw body text (no frontmatter)
            existing_entity_names: List of known entity names (file stems) to consider

        Returns:
            dict with keys: forward_links (list), backward_links (list),
                           raw_output (str), parse_success (bool)

        Raises:
            LLMError: if all models in the ``wikilink_analysis`` stage chain
                      are exhausted. Callers must NOT catch this silently.
        """
        if not existing_entity_names:
            logger.debug("No existing entities — skipping analysis")
            return {"forward_links": [], "backward_links": [], "raw_output": "", "parse_success": True}

        # Build entity list string (max ~200 entities to keep prompt manageable)
        # Sort by name length descending to help model match longer names first
        entity_list = "\n".join(
            f"- {name}" for name in sorted(existing_entity_names, key=len, reverse=True)[:200]
        )

        # P9#36: Pre-filter candidates using keyword matching before sending to LLM.
        # The local 8B model struggles with 200 raw entity names. We narrow the
        # list to the ~30 most mention-relevant candidates first, making the LLM's
        # job dramatically easier.
        body_lower = page_body.lower()
        filtered_candidates = [
            name for name in sorted(existing_entity_names, key=len, reverse=True)[:200]
            if _entity_mentioned_in_body(name, body_lower)
        ]
        if filtered_candidates:
            entity_list = "\n".join(f"- {name}" for name in filtered_candidates[:50])

        # Truncate body if too long (context window limit)
        body_truncated = page_body[:3000] if page_body else ""

        prompt = _WIKILINK_USER_PROMPT_TEMPLATE.format(
            entity_list=entity_list,
            page_title=page_title,
            page_body=body_truncated,
        )

        from personalkm.llm.router import route

        comp = route(self.stage, prompt, system=_WIKILINK_SYSTEM_PROMPT)
        raw_output = comp.text

        forward_links, backward_links = parse_wikilink_output(raw_output)

        # Sprint 3: Filter out stop-word wikilinks (common/generic terms)
        # but keep any slug that matches a real existing entity/concept file.
        existing_set = set(existing_entity_names) if existing_entity_names else set()
        from personalkm.propagate.stop_words import filter_wikilinks, load_stop_words

        stop_words = load_stop_words()
        forward_links = filter_wikilinks(forward_links, stop_words, existing_set)
        backward_links = filter_wikilinks(backward_links, stop_words, existing_set)

        logger.debug(
            f"Page '{page_title}': "
            f"forward={forward_links}, backward={backward_links}"
        )

        return {
            "forward_links": forward_links,
            "backward_links": backward_links,
            "raw_output": raw_output,
            "parse_success": True,
        }

    def is_available(self) -> bool:
        """Check if the primary provider (Ollama) is reachable.

        This is a legacy health check kept for the shell script's pre-flight
        check. The router itself handles fallback when Ollama is down — this
        method only determines whether to log a warning about the primary
        being unavailable.
        """
        from personalkm.llm.router import _provider, _candidates

        try:
            candidates = _candidates(self.stage)
            if not candidates:
                return False
            # Check the first candidate (primary)
            provider_name = candidates[0].split("/")[0]
            provider = _provider(provider_name)
            # Only Ollama has a direct health check endpoint
            if hasattr(provider, "base_url") and "ollama" in provider_name:
                from urllib.request import urlopen, Request
                req = Request(f"{provider.base_url}/api/tags", method="GET")
                with urlopen(req, timeout=5) as response:
                    return response.status == 200
            # Cloud providers are assumed available (router handles failures)
            return True
        except Exception:
            return False


# Backward-compatibility alias — old imports use ``OllamaWikilinkAnalyzer``
OllamaWikilinkAnalyzer = WikilinkAnalyzer
