#!/usr/bin/env python3
"""
Query Interface for PersonalKM
===============================
Search the vault with natural language. Uses keyword + entity search,
optionally passes matched context to an LLM for a synthesized answer
with [[wikilink]] citations.

CLI Usage:
    python scripts/query_wiki.py "what is hermes agent?"
    python scripts/query_wiki.py "how does GLM 5.2 compare to DeepSeek?" --top-k 5
    python scripts/query_wiki.py "travel recommendations" --no-llm
    python scripts/query_wiki.py "what do I know about Cursor?" --json

Import:
    from scripts.query_wiki import query_wiki
    result = query_wiki("hermes agent", Path("wiki"))
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from personalkm.propagate.entity_dedup import CANONICAL_ENTITIES, EntityRegistry, normalize_entity_name
    from personalkm.llm.router import route
except ImportError:
    # Allow running as script from repo root
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from personalkm.propagate.entity_dedup import CANONICAL_ENTITIES, EntityRegistry, normalize_entity_name
    from personalkm.llm.router import route


logger = logging.getLogger(__name__)

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

SEARCH_RESULT_KEYS = [
    "page", "slug", "title", "type", "topic", "tags",
    "confidence", "score", "match_reason", "sources",
    "summary_excerpt",
]


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and return (fm, body)."""
    fm = {}
    if not content.startswith("---"):
        return fm, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return fm, content
    fm_block = parts[1]
    body = parts[2].strip()
    for line in fm_block.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def _extract_wikilinks(text: str) -> list[str]:
    return WIKILINK_RE.findall(text)


