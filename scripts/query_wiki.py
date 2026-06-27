#!/usr/bin/env python3
"""
Query Interface CLI for PersonalKM
===================================
Search the vault with natural language.

Usage:
    python scripts/query_wiki.py "what is hermes agent?"
    python scripts/query_wiki.py "how does GLM 5.2 compare to DeepSeek?" --top-k 5
    python scripts/query_wiki.py "travel recommendations" --no-llm
    python scripts/query_wiki.py "what do I know about Cursor?" --json
    python scripts/query_wiki.py -i                          (interactive REPL)
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from bot.query_engine import query_wiki


def display_cli(result: dict, json_mode: bool = False) -> None:
    """Render query result to CLI."""
    if json_mode:
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
        print(f"  {'⚠️ ' if 'No LLM' not in result['error'] else ''}{result['error']}\n")
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


def main():
    parser = argparse.ArgumentParser(
        description="Query PersonalKM vault with natural language."
    )
    parser.add_argument("query", nargs="?", help="Natural language query")
    parser.add_argument("--vault", default=".", help="Vault root path (default: .)")
    parser.add_argument("--top-k", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive REPL")

    args = parser.parse_args()
    vault_path = Path(args.vault).resolve()

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
            result = query_wiki(q, vault_path, top_k=args.top_k, use_llm=not args.no_llm)
            display_cli(result, json_mode=args.json)
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    result = query_wiki(args.query, vault_path, top_k=args.top_k, use_llm=not args.no_llm)
    display_cli(result, json_mode=args.json)


if __name__ == "__main__":
    main()
