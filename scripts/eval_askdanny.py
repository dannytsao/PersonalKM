"""Score AskDanny search against the test set in evals/askdanny/golden.yaml.

For every question it runs the real query code against the real lifestyle
vault registry, compares the returned stores with the expected stores, and
prints found / missed / extra per question plus overall recall and precision.

    python scripts/eval_askdanny.py --vault ~/Documents/PersonalKM/Personalkm-lifestyle-vault
    python scripts/eval_askdanny.py --vault ... --details      # list missed/extra stores
    python scripts/eval_askdanny.py --vault ... --only 萬里區餐廳

Read-only: it never writes to the vault. The LLM is NOT called: steps that
would ask the LLM use AskDanny's built-in no-LLM fallback, and a "please
confirm these areas" reply is treated as the user answering "yes".
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from personalkm.query import line_bot as lb

GOLDEN = Path(__file__).resolve().parent.parent / "evals" / "askdanny" / "golden.yaml"


def _no_llm(*_args, **_kwargs):
    raise RuntimeError("LLM disabled in eval")


def _tianmu_stores(root: Path) -> set[str]:
    body = (root / "wiki" / "concepts" / "tianmu-food.md").read_text(encoding="utf-8")
    section = re.search(r"## 天母[^\n]*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    rows = re.finditer(r"^\|\s*[^|]+\|\s*([^|]+)\|", section.group(1) if section else "", re.MULTILINE)
    return {m.group(1).strip().removesuffix(" 👤") for m in rows} - {"Store", "---"}


def _text(entry: lb.RegistryEntry) -> str:
    return " ".join((entry.store, *entry.highlights)).lower()


def expected_stores(spec: dict, kinds: dict, entries: list[lb.RegistryEntry], root: Path) -> set[str]:
    kind = kinds[spec["kind"]]
    picked: set[str] = set()
    if spec["kind"] != "lookup":
        where = spec.get("where", [])
        tianmu = _tianmu_stores(root) if spec.get("tianmu") else None
        for e in entries:
            if tianmu is not None:
                if e.store.removesuffix(" 👤") not in tianmu:
                    continue
            elif not any(w in e.address or w == e.city for w in where):
                continue
            if e.subject not in kind["subjects"]:
                continue
            name = e.store.lower()
            if any(w.lower() in name for w in kind.get("not_in_name", [])):
                continue
            if "snack_words" in kind and e.subject != "小吃" and not any(w in name for w in kind["snack_words"]):
                continue
            words = kind.get("any", [])
            if words and not any(w.lower() in _text(e) for w in words):
                continue
            words = spec.get("any", [])
            if words and not any(w.lower() in _text(e) for w in words):
                continue
            picked.add(e.store)
    picked |= set(spec.get("include", []))
    picked -= set(spec.get("exclude", []))
    picked -= set(spec.get("optional", []))
    return picked


def askdanny_stores(query: str, root: Path, entries: list[lb.RegistryEntry]) -> tuple[list[str], str]:
    result = lb._query_all(query, root)
    error = result.get("error")
    if error == "needs_location_confirmation":
        intent = result["location_intent"]
        found = lb._registry_matches_for_locations(intent.subject, intent.locations, entries)
        return [e.store for e in found], f"confirmed {'/'.join(intent.locations)}"
    found = result.get("registry_entries") or ()
    if found:
        return [e.store for e in found], "registry"
    return [], error or "LLM text answer (no store list)"


@dataclass
class Score:
    query: str
    expected: set[str]
    returned: list[str]
    optional: set[str]
    path: str

    @property
    def found(self) -> set[str]:
        return self.expected & set(self.returned)

    @property
    def missed(self) -> set[str]:
        return self.expected - set(self.returned)

    @property
    def extra(self) -> set[str]:
        return set(self.returned) - self.expected - self.optional


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", type=Path, default=lb.DEFAULT_LIFESTYLE_VAULT)
    ap.add_argument("--golden", type=Path, default=GOLDEN)
    ap.add_argument("--details", action="store_true", help="list missed and extra stores")
    ap.add_argument("--only", help="run a single question")
    args = ap.parse_args()

    logging.disable(logging.CRITICAL)
    lb.route = _no_llm
    golden = yaml.safe_load(args.golden.read_text(encoding="utf-8"))
    entries = lb._load_registry_entries(args.vault)
    if not entries:
        print(f"No registry found under {args.vault}", file=sys.stderr)
        return 2

    scores = []
    for spec in golden["queries"]:
        if args.only and spec["q"] != args.only:
            continue
        expected = expected_stores(spec, golden["kinds"], entries, args.vault)
        returned, path = askdanny_stores(spec["q"], args.vault, entries)
        scores.append(Score(spec["q"], expected, returned, set(spec.get("optional", [])), path))

    print(f"{'question':<12} {'expect':>6} {'got':>5} {'found':>6} {'missed':>6} {'extra':>6}  path")
    for s in scores:
        flag = "  ✅" if not s.missed and not s.extra else "  ❌"
        print(f"{s.query:<12} {len(s.expected):>6} {len(s.returned):>5} {len(s.found):>6} "
              f"{len(s.missed):>6} {len(s.extra):>6}  {s.path}{flag}")
        if args.details:
            for name in sorted(s.missed):
                print(f"      missed: {name}")
            for name in sorted(s.extra):
                print(f"      extra:  {name}")

    exp = sum(len(s.expected) for s in scores)
    found = sum(len(s.found) for s in scores)
    scored = sum(len(s.found) + len(s.extra) for s in scores)
    perfect = sum(1 for s in scores if not s.missed and not s.extra)
    print(f"\nrecall {found}/{exp} = {found / exp:.0%}   "
          f"precision {found}/{scored} = {found / scored if scored else 0:.0%}   "
          f"perfect questions {perfect}/{len(scores)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
