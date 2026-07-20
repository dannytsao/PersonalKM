#!/usr/bin/env python3
"""
Compare ingest_synthesis quality across two stages, side by side
================================================================================
Runs the exact same real capture content through the live "ingest_synthesis"
stage (config/models.yaml) and, if defined, an "ingest_synthesis_trial" stage,
so you can judge whether a candidate model/provider is worth switching to.

Read-only: only reads the files you point it at. Never writes to the vault,
never changes any config, never touches Phase A's actual behavior.

ingest_synthesis_trial does NOT exist by default — add it to
config/models.yaml yourself when you want to try a new candidate (see
IMPROVEMENT-BACKLOG.md for the history: it existed 2026-07-20 while
comparing DeepSeek against Ollama, and was removed once DeepSeek was
adopted as ingest_synthesis's default).

Usage:
    python scripts/compare_ingest_synthesis.py --file /path/to/one.md
    python scripts/compare_ingest_synthesis.py --file a.md b.md c.md   # multiple files in one run
    python scripts/compare_ingest_synthesis.py --dir /path/to/resolved/Tech   # every *.md in a directory
    python scripts/compare_ingest_synthesis.py --file ... --page-type concept
"""
import argparse
import sys
import time
from pathlib import Path

# entity_dedup.py (imported transitively via ingestion_v2) reaches into the
# top-level tools/ package, which isn't part of the installed personalkm
# package — same workaround ingest_wiki.py needs when run with a system
# python that has no editable install.
_REPO_ROOT = Path(__file__).parent.parent.resolve()
for _p in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from personalkm.ingest.ingestion_v2 import _synthesize_wiki_note  # noqa: E402
from personalkm.llm.router import _config as _router_config  # noqa: E402

COMPARE_STAGES = ["ingest_synthesis", "ingest_synthesis_trial"]


def _stage_label(stage: str) -> str:
    """Describe a stage by its actually-configured primary model — never
    hardcode a model name here, config/models.yaml can change independently
    of this script (it did: ingest_synthesis's primary changed from Ollama
    to DeepSeek on 2026-07-20, and a hardcoded label would have kept lying
    about which model produced which output)."""
    stages = _router_config().get("stages", {})
    if stage not in stages:
        return None
    return f"{stage}（primary={stages[stage]['primary']}）"


def _run(body: str, page_type: str, source_path: str, stage: str) -> None:
    label = _stage_label(stage)
    if label is None:
        print(f"--- {stage} ---")
        print("這個 stage 目前不存在於 config/models.yaml，略過（需要你自己先加上去）。\n")
        return

    print(f"--- {label} ---")
    start = time.monotonic()
    try:
        result = _synthesize_wiki_note(
            body, page_type=page_type, source_path=source_path, synthesis_stage=stage,
        )
    except Exception as e:
        print(f"失敗：{e}\n")
        return
    elapsed = time.monotonic() - start
    print(f"耗時：{elapsed:.1f}s")
    print(f"Topic: {result.get('topic')}")
    print(f"Tags: {result.get('tags')}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Summary:\n{result.get('summary')}")
    print()


def _compare_one(path: Path, page_type: str) -> None:
    print(f"##### {path.name} #####\n")
    body = path.read_text(encoding="utf-8", errors="ignore")
    for stage in COMPARE_STAGES:
        _run(body, page_type, str(path), stage)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file", nargs="+", help="One or more real raw/resolved capture files (read-only)",
    )
    parser.add_argument("--dir", help="Directory to compare every *.md file in (read-only)")
    parser.add_argument("--page-type", default="entity", choices=["entity", "concept"])
    args = parser.parse_args()

    if not args.file and not args.dir:
        print("Need --file (one or more paths) or --dir.")
        return 1

    paths: list[Path] = []
    if args.file:
        paths.extend(Path(f).expanduser() for f in args.file)
    if args.dir:
        dir_path = Path(args.dir).expanduser()
        if not dir_path.is_dir():
            print(f"Not a directory: {dir_path}")
            return 1
        paths.extend(sorted(dir_path.glob("*.md")))

    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"File not found: {p}")
        return 1

    print(f"Comparing {len(paths)} file(s)...\n")
    for path in paths:
        _compare_one(path, args.page_type)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
