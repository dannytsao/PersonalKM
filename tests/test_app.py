from bot.app import LINE_PARTS_FILE, collect_line_message_part


def test_collect_line_message_part_merges_when_all_parts_arrive(tmp_path):
    assert collect_line_message_part(tmp_path, "[文章 2/2]\n第二段 https://example.com/b") is None

    merged = collect_line_message_part(tmp_path, "[文章 1/2]\n第一段 https://example.com/a")

    assert merged == "[文章 1/2]\n第一段 https://example.com/a\n\n[文章 2/2]\n第二段 https://example.com/b"
    assert (tmp_path / LINE_PARTS_FILE).read_text(encoding="utf-8").strip() == "{}"


def test_collect_line_message_part_passes_through_unmarked_text(tmp_path):
    assert collect_line_message_part(tmp_path, "一般 LINE 貼文") == "一般 LINE 貼文"