def _smart_truncate(text: str, max_chars: int = 300) -> str:
    """Truncate at word boundary, appending '…' if truncated."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Cut at last space
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated.strip() + "…"


def search_wiki(
    query: str,
    wiki_path: Path,
    top_k: int = 10,
    registry: Optional[EntityRegistry] = None,
) -> list[dict]:
    """
    Hybrid search: keyword match (title / body / frontmatter) + entity lookup.

    Returns list of dicts sorted by score (highest first).
    """
    query_lower = query.lower().strip()
    query_tokens = set(re.findall(r"[a-z0-9\u4e00-\u9fff\-_]+", query_lower))
    # Remove very short tokens
    query_tokens = {t for t in query_tokens if len(t) > 1}

    if not query_tokens:
        return []

    scored: list[dict] = []

    for subdir in ("entities", "concepts"):
        dir_path = wiki_path / subdir
        if not dir_path.exists():
            continue
        for fpath in sorted(dir_path.glob("*.md")):
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            fm, body = _parse_frontmatter(content)
            slug = fpath.stem
            title = fm.get("title", slug)
            title_lower = title.lower()
            body_lower = body.lower()

            score = 0.0
            reasons = []

            # Title exact / prefix match (strongest)
            if query_lower == title_lower:
                score += 20
                reasons.append("title_exact")
            elif title_lower.startswith(query_lower) or query_lower.startswith(title_lower):
                score += 15
                reasons.append("title_prefix")

            # Title token overlap
            title_tokens = set(re.findall(r"[a-z0-9\u4e00-\u9fff\-_]+", title_lower))
            overlap = query_tokens & title_tokens
            if overlap:
                score += 5 * len(overlap)
                reasons.append(f"title_tokens:{','.join(sorted(overlap)[:3])}")

            # Frontmatter field match
            fm_text = " ".join(v for v in fm.values() if isinstance(v, str)).lower()
            for token in query_tokens:
                if token in fm_text:
                    score += 3
                    reasons.append("fm_field")

            # Body keyword mentions
            body_token_count = sum(1 for t in query_tokens if t in body_lower)
            if body_token_count > 0:
                score += 2 * body_token_count
                reasons.append(f"body_mentions:{body_token_count}")

            # Entity slug or display name match
            for slug_key, display in CANONICAL_ENTITIES.items():
                if slug_key in query_tokens or display.lower() in query_lower:
                    if slug_key == slug:
                        score += 10
                        reasons.append("canonical_match")
                        break

            # EntityRegistry fuzzy match
            if registry and score > 0:
                match = registry.find_entity_match(title)
                if match and match.name == fpath.name:
                    score += 5
                    if "canonical_match" not in reasons:
                        reasons.append("registry_match")

            if score > 0:
                # Extract summary excerpt
                summary_excerpt = ""
                # Try ## Summary or first meaningful paragraph
                summary_match = re.search(
                    r"## Summary\s*\n\n(.+?)(?:\n\n|$)", body, re.DOTALL
                )
                if summary_match:
                    summary_excerpt = _smart_truncate(summary_match.group(1).strip(), 300)
                if not summary_excerpt:
                    # First non-header paragraph
                    paras = [
                        p.strip()
                        for p in re.split(r"\n\n+", body)
                        if p.strip() and not p.strip().startswith("#")
                    ]
                    for p in paras:
                        if len(p) > 30:
                            summary_excerpt = _smart_truncate(p, 300)
                            break

                scored.append({
                    "page": str(fpath.relative_to(wiki_path.parent)),
                    "slug": slug,
                    "title": title,
                    "type": fm.get("type", subdir[:-1]),
                    "topic": fm.get("topic", ""),
                    "tags": fm.get("tags", ""),
                    "confidence": fm.get("confidence", "medium"),
                    "score": score,
                    "match_reason": "; ".join(reasons[:3]),
                    "sources": fm.get("sources", ""),
                    "summary_excerpt": summary_excerpt,
                    "_path": fpath,
                    "_body": body,
                })

    scored.sort(key=lambda r: -r["score"])
    return scored[:top_k]


def build_llm_context(results: list[dict], max_chars: int = 4000) -> str:
    """Build a context string for the LLM from search results."""
    chunks = []
    total = 0
    for r in results:
        path = r["page"]
        title = r["title"]
        summary = r["summary_excerpt"]
        body_sample = _smart_truncate(r.get("_body", ""), 500)

        # Build a compact entry
        entry = f"## {path}\n"
        entry += f"Title: {title}\n"
        entry += f"Type: {r['type']} | Topic: {r['topic']} | Confidence: {r['confidence']}\n"
        if summary:
            entry += f"Summary: {summary}\n"
        if body_sample:
            entry += f"Content excerpt:\n{body_sample}\n"
        entry += "\n"

        if total + len(entry) > max_chars:
            break
        chunks.append(entry)
        total += len(entry)
    return "".join(chunks)


def answer_with_llm(
    query: str,
    context: str,
    wiki_path: Path,
) -> dict:
    """
    Send query + context to the LLM router and return a structured answer.

    Returns dict with keys: answer, sources, matched_pages.

    Raises LLMError (from personalkm.llm.router.route) when every candidate
    model for the "query_answer" stage is exhausted. Callers must NOT catch
    this and silently degrade — AGENTS.md rule 3 forbids skip_llm fallbacks;
    let it propagate so the failure is visible.
    """
    prompt = f"""You are a personal knowledge base assistant. Given wiki pages from the user's vault, answer their question. Use [[wikilink]] notation to cite sources. If the context doesn't contain enough information, say so.

Context (wiki pages sorted by relevance):
{context}

Question: {query}

