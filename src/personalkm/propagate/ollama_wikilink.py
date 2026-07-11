"""
Ollama Wikilink Analyzer — Phase B (Post-Link)
================================================
Uses Ollama (qwen3:8b) to analyze wiki page body text and produce
bidirectional wikilink suggestions using XML tag parsing.

Why XML tags instead of JSON:
  qwen3:8b does NOT reliably output structured JSON with format:json.
  XML tags are plain text and parse robustly with regex at 8B scale.

Usage:
    from personalkm.propagate.ollama_wikilink import OllamaWikilinkAnalyzer

    analyzer = OllamaWikilinkAnalyzer(ollama_url="http://127.0.0.1:11434")
    result = analyzer.analyze_page(page_body, existing_entity_names)
    # result = {forward_links: [...], backward_links: [...]}

Exit Condition:
    # A page that previously had no wikilinks:
    grep -c '\[\[' wiki/entities/example.md   # Was 0, now > 0
    # An older entity that now links back:
    grep 'example' wiki/entities/older-entity.md   # Has [[example]] now
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib import request
from urllib.error import URLError

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────────────────────────

_WIKILINK_SYSTEM_PROMPT = """你是知識庫關聯織網專家。你的任務是分析一個維基頁面的內容，對照現有的知識庫實體清單，找出所有合理的雙向連結。

規則：
- 只輸出真實存在於知識庫清單中的實體，不要發明新的 page name
- 如果沒有相關的實體，回應空的章節（不是錯誤）
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
    Parse Ollama's XML-tagged output and extract forward/backward link lists.

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

    Input: "- [[claude-code]]\n- [[docker]]  # comment"
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
# Ollama Client (direct HTTP, no SDK dependency)
# ─────────────────────────────────────────────────────────────────────────────

def call_ollama(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_OLLAMA_MODEL,
    url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 120,
) -> Optional[str]:
    """
    Call Ollama /api/generate endpoint directly via urllib.

    Returns the raw response text, or None on failure.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")

    req = request.Request(
        f"{url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return str(data.get("response", "")).strip()
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning(f"Ollama call failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main Analyzer
# ─────────────────────────────────────────────────────────────────────────────

class OllamaWikilinkAnalyzer:
    """
    Phase B: Semantic wikilink analyzer using Ollama.

    Reads a wiki page's body, queries Ollama (qwen3:8b) with semantic context,
    and returns bidirectional link suggestions parsed from XML-tagged output.
    """

    def __init__(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        ollama_model: str = DEFAULT_OLLAMA_MODEL,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model

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
        """
        if not existing_entity_names:
            logger.debug("No existing entities — skipping analysis")
            return {"forward_links": [], "backward_links": [], "raw_output": "", "parse_success": True}

        # Build entity list string (max ~200 entities to keep prompt manageable)
        # Sort by name length descending to help model match longer names first
        entity_list = "\n".join(
            f"- {name}" for name in sorted(existing_entity_names, key=len, reverse=True)[:200]
        )

        # Truncate body if too long (Ollama context window limit ~8k tokens)
        # Keep ~3000 chars — enough for semantic understanding at 8B scale
        body_truncated = page_body[:3000] if page_body else ""

        prompt = _WIKILINK_USER_PROMPT_TEMPLATE.format(
            entity_list=entity_list,
            page_title=page_title,
            page_body=body_truncated,
        )

        raw_output = call_ollama(
            prompt=prompt,
            system=_WIKILINK_SYSTEM_PROMPT,
            model=self.ollama_model,
            url=self.ollama_url,
        )

        if raw_output is None:
            logger.warning(f"Ollama call returned None for page: {page_title}")
            return {
                "forward_links": [],
                "backward_links": [],
                "raw_output": "",
                "parse_success": False,
            }

        forward_links, backward_links = parse_wikilink_output(raw_output)

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
        """Check if Ollama is reachable at the configured URL."""
        try:
            req = request.Request(
                f"{self.ollama_url.rstrip('/')}/api/tags",
                method="GET",
            )
            with request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
