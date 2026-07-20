#!/usr/bin/env python3
"""
Entity Distillation Loop (SPEC.md, IMPROVEMENT-BACKLOG.md P5)
================================================================================
Reports which wiki/entities/ and wiki/concepts/ pages currently trigger
distillation (>=5 captures, or >=30 days since last_distilled/created) and
what the LLM proposes as a concentrated summary.

By default this NEVER writes to the vault (dry-run preview only). Pass
--apply to write back — fold-preserve retention: the AI summary goes on
top, the entire original body is kept verbatim inside a collapsed <details>
block, nothing is ever deleted. --apply asks for a per-page y/n confirmation
before writing each page; nothing is written silently.

Usage:
    python scripts/distill_entities.py --vault /path/to/vault
    python scripts/distill_entities.py --vault /path/to/vault --no-llm   # list candidates only, skip API calls
    python scripts/distill_entities.py --vault /path/to/vault --json
    python scripts/distill_entities.py --vault /path/to/vault --apply    # preview + confirm + write
"""
import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from personalkm.propagate.distill import apply_distillation, scan_for_candidates

VAULT_DEFAULT = Path(os.getenv("VAULT_PATH", str(Path.home() / "Documents/PersonalKM")))


def _print_preview(p, vault_root: Path) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=str(VAULT_DEFAULT), help="Vault root path")
    parser.add_argument("--no-llm", action="store_true", help="List trigger candidates without calling the LLM")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument(
        "--apply", action="store_true",
        help="Write back after per-page confirmation (fold-preserve — nothing is deleted, only --no-llm is incompatible)",
    )
    args = parser.parse_args()

    if args.apply and args.no_llm:
        print("--apply requires an LLM summary to write; cannot combine with --no-llm.")
        return 1

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

    written, skipped = 0, 0
    for p in previews:
        _print_preview(p, vault_root)

        if not args.apply:
            continue
        if p.error or not p.proposed_summary:
            print("（無有效摘要，略過寫回）\n")
            skipped += 1
            continue

        answer = input(f"要把上面的摘要寫回 {p.path.relative_to(vault_root)} 嗎？原文會完整保留在摺疊區塊裡。[y/N] ").strip().lower()
        if answer == "y":
            apply_distillation(p.path, p)
            print(f"✅ 已寫回 {p.path.relative_to(vault_root)}\n")
            written += 1
        else:
            print("略過。\n")
            skipped += 1

    if args.apply:
        print(f"完成：寫回 {written} 頁，略過 {skipped} 頁。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
