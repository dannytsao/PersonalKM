from datetime import datetime

from scripts.ingest_copilot_conversations import (
    build_raw_note,
    parse_conversation_filename,
    resolve_topic,
    unique_path,
)

SAMPLE = """---
epoch: 1784275550627
modelKey: "gemini-flash-latest|google"
topic: "Gemini API Connection Errors"
tags:
  - copilot-conversation
---

**user**: please check if there a dashboard for token spending
[Timestamp: 2026/07/17 16:05:50]

**ai**: Hello! I am Obsidian Copilot.
[Timestamp: 2026/07/17 16:05:52]
"""


def test_parse_conversation_filename_extracts_topic_and_datetime():
    parsed = parse_conversation_filename("Gemini_API_Connection_Errors@20260717_160550")
    assert parsed == ("Gemini_API_Connection_Errors", datetime(2026, 7, 17, 16, 5, 50))


def test_parse_conversation_filename_rejects_non_copilot_names():
    assert parse_conversation_filename("Recent Conversations") is None
    assert parse_conversation_filename("2026-07-16-some-food-post") is None


def test_parse_conversation_filename_handles_topic_containing_at_sign():
    # topic itself may contain "@" (e.g. an Instagram handle) — the LAST
    # "@date_time" suffix is what matters, so greedy topic match must win.
    parsed = parse_conversation_filename("user@handle_asks_about_x@20260101_000000")
    assert parsed is not None
    topic, dt = parsed
    assert topic == "user@handle_asks_about_x"
    assert dt == datetime(2026, 1, 1, 0, 0, 0)


def test_build_raw_note_filename_matches_raw_capture_convention():
    filename, content = build_raw_note(
        "Gemini API Connection Errors",
        datetime(2026, 7, 17, 16, 5, 50),
        "gemini-flash-latest|google",
        "**user**: hi\n\n**ai**: hello",
    )
    assert filename == "2026-07-17-202607171605_00001-gemini-api-connection-errors.md"
    assert "## Log ID\n202607171605_00001" in content
    assert "gemini-flash-latest|google" in content
    assert "**user**: hi" in content


def test_unique_path_avoids_clobbering_existing_file(tmp_path):
    existing = tmp_path / "note.md"
    existing.write_text("x", encoding="utf-8")
    result = unique_path(existing)
    assert result == tmp_path / "note-2.md"


def test_resolve_topic_uses_frontmatter_when_clean():
    assert (
        resolve_topic("Gemini API Connection Errors", "Gemini_API_Connection_Errors", datetime(2026, 7, 17))
        == "Gemini API Connection Errors"
    )


def test_resolve_topic_falls_back_when_frontmatter_is_json_stub():
    # Real observed corruption: Copilot's title-gen failed and left the raw
    # unparsed JSON response (topic: "```json") in frontmatter, but the
    # actual title survives, underscored, in the filename after "___title_".
    result = resolve_topic(
        '```json',
        '```json___title_LLM_API_Token_Usage_Dashboard_In',
        datetime(2026, 7, 22),
    )
    assert result == "LLM API Token Usage Dashboard In"


def test_resolve_topic_strips_trailing_comma_and_underscore():
    result = resolve_topic(
        '```json',
        '```json___title_Main_Steps_to_Learn_Obsidian,_',
        datetime(2026, 7, 23),
    )
    assert result == "Main Steps to Learn Obsidian"


def test_resolve_topic_generic_fallback_when_both_unusable():
    result = resolve_topic("```json", "```json___title_", datetime(2026, 7, 23))
    assert result == "Copilot Conversation 2026-07-23"


def test_unique_path_passthrough_when_free(tmp_path):
    target = tmp_path / "note.md"
    assert unique_path(target) == target


def test_end_to_end_move_reads_frontmatter_topic_and_model(tmp_path):
    vault = tmp_path
    convo_dir = vault / "copilot" / "copilot-conversations"
    convo_dir.mkdir(parents=True)
    src = convo_dir / "Gemini_API_Connection_Errors@20260717_160550.md"
    src.write_text(SAMPLE, encoding="utf-8")

    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_copilot_conversations.py",
            "--vault",
            str(vault),
            "--apply",
        ],
        capture_output=True,
        text=True,
        cwd=str(__file__.rsplit("/tests/", 1)[0]),
    )
    assert result.returncode == 0, result.stderr

    assert not src.exists()  # moved, not copied
    moved = list((vault / "raw" / "Tech").glob("*.md"))
    assert len(moved) == 1
    content = moved[0].read_text(encoding="utf-8")
    assert "Gemini API Connection Errors" in content
    assert "gemini-flash-latest|google" in content
    assert "**user**: please check" in content
