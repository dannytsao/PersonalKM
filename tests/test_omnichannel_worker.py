from tools.omnichannel_md.frontmatter import parse_markdown, update_frontmatter
from tools.omnichannel_md.worker import scan_pending_notes


def test_update_frontmatter_preserves_body_and_updates_worker_fields():
    markdown = """---
title: Example
needs_local_worker: true
worker_status: pending
---
# Example

Body
"""

    updated = update_frontmatter(
        markdown,
        {
            "needs_local_worker": False,
            "worker_status": "done",
            "worker_retry_count": 0,
        },
    )

    document = parse_markdown(updated)

    assert document.frontmatter["needs_local_worker"] is False
    assert document.frontmatter["worker_status"] == "done"
    assert document.frontmatter["worker_retry_count"] == 0
    assert document.body.startswith("# Example")


def test_scan_pending_notes_finds_explicit_pending_note(tmp_path):
    note = tmp_path / "raw" / "Tech" / "youtube.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        """---
platform: youtube
extraction_status: partial
needs_local_worker: true
worker_status: pending
---
# YouTube
""",
        encoding="utf-8",
    )

    candidates = scan_pending_notes(tmp_path)

    assert len(candidates) == 1
    assert candidates[0].path == note
    assert not candidates[0].legacy


def test_scan_pending_notes_finds_legacy_partial_note(tmp_path):
    note = tmp_path / "raw" / "Tech" / "legacy.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        """---
platform: youtube
extraction_status: partial
---
# Legacy
""",
        encoding="utf-8",
    )

    candidates = scan_pending_notes(tmp_path)

    assert len(candidates) == 1
    assert candidates[0].legacy


def test_scan_pending_notes_ignores_normal_web_note(tmp_path):
    note = tmp_path / "raw" / "Tech" / "web.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        """---
platform: web
extraction_status: ok
needs_local_worker: false
worker_status: not_required
---
# Web
""",
        encoding="utf-8",
    )

    assert scan_pending_notes(tmp_path) == []
