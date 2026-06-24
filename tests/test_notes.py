from datetime import date

from bot.notes import LinkNote, note_filename, note_target_dir, render_note, slugify


def test_slugify_keeps_readable_chinese_title():
    assert slugify("台北 美食 / Coffee?") == "台北-美食-coffee"


def test_render_note_outputs_pure_markdown_no_frontmatter():
    """Raw notes should be pure markdown body — no YAML frontmatter.

    YAML frontmatter was removed from raw/ notes because it was fully
    stripped during ingestion anyway. The real frontmatter is generated
    by ingestion_v2.py when raw/ → wiki/.
    """
    note = LinkNote(
        title="Example",
        url="https://example.com",
        summary="第一句摘要。\n第二句摘要。",
        category="tech",
        captured_on=date(2026, 5, 31),
    )

    rendered = render_note(note)

    # No YAML frontmatter
    assert not rendered.startswith("---")
    assert "tags:" not in rendered
    assert "source:" not in rendered
    assert "platform:" not in rendered
    assert "status:" not in rendered

    # Title heading
    assert rendered.startswith("# Example\n\n")

    # Content present
    assert "## 原文連結\nhttps://example.com" in rendered


def test_render_note_with_log_id():
    note = LinkNote(
        title="Example",
        url="https://example.com",
        summary="摘要",
        category="general",
        captured_on=date(2026, 6, 8),
        log_id="202606081147_00001",
    )

    rendered = render_note(note)

    # Log ID section (markdown, not frontmatter key)
    assert "## Log ID\n202606081147_00001" in rendered
    # No frontmatter key-value
    assert "log_id:" not in rendered


def test_render_note_with_body_markdown():
    """Custom body_markdown overrides default body."""
    note = LinkNote(
        title="YouTube",
        url="https://youtu.be/example",
        summary="一句話重點。",
        category="tech",
        captured_on=date(2026, 5, 31),
        body_markdown="## 一句話重點\n一句話重點。\n\n## 核心摘要\n詳細內容。",
    )

    rendered = render_note(note)

    assert "## 一句話重點\n一句話重點。" in rendered
    assert "## 核心摘要\n詳細內容。" in rendered
    assert "# YouTube\n\n" in rendered
    # No YAML
    assert "summary:" not in rendered


def test_render_note_without_body_uses_summary_fallback():
    note = LinkNote(
        title="No Body",
        url="https://example.com",
        summary="Summary fallback",
        category="tech",
        captured_on=date(2026, 6, 1),
    )

    rendered = render_note(note)

    assert "## 摘要\nSummary fallback\n\n## 原文連結\nhttps://example.com" in rendered


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
