#!/usr/bin/env python3
"""
One-time migration: repair the wiki damage left behind by the frontmatter
round-trip bugs fixed in personalkm.frontmatter (P7#27/P7#28).

Three passes, each targeting a confirmed damage shape:

1. recover: pages whose real frontmatter was deleted wholesale (first
   block has no `title:` — e.g. claude-code.md, 2026-07-12). The last
   version in vault git history that still had a `title:` is located, its
   frontmatter recovered, the newest `wikilink_processed` found across the
   current orphan wrapper blocks is kept, and the page is rebuilt as
   recovered-frontmatter + current body (wrapper blocks dropped).

2. strip-pasted: pages whose body contains another page's frontmatter as
   bare unwrapped text (kimi-k3.md, P7#28) — a contiguous run of 4+
   frontmatter-key lines in the body plus their list continuation lines is
   removed.

3. normalize: every structurally healthy page is round-tripped through
   split_frontmatter/join_frontmatter once, stripping the blank-line
   padding that legacy rewrites accumulated (github.md's ~63 lines).

AGENTS.md hard rule 1: agents must never touch the vault directly. This
script is tested against fixtures only; run it yourself against the real
vault path (dry-run is the default; --apply writes).

Usage:
    python scripts/fix_wiki_frontmatter_damage.py --vault <path> [--apply]
"""

import argparse
import re
import subprocess
from pathlib import Path

from personalkm.frontmatter import join_frontmatter, split_frontmatter

_FM_KEYS = (
    "title", "created", "updated", "topic", "tags", "type",
    "sources", "confidence", "canonical", "stub", "wikilink_processed",
)
_FM_KEY_LINE_RE = re.compile(rf"^({'|'.join(_FM_KEYS)}):")
_WLP_RE = re.compile(r"^wikilink_processed:\s*(\S+)", re.MULTILINE)


# ── Pass 1: recover deleted frontmatter from git history ─────────────────

def first_block_has_title(content: str) -> bool:
    fm, _ = split_frontmatter(content)
    return fm is not None and "title:" in fm


def peel_wrapper_blocks(content: str) -> tuple[list[str], str]:
    """Remove leading orphan wrapper blocks (frontmatter-shaped blocks
    without a `title:`), returning (their inner texts, remaining body)."""
    wrappers: list[str] = []
    while True:
        fm, body = split_frontmatter(content)
        if fm is None or "title:" in fm:
            return wrappers, content
        wrappers.append(fm)
        content = body


def recover_frontmatter_from_git(vault: Path, rel_path: str) -> str | None:
    """Return the frontmatter text from the newest commit in which the
    file's first block still had a `title:`, or None if never found."""
    log = subprocess.run(
        ["git", "log", "--format=%H", "--", rel_path],
        cwd=vault, text=True, capture_output=True, check=True,
    ).stdout.split()
    for commit in log:
        show = subprocess.run(
            ["git", "show", f"{commit}:{rel_path}"],
            cwd=vault, text=True, capture_output=True, check=False,
        )
        if show.returncode != 0:
            continue
        if first_block_has_title(show.stdout):
            fm, _ = split_frontmatter(show.stdout)
            return fm
    return None


