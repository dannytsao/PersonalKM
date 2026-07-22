#!/usr/bin/env python3
"""
Bootstrap / refresh the vault's canonical-entity registry file
(IMPROVEMENT-BACKLOG.md P6#20): wiki/_registry/entities.yaml.

Writes two sections:

- `canonical:` — the active whitelist (slug -> display name). On first run
  this is seeded from the built-in DEFAULT_CANONICAL_ENTITIES; on
  subsequent runs the file's existing canonical section is preserved
  verbatim (the file is the source of truth — this script never demotes).

- `proposed:` — promotion candidates detected from the vault, for HUMAN
  review (backlog: 「提示（不自動）候選晉升」). A date-prefixed page
  becomes a candidate when it has accumulated >= --min-signals signals
  (incoming [[wikilinks]] from other pages + its own `### ... (date)`
  capture sections). Promote one by moving its entry into `canonical:`
  with your chosen slug/display name; the pipeline picks it up on the
  next EntityRegistry construction (hourly).

AGENTS.md hard rule 1: agents must never touch the vault directly. Tested
against fixtures; run it yourself against the real vault (dry-run default,
--apply writes).

Usage:
    python scripts/build_entities_registry.py --vault <path> [--apply] [--min-signals N]
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import yaml  # noqa: E402

from personalkm.propagate.entity_dedup import (  # noqa: E402
    DEFAULT_CANONICAL_ENTITIES,
    REGISTRY_FILE_RELPATH,
)

_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_CAPTURE_HEADING_RE = re.compile(r"^###\s+.+\(\d{4}-\d{2}-\d{2}\)\s*$", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def collect_candidates(wiki: Path, canonical: dict, min_signals: int) -> dict:
    """Scan date-prefixed pages and score promotion signals."""
    pages = [
        f for sub in ("entities", "concepts")
        for f in sorted((wiki / sub).glob("*.md"))
        if (wiki / sub).exists()
    ]
    date_prefixed = [f for f in pages if _DATE_PREFIX_RE.match(f.stem)]

    incoming: dict[str, int] = {}
    for f in pages:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for target in _WIKILINK_RE.findall(content):
            t = target.strip()
            if "/" in t:
                continue
            incoming[t.lower()] = incoming.get(t.lower(), 0) + (t.lower() != f.stem.lower())

    candidates = {}
    today = datetime.now().strftime("%Y-%m-%d")
    for f in date_prefixed:
        if f.stem in canonical:
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        captures = len(_CAPTURE_HEADING_RE.findall(content))
        links_in = incoming.get(f.stem.lower(), 0)
        signals = captures + links_in
        if signals >= min_signals:
            candidates[f.stem] = {
                "captures": captures,
                "incoming_links": links_in,
                "first_proposed": today,
            }
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--min-signals", type=int, default=2)
    args = parser.parse_args()

    wiki = Path(args.vault) / "wiki"
    if not wiki.exists():
        raise SystemExit(f"No wiki/ under {args.vault}")

    registry_path = wiki / REGISTRY_FILE_RELPATH
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Registry file: {registry_path}\n")

    canonical = dict(DEFAULT_CANONICAL_ENTITIES)
    existing_proposed: dict = {}
    if registry_path.exists():
        data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        if isinstance(data.get("canonical"), dict) and data["canonical"]:
            canonical = data["canonical"]  # file is source of truth
            print(f"Preserving existing canonical section ({len(canonical)} entries)")
        if isinstance(data.get("proposed"), dict):
            existing_proposed = data["proposed"]
    else:
        print(f"Seeding canonical from built-in defaults ({len(canonical)} entries)")

    candidates = collect_candidates(wiki, canonical, args.min_signals)
    # Keep previously proposed entries (with their first_proposed date)
    # unless they've since been promoted into canonical.
    merged_proposed = {
        k: v for k, v in existing_proposed.items() if k not in canonical
    }
    for slug, info in candidates.items():
        if slug in merged_proposed:
            merged_proposed[slug].update(
                {k: v for k, v in info.items() if k != "first_proposed"}
            )
        else:
            merged_proposed[slug] = info

    print(f"Promotion candidates (>= {args.min_signals} signals): {len(candidates)}")
    for slug, info in sorted(candidates.items(), key=lambda x: -(x[1]["captures"] + x[1]["incoming_links"])):
        print(f"  {info['captures']}cap+{info['incoming_links']}in  {slug[:70]}")

    doc = {
        "canonical": canonical,
        "proposed": merged_proposed,
    }
    rendered = (
        "# Canonical entity registry (P6#20). `canonical:` is the live\n"
        "# whitelist (slug -> display name) — the pipeline reloads it every\n"
        "# EntityRegistry construction. Promote a proposed entry by moving\n"
        "# it up into canonical: with your chosen slug and display name.\n"
        + yaml.dump(doc, allow_unicode=True, sort_keys=True, default_flow_style=False)
    )

    if args.apply:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(rendered, encoding="utf-8")
        print(f"\nWrote {registry_path}")
    else:
        print("\nRun with --apply to write the registry file.")


if __name__ == "__main__":
    main()
