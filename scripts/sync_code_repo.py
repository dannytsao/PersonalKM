#!/usr/bin/env python3
"""
Cron entry point: best-effort `git pull --ff-only` for the CODE repo
(IMPROVEMENT-BACKLOG.md #36).

Run this — and only this — before importing/launching any pipeline module,
so a `git pull` mid-process can never race code that's already loaded into
memory. The actual pull logic lives in `personalkm.gitstate.sync_code_repo`;
this script exists solely to invoke it as a separate process, from bash,
ahead of the real Phase A/B/C entry point.

Always exits 0 — a failed pull is logged and the pipeline proceeds on
whatever code is already on disk. This script must never be the reason a
cron run aborts.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from personalkm.gitstate import sync_code_repo  # noqa: E402

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z")
logger = logging.getLogger("sync_code_repo")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()

    result = sync_code_repo(args.repo, args.branch)
    if result["repair_actions"]:
        logger.warning(f"Repaired code repo git state before pull: {result['repair_actions']}")
    if result["status"] == "pulled":
        logger.info(f"Code repo updated: {result['detail']}")
    elif result["status"] == "up_to_date":
        logger.info(f"Code repo already up to date ({result['detail']}).")
    else:
        logger.warning(f"Code repo sync skipped — running existing checkout as-is: {result['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
