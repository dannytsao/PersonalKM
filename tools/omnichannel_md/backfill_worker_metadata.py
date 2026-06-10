from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.omnichannel_md.frontmatter import parse_markdown, update_frontmatter
from tools.omnichannel_md.worker import LOCAL_WORKER_PLATFORMS, LOCAL_WORKER_STATUSES, WORKER_TYPE


WORKER_FIELDS = {
    "needs_local_worker",
    "worker_status",
    "worker_type",
    "worker_retry_count",
}


@dataclass(frozen=True)
class BackfillPlan:
    path: Path
    updates: dict[str, Any]


def worker_metadata_for(frontmatter: dict[str, Any]) -> dict[str, Any]:
    platform = str(frontmatter.get("platform") or "")
    extraction_status = str(frontmatter.get("extraction_status") or "")
    needs_review = frontmatter.get("needs_review") is True
    needs_local_worker = (
        platform in LOCAL_WORKER_PLATFORMS
        and (extraction_status in LOCAL_WORKER_STATUSES or needs_review)
    )
    if needs_local_worker:
        return {
            "needs_local_worker": True,
            "worker_status": "pending",
            "worker_type": WORKER_TYPE,
            "worker_retry_count": int(frontmatter.get("worker_retry_count") or 0),
        }
    return {
        "needs_local_worker": False,
        "worker_status": "not_required",
        "worker_type": "none",
        "worker_retry_count": int(frontmatter.get("worker_retry_count") or 0),
    }


def missing_or_incomplete_worker_metadata(frontmatter: dict[str, Any]) -> bool:
    return any(field not in frontmatter for field in WORKER_FIELDS)


def collect_backfill_plans(repo_root: Path) -> list[BackfillPlan]:
    plans: list[BackfillPlan] = []
    raw_root = repo_root / "raw"
    if not raw_root.exists():
        return plans

    for path in sorted(raw_root.rglob("*.md")):
        markdown = path.read_text(encoding="utf-8")
        document = parse_markdown(markdown)
        if not document.frontmatter or not missing_or_incomplete_worker_metadata(document.frontmatter):
            continue
        plans.append(BackfillPlan(path=path, updates=worker_metadata_for(document.frontmatter)))
    return plans


def apply_backfill(plans: list[BackfillPlan]) -> None:
    for plan in plans:
        markdown = plan.path.read_text(encoding="utf-8")
        plan.path.write_text(update_frontmatter(markdown, plan.updates), encoding="utf-8")


def print_plans(repo_root: Path, plans: list[BackfillPlan]) -> None:
    if not plans:
        print("No notes need worker metadata backfill.")
        return
    for index, plan in enumerate(plans, start=1):
        status = plan.updates["worker_status"]
        print(f"{index}. {plan.path.relative_to(repo_root)} worker_status={status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill worker metadata into legacy raw notes")
    parser.add_argument("--repo-root", default=".", help="Path to the PersonalKM repo")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    plans = collect_backfill_plans(repo_root)
    print_plans(repo_root, plans)
    if args.apply:
        apply_backfill(plans)
        print(f"Applied worker metadata backfill to {len(plans)} note(s).")
    else:
        print(f"Dry-run only. {len(plans)} note(s) would be updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
