from tools.omnichannel_md.frontmatter import parse_markdown, update_frontmatter
from pathlib import Path

from tools.omnichannel_md.backfill_worker_metadata import collect_backfill_plans, worker_metadata_for
from tools.omnichannel_md.worker import (
    QueueCandidate,
    infer_metadata_from_markdown_body,
    replace_body,
    scan_pending_notes,
    select_candidate,
    transcribe_with_whisper,
)


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


def test_scan_pending_notes_finds_pure_markdown_blocked_social_note(tmp_path):
    note = tmp_path / "raw" / "Tech" / "x.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        """# X/Twitter post

## 原始內容
> 無法擷取

## 擷取狀態
- 平台：x
- 類型：social_post
- 擷取狀態：blocked
- 需要人工確認：是
- 需要本機 worker：是
- worker_status：pending
- worker_type：omnichannel_md
- worker_retry_count：0

## 原文連結
https://x.com/user/status/1
""",
        encoding="utf-8",
    )

    candidates = scan_pending_notes(tmp_path)

    assert len(candidates) == 1
    assert candidates[0].path == note
    assert candidates[0].metadata["platform"] == "x"
    assert candidates[0].metadata["url"] == "https://x.com/user/status/1"


def test_infer_metadata_from_markdown_body_reads_worker_status_block():
    metadata = infer_metadata_from_markdown_body(
        """## 擷取狀態
- 平台：threads
- 擷取狀態：blocked
- 需要人工確認：是
- 需要本機 worker：是
- worker_status：pending
- worker_retry_count：2

## 原文連結
https://www.threads.net/@user/post/abc
"""
    )

    assert metadata == {
        "platform": "threads",
        "extraction_status": "blocked",
        "needs_review": True,
        "needs_local_worker": True,
        "worker_status": "pending",
        "worker_retry_count": 2,
        "url": "https://www.threads.net/@user/post/abc",
    }


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


def test_select_candidate_can_target_log_id():
    candidates = [
        QueueCandidate(Path("old.md"), {"platform": "youtube", "log_id": "old"}, legacy=True),
        QueueCandidate(Path("new.md"), {"platform": "youtube", "log_id": "target"}, legacy=False),
    ]

    assert select_candidate(candidates, "target").path == Path("new.md")


def test_select_candidate_prefers_explicit_pending_youtube_before_legacy():
    candidates = [
        QueueCandidate(Path("legacy.md"), {"platform": "youtube"}, legacy=True),
        QueueCandidate(Path("explicit.md"), {"platform": "youtube"}, legacy=False),
    ]

    assert select_candidate(candidates).path == Path("explicit.md")


def test_worker_metadata_for_marks_partial_youtube_pending():
    metadata = worker_metadata_for({"platform": "youtube", "extraction_status": "partial"})

    assert metadata["needs_local_worker"] is True
    assert metadata["worker_status"] == "pending"
    assert metadata["worker_type"] == "omnichannel_md"


def test_worker_metadata_for_marks_ok_web_not_required():
    metadata = worker_metadata_for({"platform": "web", "extraction_status": "ok"})

    assert metadata["needs_local_worker"] is False
    assert metadata["worker_status"] == "not_required"
    assert metadata["worker_type"] == "none"


def test_collect_backfill_plans_skips_notes_that_already_have_worker_metadata(tmp_path):
    raw = tmp_path / "raw" / "Tech"
    raw.mkdir(parents=True)
    legacy = raw / "legacy.md"
    legacy.write_text("---\nplatform: youtube\nextraction_status: partial\n---\n# Legacy\n", encoding="utf-8")
    current = raw / "current.md"
    current.write_text(
        "---\nplatform: web\nextraction_status: ok\nneeds_local_worker: false\n"
        "worker_status: not_required\nworker_type: none\nworker_retry_count: 0\n---\n# Current\n",
        encoding="utf-8",
    )

    plans = collect_backfill_plans(tmp_path)

    assert [plan.path for plan in plans] == [legacy]
    assert plans[0].updates["worker_status"] == "pending"
