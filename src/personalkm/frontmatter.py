"""
Robust frontmatter split/join for wiki pages (IMPROVEMENT-BACKLOG.md P7#27
root-cause fix).

Two long-lived corruption mechanisms lived in the ad-hoc frontmatter
round-trips scattered across the pipeline:

A. Padding growth: rewrites did `f"---\\n{parts[1]}\\n---"` where parts[1]
   already begins and ends with a newline — every hourly rewrite added one
   blank line to the top and bottom of the frontmatter. github.md
   accumulated ~63 of them.

B. Asymmetric strip/re-add: merges took the body via a stripper that
   removes a frontmatter block found ANYWHERE in the file, but re-attached
   it only when the file `startswith("---")`. Any leading junk — a stray
   blank line, an Obsidian Git conflict marker — flipped that check and
   the entire frontmatter (title/canonical/sources/tags) was silently
   deleted on the next merge. That is how claude-code.md lost its
   frontmatter on 2026-07-12.

C. Stacked orphan wrapper blocks (found 2026-09-21, IMPROVEMENT-BACKLOG.md
   #27 follow-up): once a page has lost its real frontmatter to (A) or (B),
   any writer that can't find it (Phase B's `set_frontmatter_value`) just
   creates a brand-new block containing only `wikilink_processed` at the
   very top, on every run that touches the page. Every one of those blocks
   `startswith("---")`, so a naive "grab the first block" reader keeps
   finding the thin, most-recent wrapper — treating the real, richer block
   underneath as ordinary body text forever, even after (A)/(B) are fixed.
   `split_frontmatter()` peels off leading blocks whose only key is
   `wikilink_processed` until it finds one with real content.

`split_frontmatter()` finds the first non-wrapper `---` block anywhere in
the leading region of the file, `join_frontmatter()` reassembles without
growing — round-tripping through the pair is idempotent.
"""

import re

# First "--- ... ---" block whose opener is at the start of a line, with
# only whitespace allowed before it (tolerates the leading-junk-blank-lines
# case; a conflict marker before it means the block is still found because
# the opener just needs to sit at its own line start).
_FM_BLOCK_RE = re.compile(r"(?:^|\n)---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", re.DOTALL)

# Same block shape, but anchored at position 0 of whatever string it's
# matched against — used to look for another block directly underneath one
# already found, not searching further into the file.
_FM_BLOCK_AT_START_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", re.DOTALL)

_YAML_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:")
_TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):", re.MULTILINE)

# A real frontmatter block sits at (or very near) the top of the file. If
# the text before the first "---" block is longer than this, the match is a
# body divider pair (e.g. legacy capture separators), not frontmatter.
_MAX_LEADING_JUNK = 200

# The only field every orphan wrapper block observed in this vault has ever
# contained (root cause C). A block whose keys are a subset of this is
# disposable bookkeeping, never real page content — safe to discard once a
# richer block is found underneath it.
_ORPHAN_WRAPPER_ONLY_KEYS = {"wikilink_processed"}


def _top_level_keys(fm_text: str) -> set[str]:
    return set(_TOP_LEVEL_KEY_RE.findall(fm_text))


def split_single_frontmatter_block(content: str) -> tuple[str | None, str]:
    """
    Extract exactly the *first* `---` block found in *content* — no peeling
    past orphan wrapper blocks underneath it. This is the primitive
    `split_frontmatter()` builds on; use it directly only when a caller
    needs to inspect each stacked block one at a time (e.g. a one-time
    repair pass harvesting a timestamp from every wrapper before discarding
    them — see `scripts/fix_wiki_frontmatter_damage.py::peel_wrapper_blocks`).
    Everything else should call `split_frontmatter()`.

    Returns (frontmatter_text, body) — semantics match `split_frontmatter()`
    for a single block: None when no block exists or it doesn't look like
    real frontmatter (deep-in-file body divider, non-YAML-looking content).
    """
    m = _FM_BLOCK_RE.search(content)
    if not m:
        return None, content
    before = content[: m.start()]
    if len(before.strip()) > _MAX_LEADING_JUNK:
        return None, content
    inner = m.group(1).strip("\n")
    first_line = next((line for line in inner.split("\n") if line.strip()), "")
    if inner and not _YAML_KEY_RE.match(first_line.strip()):
        return None, content
    after = content[m.end():]
    body = after if not before.strip() else before.rstrip("\n") + "\n" + after
    return inner, body


def split_frontmatter(content: str) -> tuple[str | None, str]:
    """
    Extract the real frontmatter block found in *content*, skipping past
    any leading orphan wrapper blocks stacked on top of it (root cause C).

    Returns (frontmatter_text, body): frontmatter_text is the block's inner
    text stripped of the padding blank lines that legacy round-trips
    accumulated (None when no block exists); body is everything after the
    block, with anything before the block dropped only if it is pure
    whitespace (real leading content is preserved at the front of body).

    Refuses to treat a "---" pair as frontmatter when it sits deep in the
    file (legacy body dividers) or when its content doesn't look like YAML
    keys — those cases return (None, content) untouched.
    """
    inner, body = split_single_frontmatter_block(content)
    if inner is None:
        return None, body

    # Peel off leading wrapper-only blocks (root cause C) until we hit one
    # with real content, or run out of stacked blocks to look under.
    while inner and _top_level_keys(inner) <= _ORPHAN_WRAPPER_ONLY_KEYS:
        candidate = body.lstrip("\n")
        m2 = _FM_BLOCK_AT_START_RE.match(candidate)
        if not m2:
            break
        inner2 = m2.group(1).strip("\n")
        first_line2 = next((line for line in inner2.split("\n") if line.strip()), "")
        if inner2 and not _YAML_KEY_RE.match(first_line2.strip()):
            break
        inner, body = inner2, candidate[m2.end():]

    return inner, body


def join_frontmatter(fm: str | None, body: str) -> str:
    """Reassemble a page. Idempotent with split_frontmatter: no padding
    growth across repeated round-trips."""
    if fm is None:
        return body
    return f"---\n{fm.strip(chr(10))}\n---\n\n{body.lstrip(chr(10))}"
