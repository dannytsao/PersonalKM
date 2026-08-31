"""Tests for the wikilink stop-words filter (Sprint 3)."""

from pathlib import Path

import pytest


def _make_stop_words_file(tmp_path: Path, words: list[str]) -> Path:
    p = tmp_path / "stop_words.txt"
    p.write_text("\n".join(words), encoding="utf-8")
    return p


class TestLoadStopWords:
    def test_loads_basic_words(self, tmp_path: Path):
        from src.personalkm.propagate.stop_words import load_stop_words

        p = _make_stop_words_file(tmp_path, ["test", "環境", "教學"])
        words = load_stop_words(p)
        assert "test" in words
        assert "環境" in words
        assert "教學" in words
        assert len(words) == 3

    def test_skips_comments_and_section_headers(self, tmp_path: Path):
        from src.personalkm.propagate.stop_words import load_stop_words

        content = (
            "# PersonalKM stop words\n"
            "[chinese]\n"
            "測試\n"
            "[english]\n"
            "the\n"
            "# this is a comment\n"
            "and\n"
        )
        p = tmp_path / "stop_words.txt"
        p.write_text(content, encoding="utf-8")
        words = load_stop_words(p)
        assert "測試" in words
        assert "the" in words
        assert "and" in words
        # Section headers and comments should not be in the set
        assert "[chinese]" not in words
        assert "#" not in words

    def test_handles_inline_comments(self, tmp_path: Path):
        from src.personalkm.propagate.stop_words import load_stop_words

        p = _make_stop_words_file(tmp_path, ["測試  # 常見的", "環境  # over-linked term"])
        words = load_stop_words(p)
        assert "測試" in words
        assert "環境" in words

    def test_missing_file_returns_empty_set(self, tmp_path: Path):
        from src.personalkm.propagate.stop_words import load_stop_words

        missing = tmp_path / "nonexistent.txt"
        words = load_stop_words(missing)
        assert words == set()

    def test_lowercases_all_words(self, tmp_path: Path):
        from src.personalkm.propagate.stop_words import load_stop_words

        p = _make_stop_words_file(tmp_path, ["Test", "GUIDE"])
        words = load_stop_words(p)
        assert "test" in words
        assert "guide" in words


class TestFilterWikilinks:
    def test_removes_stop_words(self):
        from src.personalkm.propagate.stop_words import filter_wikilinks

        result = filter_wikilinks(
            ["claude-code", "測試", "docker", "教學", "python"],
            {"測試", "教學", "環境"},
        )
        assert result == ["claude-code", "docker", "python"]

    def test_whitelist_keeps_even_stop_words(self):
        from src.personalkm.propagate.stop_words import filter_wikilinks

        result = filter_wikilinks(
            ["測試", "環境", "claude-code"],
            {"測試", "環境"},
            existing_slugs={"測試", "claude-code"},  # 測試 is whitelisted
        )
        # 測試 kept because it's whitelisted; 環境 dropped
        assert result == ["測試", "claude-code"]

    def test_empty_slugs_returns_empty(self):
        from src.personalkm.propagate.stop_words import filter_wikilinks

        assert filter_wikilinks([], {"test"}) == []

    def test_no_stop_words_passthrough(self):
        from src.personalkm.propagate.stop_words import filter_wikilinks

        result = filter_wikilinks(
            ["claude-code", "docker", "python"],
            {"測試", "教學"},
        )
        assert result == ["claude-code", "docker", "python"]

    def test_case_insensitive_filtering(self):
        from src.personalkm.propagate.stop_words import filter_wikilinks

        result = filter_wikilinks(
            ["Claude-Code", "測試", "DOCKER"],
            {"測試", "docker"},
            existing_slugs={"claude-code"},  # whitelist also lowercased
        )
        assert "DOCKER" not in result  # dropped because "docker" is a stop word

    def test_preserves_order(self):
        from src.personalkm.propagate.stop_words import filter_wikilinks

        result = filter_wikilinks(
            ["b", "測試", "a", "教學", "c"],
            {"測試", "教學"},
        )
        assert result == ["b", "a", "c"]