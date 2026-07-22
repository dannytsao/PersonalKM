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

`split_frontmatter()` finds the first `---` block anywhere in the leading
region of the file, `join_frontmatter()` reassembles without growing —
round-tripping through the pair is idempotent.
"""

import re

# First "--- ... ---" block whose opener is at the start of a line, with
# only whitespace allowed before it (tolerates the leading-junk-blank-lines
# case; a conflict marker before it means the block is still found because
# the opener just needs to sit at its own line start).
_FM_BLOCK_RE = re.compile(r"(?:^|\n)---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", re.DOTALL)


_YAML_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*:")

# A real frontmatter block sits at (or very near) the top of the file. If
# the text before the first "---" block is longer than this, the match is a
# body divider pair (e.g. legacy capture separators), not frontmatter.
_MAX_LEADING_JUNK = 200


def split_frontmatter(content: str) -> tuple[str | None, str]:
    """
    Extract the first frontmatter block found in *content*.

    Returns (frontmatter_text, body): frontmatter_text is the block's inner
    text stripped of the padding blank lines that legacy round-trips
    accumulated (None when no block exists); body is everything after the
    block, with anything before the block dropped only if it is pure
    whitespace (real leading content is preserved at the front of body).

    Refuses to treat a "---" pair as frontmatter when it sits deep in the
    file (legacy body dividers) or when its content doesn't look like YAML
    keys — those cases return (None, content) untouched.
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


def join_frontmatter(fm: str | None, body: str) -> str:
    """Reassemble a page. Idempotent with split_frontmatter: no padding
    growth across repeated round-trips."""
    if fm is None:
        return body
    return f"---\n{fm.strip(chr(10))}\n---\n\n{body.lstrip(chr(10))}"