def repair_missing_frontmatter(vault: Path, page: Path) -> str | None:
    """Build the repaired content for a page whose frontmatter was deleted.
    Returns None when no recoverable frontmatter exists in history."""
    content = page.read_text(encoding="utf-8")
    rel = str(page.relative_to(vault))
    recovered = recover_frontmatter_from_git(vault, rel)
    if recovered is None:
        return None

    wrappers, body = peel_wrapper_blocks(content)

    # A wrapper whose closing "---" doubled as the next block's opener can
    # leave stray bare frontmatter-key lines at the top of the body (the
    # real claude-code.md had a second wikilink_processed line stranded
    # this way). Drop them, but feed their timestamps into the newest-
    # timestamp computation below.
    leftover_lines = []
    body_lines = body.split("\n")
    while body_lines and (
        not body_lines[0].strip()
        or body_lines[0].strip() == "---"
        or _FM_KEY_LINE_RE.match(body_lines[0])
    ):
        if _FM_KEY_LINE_RE.match(body_lines[0]):
            leftover_lines.append(body_lines[0])
        body_lines.pop(0)
    body = "\n".join(body_lines)

    # Keep the newest wikilink_processed timestamp seen anywhere (wrapper
    # blocks were where Phase B kept refreshing it after the damage).
    stamps = _WLP_RE.findall(recovered) + [
        s for w in wrappers for s in _WLP_RE.findall(w)
    ] + [s for line in leftover_lines for s in _WLP_RE.findall(line)]
    if stamps:
        newest = max(stamps)
        if _WLP_RE.search(recovered):
            recovered = _WLP_RE.sub(f"wikilink_processed: {newest}", recovered, count=1)
        else:
            recovered = recovered.rstrip("\n") + f"\nwikilink_processed: {newest}"

    return join_frontmatter(recovered, body)


# ── Pass 2: strip another page's frontmatter pasted bare into the body ───

def strip_pasted_frontmatter(content: str) -> tuple[str, int]:
    """Remove contiguous runs of 4+ bare frontmatter-key lines (plus their
    indented list continuations) from the body. Returns (new_content,
    blocks_removed)."""
    fm, body = split_frontmatter(content)
    lines = body.split("\n")
    out: list[str] = []
    removed = 0
    i = 0
    while i < len(lines):
        j = i
        key_count = 0
        while j < len(lines):
            if _FM_KEY_LINE_RE.match(lines[j]):
                key_count += 1
                j += 1
            elif lines[j].startswith("  ") and key_count > 0:
                j += 1  # list continuation under a key
            else:
                break
        if key_count >= 4:
            removed += 1
            i = j  # drop the whole run
        else:
            out.append(lines[i])
            i += 1
    if removed == 0:
        return content, 0
    return join_frontmatter(fm, "\n".join(out)), removed


# ── Pass 3: strip accumulated padding on healthy pages ───────────────────

def normalize_padding(content: str) -> str:
    fm, body = split_frontmatter(content)
    if fm is None or "title:" not in fm:
        return content
    return join_frontmatter(fm, re.sub(r"\n{4,}", "\n\n\n", body))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault)
    wiki = vault / "wiki"
    if not wiki.exists():
        raise SystemExit(f"No wiki/ under {args.vault}")

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")
    stats = {"recovered": 0, "stripped": 0, "normalized": 0, "unrecoverable": 0}

    for sub in ("entities", "concepts"):
        d = wiki / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            new_content = content
            labels = []

            if not first_block_has_title(new_content):
                repaired = repair_missing_frontmatter(vault, f)
                if repaired is None:
                    stats["unrecoverable"] += 1
                    print(f"  [UNRECOVERABLE] {f.relative_to(wiki)}: no titled version in history")
                    continue
                new_content = repaired
                stats["recovered"] += 1
                labels.append("recovered-frontmatter")

            new_content, n = strip_pasted_frontmatter(new_content)
            if n:
                stats["stripped"] += 1
                labels.append(f"stripped-{n}-pasted-block(s)")

            normalized = normalize_padding(new_content)
            if normalized != new_content:
                new_content = normalized
                if not labels:
                    stats["normalized"] += 1
                    labels.append("normalized-padding")

            if new_content != content:
                print(f"  [{'FIXED' if args.apply else 'WOULD FIX'}] {f.relative_to(wiki)}: {', '.join(labels)}")
                if args.apply:
                    f.write_text(new_content, encoding="utf-8")

    print(f"\nRecovered frontmatter: {stats['recovered']}")
    print(f"Stripped pasted blocks: {stats['stripped']}")
    print(f"Padding normalized:     {stats['normalized']}")
    print(f"Unrecoverable:          {stats['unrecoverable']}")
    if not args.apply:
        print("\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
