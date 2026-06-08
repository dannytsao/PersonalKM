from datetime import datetime

from bot.app import LINE_PARTS_FILE, collect_line_message_part, generate_line_log_id


def test_collect_line_message_part_merges_when_all_parts_arrive(tmp_path):
    assert collect_line_message_part(tmp_path, "[文章 2/2]\n第二段 https://example.com/b") is None

    merged, log_id = collect_line_message_part(tmp_path, "[文章 1/2]\n第一段 https://example.com/a")

    assert merged == "[文章 1/2]\n第一段 https://example.com/a\n\n[文章 2/2]\n第二段 https://example.com/b"
    assert log_id.endswith("_00001")
    assert (tmp_path / LINE_PARTS_FILE).read_text(encoding="utf-8").strip() == "{}"


def test_collect_line_message_part_passes_through_unmarked_text(tmp_path):
    text, log_id = collect_line_message_part(tmp_path, "一般 LINE 貼文")

    assert text == "一般 LINE 貼文"
    assert log_id.endswith("_00001")


def test_generate_line_log_id_uses_minute_and_five_digit_sequence(tmp_path):
    first = generate_line_log_id(tmp_path, datetime(2026, 6, 8, 11, 47))
    second = generate_line_log_id(tmp_path, datetime(2026, 6, 8, 11, 47, 59))
    next_minute = generate_line_log_id(tmp_path, datetime(2026, 6, 8, 11, 48))

    assert first == "202606081147_00001"
    assert second == "202606081147_00002"
    assert next_minute == "202606081148_00001"


def test_multipart_line_message_keeps_same_log_id(tmp_path):
    assert collect_line_message_part(tmp_path, "[文章 1/2]\n第一段") is None
    merged, log_id = collect_line_message_part(tmp_path, "[文章 2/2]\n第二段")

    assert merged == "[文章 1/2]\n第一段\n\n[文章 2/2]\n第二段"
    assert log_id.endswith("_00001")
