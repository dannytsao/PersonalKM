from scripts.archive_inbox import collect_archive_moves, collect_moves, frontmatter_status


def test_frontmatter_status_reads_status_value():
    markdown = """---
tags: [技術]
status: archived
---

# Note
"""

    assert frontmatter_status(markdown) == "archived"


def test_collect_archive_moves_only_moves_archived_notes(tmp_path):
    vault = tmp_path
    inbox_tech = vault / "Inbox" / "Tech"
    archive_tech = vault / "Archive" / "Tech"
    inbox_tech.mkdir(parents=True)
    archive_tech.mkdir(parents=True)

    archived = inbox_tech / "archived.md"
    unread = inbox_tech / "unread.md"
    archived.write_text("---\nstatus: archived\n---\n# Archived\n", encoding="utf-8")
    unread.write_text("---\nstatus: unread\n---\n# Unread\n", encoding="utf-8")

    moves = collect_archive_moves(vault)

    assert len(moves) == 1
    assert moves[0].source == archived
    assert moves[0].target == archive_tech / "archived.md"


def test_collect_archive_moves_avoids_target_name_collision(tmp_path):
    vault = tmp_path
    inbox_general = vault / "Inbox" / "General"
    archive_general = vault / "Archive" / "General"
    inbox_general.mkdir(parents=True)
    archive_general.mkdir(parents=True)

    note = inbox_general / "same.md"
    existing = archive_general / "same.md"
    note.write_text("---\nstatus: done\n---\n# Done\n", encoding="utf-8")
    existing.write_text("---\nstatus: archived\n---\n# Existing\n", encoding="utf-8")

    moves = collect_archive_moves(vault)

    assert moves[0].target == archive_general / "same-2.md"


def test_collect_moves_sends_x_status_to_trash_as_non_markdown(tmp_path):
    vault = tmp_path
    inbox_food = vault / "Inbox" / "Food"
    trash_food = vault / "Trash" / "Food"
    inbox_food.mkdir(parents=True)
    trash_food.mkdir(parents=True)

    note = inbox_food / "bad.md"
    note.write_text("---\nstatus: X\n---\n# Bad\n", encoding="utf-8")

    moves = collect_moves(vault)

    assert len(moves) == 1
    assert moves[0].source == note
    assert moves[0].target == trash_food / "bad.md.trash"


def test_collect_moves_keeps_unread_in_inbox(tmp_path):
    vault = tmp_path
    inbox_tech = vault / "Inbox" / "Tech"
    inbox_tech.mkdir(parents=True)
    note = inbox_tech / "unread.md"
    note.write_text("---\nstatus: unread\n---\n# Unread\n", encoding="utf-8")

    assert collect_moves(vault) == []
