#!/usr/bin/env python3
"""
Entity Distillation Loop — dry-run preview (SPEC.md, IMPROVEMENT-BACKLOG.md P5)
================================================================================
Reports which wiki/entities/ and wiki/concepts/ pages currently trigger
distillation (>=5 captures, or >=30 days since last_distilled/created) and
what the LLM proposes as a concentrated summary.

This NEVER writes to the vault. Writing (fold-preserve retention — proposed
summary on top, original capture entries folded into a collapsed block,
nothing deleted) is a deliberate later step once this dry-run output has
been manually reviewed against real content.

Usage:
    python scripts/distill_entities.py --vault /path/to/vault
    python scripts/distill_entities.py --vault /path/to/vault --no-llm   # list candidates only, skip API calls
    python scripts/distill_entities.py --vault /path/to/vault --json
"""
import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from personalkm.propagate.distill import scan_for_candidates

VAULT_DEFAULT = Path(os.getenv("VAULT_PATH", str(Path.home() / "Documents/PersonalKM")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=str(VAULT_DEFAULT), help="Vault root path")
    parser.add_argument("--no-llm", action="store_true", help="List trigger candidates without calling the LLM")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    vault_root = Path(args.vault).expanduser()
    wiki_path = vault_root / "wiki"
    if not wiki_path.exists():
        print(f"No wiki/ found at {wiki_path}")
        return 1

    previews = scan_for_candidates(wiki_path, call_llm=not args.no_llm)

    if args.json:
        print(json.dumps(
            [
                {**asdict(p), "path": str(p.path.relative_to(vault_root))}
                for p in previews
            ],
            indent=2, ensure_ascii=False,
        ))
        return 0

    if not previews:
        print("目前沒有頁面觸發濃縮條件。")
        return 0

    print(f"{len(previews)} 個頁面觸發濃縮條件：\n")
    for p in previews:
        print(f"=== {p.path.relative_to(vault_root)} ===")
        print(f"標題：{p.title}")
        print(f"觸發原因：{p.reason}（累積 captures：{p.captures_count}）")
        if p.error:
            print(f"LLM 呼叫失敗：{p.error}")
        elif p.proposed_summary:
            print(f"\n提議摘要：\n{p.proposed_summary}")
            if p.proposed_key_facts:
                print("\n提議重點：")
                for fact in p.proposed_key_facts:
                    print(f"  - {fact}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
