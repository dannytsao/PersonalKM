from personalkm.frontmatter import join_frontmatter, split_frontmatter


def test_split_normal_page():
    fm, body = split_frontmatter("---\ntitle: X\ncanonical: true\n---\n\nBody.\n")
    assert fm == "title: X\ncanonical: true"
    assert body.strip() == "Body."


def test_split_survives_leading_blank_line():
    # Root cause B of the claude-code.md frontmatter loss: a single blank
    # line before "---" made startswith("---") False and the merge then
    # wrote body-only output. split_frontmatter must still find the block.
    fm, body = split_frontmatter("\n---\ntitle: X\n---\n\nBody.\n")
    assert fm == "title: X"
    assert body.strip() == "Body."


def test_split_survives_conflict_marker_and_preserves_it_in_body():
    content = "<<<<<<< HEAD\n---\ntitle: X\n---\n\nBody.\n"
    fm, body = split_frontmatter(content)
    assert fm == "title: X"
    assert "<<<<<<< HEAD" in body  # junk preserved, not silently dropped
    assert "Body." in body


def test_split_strips_accumulated_padding():
    fm, _ = split_frontmatter("---\n\n\n\n\ntitle: X\n\n\n\n\n---\n\nBody.\n")
    assert fm == "title: X"


def test_split_refuses_deep_body_divider_pair():
    # A page with NO frontmatter whose body contains legacy "---" capture
    # dividers must not have prose misidentified as frontmatter.
    content = "## Summary\n\n" + ("Long prose line here. " * 20) + "\n\n---\n\nsome: thing\n\n---\n\nMore.\n"
    fm, body = split_frontmatter(content)
    assert fm is None
    assert body == content


def test_split_refuses_non_yaml_block():
    content = "---\nJust a prose sentence, no key.\n---\n\nBody.\n"
    fm, body = split_frontmatter(content)
    assert fm is None
    assert body == content


def test_roundtrip_is_idempotent_no_padding_growth():
    # Root cause A: the old rewrites added one blank line top and bottom of
    # the frontmatter on every write. split/join must be stable.
    content = "---\ntitle: X\ncreated: 2026-07-01\n---\n\nBody.\n"
    for _ in range(5):
        fm, body = split_frontmatter(content)
        content = join_frontmatter(fm, body)
    assert content.startswith("---\ntitle: X\n")
    assert content.count("\n\n\n") == 0


def test_join_without_frontmatter_returns_body():
    assert join_frontmatter(None, "Body.\n") == "Body.\n"
