from datetime import date

from bot.notes import LinkNote, note_filename, note_target_dir, render_note, slugify


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
    assert "platform: web" in rendered
    assert "extraction_status: ok" in rendered
    assert "needs_review: false" in rendered
    assert "status: unread" in rendered
    assert "## 原文連結\nhttps://example.com" in rendered


def test_render_note_includes_blocked_platform_metadata():
    note = LinkNote(
        title="Instagram Reel",
        url="https://www.instagram.com/reel/abc/",
        summary="需要直接開啟查看。",
        category="general",
        captured_on=date(2026, 5, 31),
        platform="instagram",
        extraction_status="blocked",
        needs_review=True,
    )

    rendered = render_note(note)

    assert "platform: instagram" in rendered
    assert "extraction_status: blocked" in rendered
    assert "needs_review: true" in rendered


def test_note_filename_uses_date_and_title():
    note = LinkNote(
        title="Example Title",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 5, 31),
    )

    assert note_filename(note) == "2026-05-31-example-title.md"


def test_note_target_dir_routes_known_categories():
    captured_on = date(2026, 5, 31)

    assert note_target_dir(
        LinkNote("Cafe", "https://example.com", "摘要", "food", captured_on), "Inbox"
    ) == "Inbox/Food"
    assert note_target_dir(
        LinkNote("API", "https://example.com", "摘要", "tech", captured_on), "Inbox"
    ) == "Inbox/Tech"
    assert note_target_dir(
        LinkNote("Spot", "https://example.com", "摘要", "photography", captured_on), "Inbox"
    ) == "Inbox/Photography"
    assert note_target_dir(
        LinkNote("Unknown", "https://example.com", "摘要", "general", captured_on), "Inbox"
    ) == "Inbox/General"
