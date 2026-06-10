from tools.omnichannel_md.frontmatter import parse_markdown, update_frontmatter
from tools.omnichannel_md.worker import replace_body, scan_pending_notes, transcribe_with_whisper


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


def test_transcribe_with_whisper_reports_missing_model(tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"not real wav")

    result = transcribe_with_whisper(audio, tmp_path / "missing.bin")

    assert not result.ok
    assert result.error.startswith("whisper_model_missing:")


def test_replace_body_preserves_h1_title():
    markdown = """---
platform: youtube
---
# Original Title

Old body
"""

    updated = replace_body(markdown, "## 摘要\nNew body", "Original Title")

    assert "---\n# Original Title\n\n## 摘要\nNew body\n" in updated
