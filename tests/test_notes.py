from datetime import date

from bot.notes import LinkNote, note_filename, render_note, slugify


def test_slugify_keeps_readable_chinese_title():
    assert slugify("台北 美食 / Coffee?") == "台北-美食-coffee"


def test_render_note_matches_obsidian_template():
    note = LinkNote(
        title="Example",
        url="https://example.com",
        summary="第一句摘要。\n第二句摘要。",
        category="tech",
        captured_on=date(2026, 5, 31),
    )

    rendered = render_note(note)

    assert "tags: [技術]" in rendered
    assert "source: LINE" in rendered
    assert "status: unread" in rendered
    assert "## 原文連結\nhttps://example.com" in rendered


def test_note_filename_uses_date_and_title():
    note = LinkNote(
        title="Example Title",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 5, 31),
    )

    assert note_filename(note) == "2026-05-31-example-title.md"