Answer (cite sources with [[wikilink]], e.g. [[hermes-agent]]):"""

    completion = route("query_answer", prompt)
    answer_text = completion.text.strip()

    # Extract [[wikilinks]] from the answer for source tracking
    cited = list(set(_extract_wikilinks(answer_text)))

    return {
        "answer": answer_text,
        "error": None,
        "sources": cited,
        "matched_pages": len(context.split("## ")) - 1 if context else 0,
    }


def query_wiki(
    query: str,
    vault_root: Path,
    top_k: int = 10,
    use_llm: bool = True,
) -> dict:
    """
    Full query pipeline: search → (optional LLM) → result.

    Args:
        query: Natural language question.
        vault_root: Vault root path (parent of wiki/ directory).
        top_k: Max search results to return.

    Returns dict with keys:
        query, timestamp, matched_pages (list), answer (optional),
        total_matches, llm_used, error
    """
    wiki_path = vault_root / "wiki"
    if not wiki_path.exists():
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "matched_pages": [],
            "total_matches": 0,
            "llm_used": False,
            "answer": None,
            "error": f"wiki/ not found in {vault_root}",
        }
    registry = EntityRegistry(wiki_path) if wiki_path.exists() else None
    results = search_wiki(query, wiki_path, top_k=top_k, registry=registry)

    output = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "matched_pages": [
            {k: r[k] for k in SEARCH_RESULT_KEYS if k in r}
            for r in results
        ],
        "total_matches": len(results),
        "llm_used": False,
        "answer": None,
        "error": None,
    }

    if use_llm and results:
        context = build_llm_context(results)
        llm_result = answer_with_llm(query, context, wiki_path)
        output["llm_used"] = True
        if llm_result["error"]:
            output["error"] = llm_result["error"]
        else:
            output["answer"] = {
                "text": llm_result["answer"],
                "sources": llm_result["sources"],
            }
    elif not results:
        output["error"] = "No matching pages found"

    return output


def display_cli(result: dict, json_mode: bool = False) -> None:
    """Render query result to CLI."""
    if json_mode:
        # Clean up internal fields
        display = {
            "query": result["query"],
            "timestamp": result["timestamp"],
            "total_matches": result["total_matches"],
            "matched_pages": result["matched_pages"],
            "answer": result.get("answer"),
            "llm_used": result["llm_used"],
            "error": result.get("error"),
        }
        print(json.dumps(display, indent=2, ensure_ascii=False))
        return

    print(f"\n{'='*60}")
    print(f"  Query: {result['query']}")
    print(f"  Matches: {result['total_matches']} page(s)")
    print(f"{'='*60}\n")

    if result.get("answer"):
        print("── Answer ──────────────────────────────────────────")
        print(f"\n{result['answer']['text']}\n")
        if result["answer"]["sources"]:
            print(f"Sourced from: {', '.join(result['answer']['sources'])}\n")
        print("─" * 60)
    elif result.get("error"):
        print(f"  ⚠️  {result['error']}\n")
        print("─" * 60)

    if result["matched_pages"]:
        print("\n── Matched Pages ──────────────────────────────────\n")
        for i, page in enumerate(result["matched_pages"], 1):
            score = page.get("score", 0)
            conf = page.get("confidence", "?")
            title = page.get("title", page["slug"])
            page_type = page.get("type", "?")
            topic = page.get("topic", "")
            excerpt = page.get("summary_excerpt", "")
            reasons = page.get("match_reason", "")
            bar = "█" * min(int(score), 20) + "░" * max(0, 20 - min(int(score), 20))
            print(f"  {i:2d}. [{bar}] {conf.upper():6s} | {title}")
            print(f"      {page['page']}")
            if reasons:
                print(f"      match: {reasons}")
            if topic:
                print(f"      topic: {topic} | type: {page_type}")
            if excerpt:
                print(f"      {excerpt[:200]}")
            print()

    print(f"{'='*60}")


# ── CLI entry point ──

def main():
    parser = argparse.ArgumentParser(
        description="Query PersonalKM vault with natural language."
    )
    parser.add_argument("query", nargs="?", help="Natural language query")
    parser.add_argument("--vault", default=".", help="Vault root path (default: .)")
    parser.add_argument("--top-k", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis, show raw matches only")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive REPL mode")

    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    wiki_path = vault_path / "wiki"
    if not wiki_path.exists():
        print(f"Error: wiki/ not found in {vault_path}")
        sys.exit(1)

    if args.interactive:
        print("PersonalKM Query Interface (interactive)")
        print("Type your question, or /quit to exit.\n")
        while True:
            try:
                q = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q or q.lower() in ("/quit", "/exit", "/q"):
                break
            result = query_wiki(q, wiki_path, top_k=args.top_k, use_llm=not args.no_llm)
            display_cli(result, json_mode=args.json)
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    result = query_wiki(args.query, wiki_path, top_k=args.top_k, use_llm=not args.no_llm)
    display_cli(result, json_mode=args.json)


if __name__ == "__main__":
    main()
