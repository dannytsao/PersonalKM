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
    assert "needs_local_worker: false" in rendered
    assert "worker_status: not_required" in rendered
    assert "worker_type: none" in rendered
    assert "worker_retry_count: 0" in rendered
    assert "status: unread" in rendered
    assert "## 原文連結\nhttps://example.com" in rendered


def test_render_note_includes_pending_worker_metadata():
    note = LinkNote(
        title="YouTube",
        url="https://youtu.be/example",
        summary="需要本機補強。",
        category="tech",
        captured_on=date(2026, 6, 10),
        platform="youtube",
        extraction_status="partial",
        needs_review=True,
        needs_local_worker=True,
        worker_status="pending",
        worker_type="omnichannel_md",
        worker_retry_count=1,
        worker_error="yt_dlp_not_installed",
    )

    rendered = render_note(note)

    assert "needs_local_worker: true" in rendered
    assert "worker_status: pending" in rendered
    assert "worker_type: omnichannel_md" in rendered
    assert "worker_retry_count: 1" in rendered
    assert "worker_error: yt_dlp_not_installed" in rendered


def test_render_note_includes_content_type_when_present():
    note = LinkNote(
        title="Example",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 5, 31),
        content_type="webpage",
    )

    rendered = render_note(note)

    assert "content_type: webpage" in rendered


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


def test_render_note_includes_location_city_when_present():
    note = LinkNote(
        title="Cafe",
        url="https://example.com",
        summary="店名：Cafe；地址：臺北市中山區中山北路三段181號",
        category="food",
        captured_on=date(2026, 5, 31),
        location_city="臺北市",
    )

    rendered = render_note(note)

    assert "location_city: 臺北市" in rendered


def test_render_note_includes_log_id_metadata_and_section():
    note = LinkNote(
        title="Example",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 6, 8),
        log_id="202606081147_00001",
    )

    rendered = render_note(note)

    assert "log_id: 202606081147_00001" in rendered
    assert "## Log ID\n202606081147_00001" in rendered


def test_render_note_uses_custom_body_markdown():
    note = LinkNote(
        title="YouTube",
        url="https://youtu.be/example",
        summary="一句話重點。",
        category="tech",
        captured_on=date(2026, 5, 31),
        platform="youtube",
        body_markdown="## 一句話重點\n一句話重點。\n\n## 核心摘要\n詳細內容。",
    )

    rendered = render_note(note)

    assert "summary: 一句話重點。" in rendered
    assert "## 一句話重點\n一句話重點。" in rendered
    assert "## 核心摘要\n詳細內容。" in rendered


def test_note_filename_uses_date_and_title():
    note = LinkNote(
        title="Example Title",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 5, 31),
    )

    assert note_filename(note) == "2026-05-31-example-title.md"


def test_note_filename_includes_log_id_when_present():
    note = LinkNote(
        title="Example Title",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 5, 31),
        log_id="202606081147_00001",
    )

    assert note_filename(note) == "2026-05-31-202606081147_00001-example-title.md"


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
