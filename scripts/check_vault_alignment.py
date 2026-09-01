#!/usr/bin/env python3
"""
Vault Alignment Health Check — scans both vaults for topic vs vault mismatches.

Uses content-based heuristics (food/travel/tech keywords) plus source file
subdirectory hints to detect truly mis-placed pages. Reports via stdout.

Run:  python3 scripts/check_vault_alignment.py
Exit: 0 = clean, 1 = mismatches found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HOME = Path.home()

TECH_VAULT = HOME / "Documents/PersonalKM/Personalkm-vault"
LIFE_VAULT = HOME / "Documents/PersonalKM/Personalkm-lifestyle-vault"

# ── Content-based heuristics ──────────────────────────────────────────

FOOD_KW = [
    "美食", "餐廳", "小吃", "料理", "牛肉麵", "牛排", "火鍋",
    "燒肉", "拉麵", "丼飯", "壽司", "生魚片", "咖啡",
    "吃到飽", "必比登", "米其林", "排隊", "菜單",
    "食記", "食評", "店家", "地址", "營業時間",
    "店名", "晚餐", "午餐", "早餐", "必吃",
    "滷味", "鹹酥雞", "雞排", "便當", "飯糰",
    "早餐", "午餐", "晚餐",
    "牛肉湯", "羊肉爐", "薑母鴨",
    "小籠包", "鍋貼", "炒飯", "炒麵", "湯麵",
    "鵝肉", "鴨肉", "雞肉", "豬肉", "排骨",
    "火鍋料", "燒肉", "拉麵", "海鮮",
]

TRAVEL_KW = [
    "景點", "秘境", "步道", "登山", "瀑布", "風景", "美景",
    "日落", "日出", "旅館", "民宿", "住宿", "飯店", "溫泉",
    "一日遊", "旅行", "旅遊", "行程",
    "露營", "camping", "野餐",
    "花季", "櫻花", "楓葉",
    "古道", "自行車", "單車",
    "打卡", "網美",
]

# Lifestyle domains — pages whose source URL matches these should be in lifestyle
LIFESTYLE_DOMAINS = [
    "travel.ettoday", "travel.udn", "tripmoment.com",
    "bobowin.com", "anniekoko.com", "annieko.tw",
    "journey.tw", "foodmap.tw",
    "instagram.com", "threads.net", "threads.com",
]

# Tech domains — pages whose source URL matches these should be in tech
TECH_DOMAINS = [
    "github.com", "youtube.com/watch", "arxiv.org",
    "pypi.org", "npmjs.com", "hub.docker.com",
]


def _contains_keyword(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in text."""
    text_lower = text.lower()
    count = 0
    for kw in keywords:
        if kw.lower() in text_lower:
            count += 1
    return count


def extract_frontmatter_field(text: str, field: str) -> str:
    """Extract a single frontmatter field value."""
    m = re.search(rf"^{field}:\s*(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ""


def extract_sources(text: str) -> list[str]:
    """Extract [[wikilink]] sources from frontmatter."""
    sources = []
    in_sources = False
    for line in text.splitlines():
        if line.strip() == "sources:":
            in_sources = True
            continue
        if in_sources:
            if line.startswith("---"):
                break
            m = re.search(r"\[\[([^\]]+)\]\]", line)
            if m:
                sources.append(m.group(1))
    return sources


def is_lifestyle_content(text: str, title: str) -> bool:
    """Check if page content is clearly lifestyle (food/travel)."""
    corpus = f"{title} {text}".lower()
    food_count = _contains_keyword(corpus, FOOD_KW)
    travel_count = _contains_keyword(corpus, TRAVEL_KW)
    return food_count >= 3 or travel_count >= 3


def has_lifestyle_domain(sources: list[str]) -> bool:
    corpus = " ".join(sources).lower()
    return any(d in corpus for d in LIFESTYLE_DOMAINS)


def has_tech_domain(sources: list[str]) -> bool:
    corpus = " ".join(sources).lower()
    return any(d in corpus for d in TECH_DOMAINS)


def check_page(fpath: Path, vault: Path, vault_name: str) -> dict | None:
    """Check a single wiki page for vault misplacement."""
    text = fpath.read_text(encoding="utf-8", errors="replace")
    title = extract_frontmatter_field(text, "title")
    tags = extract_frontmatter_field(text, "tags").lower()
    summary = extract_frontmatter_field(text, "summary") or ""
    sources = extract_sources(text)

    # Get the body after frontmatter
    body_match = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
    body = body_match[2] if len(body_match) >= 3 else text

    # Combined text for analysis
    corpus = f"{title} {summary} {body} {tags}"

    is_life = is_lifestyle_content(corpus, title)
    has_life_domain = has_lifestyle_domain(sources)
    has_tech_domain_flag = has_tech_domain(sources)

    rel = str(fpath.relative_to(vault))

    if vault_name == "tech":
        # In tech vault: flag if lifestyle content AND no strong tech signal
        if is_life or has_life_domain:
            # Check if there's a strong tech signal that overrides
            tech_signals = _contains_keyword(corpus, [
                "ai", "llm", "api", "code", "github", "python",
                "docker", "agent", "workflow", "prompt", "mcp",
                "claude", "chatgpt", "gemini", "openai",
            ])
            if tech_signals < 3:
                reasons = []
                if is_life:
                    reasons.append("lifestyle keywords in content")
                if has_life_domain:
                    reasons.append(f"lifestyle domain in sources")
                return {
                    "file": rel,
                    "reason": "; ".join(reasons),
                    "target": "lifestyle",
                }

    elif vault_name == "lifestyle":
        # In lifestyle vault: flag if strong tech content AND no lifestyle signal
        tech_signals = _contains_keyword(corpus, [
            "ai", "llm", "api", "code", "github", "python",
            "docker", "agent", "workflow", "prompt", "mcp",
            "claude", "chatgpt", "gemini", "openai",
            "codex", "karpathy", "obsidian plugin",
        ])
        life_signals = _contains_keyword(corpus, FOOD_KW + TRAVEL_KW)

        if tech_signals >= 5 and life_signals < 2:
            return {
                "file": rel,
                "reason": f"tech keywords (count={tech_signals}) in lifestyle vault",
                "target": "tech",
            }

    return None


def main() -> int:
    mismatches: list[dict] = []
    total = 0

    for vault, name in [(TECH_VAULT, "tech"), (LIFE_VAULT, "lifestyle")]:
        for wiki_dir in ["wiki/entities", "wiki/concepts"]:
            d = vault / wiki_dir
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                total += 1
                try:
                    result = check_page(f, vault, name)
                    if result:
                        mismatches.append(result)
                except Exception:
                    pass

    print(f"🔍 Vault Alignment Health Check — {total} pages scanned")
    print()

    if not mismatches:
        print("✅ No mismatches found — both vaults are clean.")
        return 0

    tech_to_life = [m for m in mismatches if m["target"] == "lifestyle"]
    life_to_tech = [m for m in mismatches if m["target"] == "tech"]

    if tech_to_life:
        print(f"⚠️  Tech vault → Lifestyle ({len(tech_to_life)} pages):")
        for m in tech_to_life:
            print(f"    {m['file'][:70]}")
            print(f"      reason: {m['reason']}")
        print()

    if life_to_tech:
        print(f"⚠️  Lifestyle vault → Tech ({len(life_to_tech)} pages):")
        for m in life_to_tech:
            print(f"    {m['file'][:70]}")
            print(f"      reason: {m['reason']}")
        print()

    print(f"📋 Summary: {len(mismatches)} mismatches "
          f"(tech→lifestyle={len(tech_to_life)}, lifestyle→tech={len(life_to_tech)})")
    print("🔧 No auto-fix applied — manual review required.")
    return 1


if __name__ == "__main__":
    sys.exit(main())