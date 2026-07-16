"""Unit tests for the Resolver Layer adapters and URL extractor.

Tests are design to be deterministic — they mock network calls
for the fetch() methods and test business logic directly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.personalkm.resolve.adapters.base import (
    AuthWallError,
    FetchedContent,
    GoneError,
    classify_url,
)
from src.personalkm.resolve.url_extractor import extract_url, extract_all_urls
from src.personalkm.resolve.runner import _find_adapter


# ── test fixtures ─────────────────────────────────────────────

FIXTURES = Path(__file__).parent.parent / "fixtures" / "resolve"


# ── classify_url tests ────────────────────────────────────────

class TestClassifyUrl:
    def test_youtube_watch(self):
        assert classify_url("https://www.youtube.com/watch?v=abc123") == "youtube"

    def test_youtube_short(self):
        assert classify_url("https://youtu.be/abc123") == "youtube"

    def test_youtube_shorts(self):
        assert classify_url("https://www.youtube.com/shorts/abc123") == "youtube"

    def test_github_root(self):
        assert classify_url("https://github.com/owner/repo") == "github"

    def test_github_tree(self):
        assert classify_url("https://github.com/owner/repo/tree/main") == "github"

    def test_github_blob(self):
        assert classify_url("https://github.com/owner/repo/blob/main/README.md") == "github"

    def test_github_subdir(self):
        # The classify_url pattern is repo-level — any github.com/owner/repo matches
        assert classify_url("https://github.com/nousresearch/hermes") == "github"

    def test_threads(self):
        assert classify_url("https://www.threads.net/@user/post/abc") == "threads"

    def test_instagram(self):
        assert classify_url("https://www.instagram.com/p/abc123/") == "instagram"

    def test_x(self):
        assert classify_url("https://x.com/user/status/123") == "x"
        assert classify_url("https://twitter.com/user/status/123") == "x"

    def test_tiktok(self):
        assert classify_url("https://www.tiktok.com/@user/video/123") == "tiktok"
        assert classify_url("https://vm.tiktok.com/abc") == "tiktok"

    def test_generic_http(self):
        assert classify_url("https://example.com/article") == "generic"

    def test_generic_news(self):
        assert classify_url("https://news.ycombinator.com/item?id=123") == "generic"

    def test_generic_unknown(self):
        assert classify_url("https://some-unknown-site.com/page") == "generic"

    def test_no_protocol(self):
        # Without https://, classify_url should return generic
        assert classify_url("example.com") == "generic"


# ── URL extractor tests ───────────────────────────────────────

class TestExtractUrl:
    def test_frontmatter_url(self, tmp_path: Path):
        """Frontmatter url: field should be preferred."""
        f = tmp_path / "test.md"
        f.write_text(
            "---\ncreated: 2026-07-04\nsource: line\n"
            "url: https://github.com/example/repo\nfetch_status: pending\n---\n"
            "Some body text"
        )
        assert extract_url(f) == "https://github.com/example/repo"

    def test_yuanyin_lianjie_section(self, tmp_path: Path):
        """原文連結 section should be second priority."""
        f = tmp_path / "test.md"
        f.write_text(
            "# A Note\n\n"
            "## 摘要\nsome summary\n\n"
            "## 原文連結\nhttps://example.com/article\n\n"
            "## 內含連結\n- https://fallback.com"
        )
        assert extract_url(f) == "https://example.com/article"

    def test_neihan_lianjie_section(self, tmp_path: Path):
        """內含連結 section should be third priority."""
        f = tmp_path / "test.md"
        f.write_text(
            "# A Note\n\n"
            "## 內含連結\n- https://github.com/other/repo\n- https://fallback.com"
        )
        assert extract_url(f) == "https://github.com/other/repo"

    def test_fallback_any_url(self, tmp_path: Path):
        """Any https URL works as last resort."""
        f = tmp_path / "test.md"
        f.write_text("Some text with a https://example.com/fallback link in it")
        assert extract_url(f) == "https://example.com/fallback"

    def test_no_url_returns_none(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("Just some text without any links")
        assert extract_url(f) is None

    def test_extract_all_urls(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text(
            "# Multi-link\n\n"
            "Link A: https://site1.com\n"
            "Link B: https://site2.com/page\n"
        )
        urls = extract_all_urls(f)
        assert len(urls) == 2
        assert "https://site1.com" in urls
        assert "https://site2.com/page" in urls


# ── Adapter matching tests ────────────────────────────────────

class TestAdapterSelection:
    def test_github_url_matches(self):
        adapter = _find_adapter("https://github.com/owner/repo")
        assert adapter is not None
        assert adapter.source_type == "github"

    def test_youtube_url_matches(self):
        adapter = _find_adapter("https://youtu.be/abc123")
        assert adapter is not None
        assert adapter.source_type == "youtube"

    def test_youtube_watch_matches(self):
        adapter = _find_adapter("https://www.youtube.com/watch?v=abc123")
        assert adapter is not None
        assert adapter.source_type == "youtube"

    def test_generic_url_matches(self):
        adapter = _find_adapter("https://example.com/article")
        assert adapter is not None
        assert adapter.source_type == "generic"

    def test_threads_url_uses_jina_adapter(self):
        adapter = _find_adapter("https://www.threads.net/@user/post/abc")
        assert adapter is not None
        assert adapter.__class__.__name__ == "JinaAdapter"

    def test_x_url_has_no_cloud_adapter(self):
        assert _find_adapter("https://x.com/user/status/123") is None


# ── Healthy test helper ───────────────────────────────────────

class TestFetchedContent:
    def test_create_fetched_content(self):
        fc = FetchedContent(
            url="https://example.com",
            source_type="generic",
            title="Test Article",
            markdown="## Hello\n\nThis is test content.",
            meta={"fetched_from": "https://example.com"},
        )
        assert fc.url == "https://example.com"
        assert fc.source_type == "generic"
        assert "Test Article" in fc.title
        assert len(fc.markdown) > 0
        assert fc.meta["fetched_from"] == "https://example.com"

    def test_minimal_fetched_content(self):
        fc = FetchedContent(
            url="https://github.com/owner/repo",
            source_type="github",
        )
        assert fc.url == "https://github.com/owner/repo"
        assert fc.title == ""
        assert fc.markdown == ""
        assert fc.meta == {}


# ── GitHub adapter unit tests (mock network) ──────────────────

class TestGitHubAdapter:
    def test_matches_various_urls(self):
        from src.personalkm.resolve.adapters.github import GitHubAdapter

        a = GitHubAdapter()
        assert a.matches("https://github.com/owner/repo")
        assert a.matches("https://github.com/owner/repo/tree/main")
        assert a.matches("https://github.com/owner/repo/blob/main/README.md")
        assert not a.matches("https://example.com")
        assert not a.matches("https://github.com")  # missing owner/repo

    def test_raises_on_invalid_url(self):
        from src.personalkm.resolve.adapters.github import GitHubAdapter

        a = GitHubAdapter()
        with pytest.raises(ValueError, match="Not a GitHub URL"):
            a.fetch("https://example.com")

    @patch("src.personalkm.resolve.adapters.github.urllib.request")
    def test_fetch_readme(self, mock_request):
        from src.personalkm.resolve.adapters.github import GitHubAdapter

        # Mock the HTTP response
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"# Test README\n\nThis is a test."
        mock_resp.headers = {"Content-Type": "text/plain; charset=utf-8"}
        mock_request.urlopen.return_value.__enter__.return_value = mock_resp

        a = GitHubAdapter()
        result = a.fetch("https://github.com/testuser/testrepo")

        assert result.source_type == "github"
        assert result.title == "testuser/testrepo"
        assert "Test README" in result.markdown


# ── YouTube adapter unit tests ────────────────────────────────

class TestYouTubeAdapter:
    def test_matches_various_urls(self):
        from src.personalkm.resolve.adapters.youtube import YouTubeAdapter

        a = YouTubeAdapter()
        assert a.matches("https://www.youtube.com/watch?v=abc123")
        assert a.matches("https://youtu.be/abc123")
        assert a.matches("https://www.youtube.com/shorts/abc123")
        assert not a.matches("https://example.com")

    def test_raises_on_invalid_url(self):
        from src.personalkm.resolve.adapters.youtube import YouTubeAdapter

        a = YouTubeAdapter()
        with pytest.raises((GoneError, AuthWallError, RuntimeError)):
            a.fetch("https://youtu.be/INVALIDVIDEOID")


# ── Generic adapter unit tests ────────────────────────────────

class TestGenericAdapter:
    def test_matches_generic_url(self):
        from src.personalkm.resolve.adapters.generic import GenericAdapter

        a = GenericAdapter()
        assert a.matches("https://example.com/article")
        assert a.matches("https://news.ycombinator.com/item?id=123")
        assert a.matches("https://zh.wikipedia.org/zh-tw/Python")
        assert not a.matches("https://www.youtube.com/watch?v=abc")
        assert not a.matches("https://github.com/owner/repo")

    def test_format_duration(self):
        from src.personalkm.resolve.adapters.youtube import YouTubeAdapter

        a = YouTubeAdapter()
        assert a._format_duration(0) == "0m 0s"
        assert a._format_duration(65) == "1m 5s"
        assert a._format_duration(3661) == "1h 1m 1s"

    def test_parse_vtt_basic(self):
        from src.personalkm.resolve.adapters.youtube import YouTubeAdapter

        a = YouTubeAdapter()
        vtt = (
            "WEBVTT\nKind: captions\nLanguage: zh-TW\n\n"
            "00:00:01.000 --> 00:00:04.000\nHello world\n\n"
            "00:00:05.000 --> 00:00:08.000\nSecond line\n"
        )
        result = a._parse_vtt(vtt)
        assert result == "Hello world\nSecond line"

    def test_parse_vtt_with_tags(self):
        from src.personalkm.resolve.adapters.youtube import YouTubeAdapter

        a = YouTubeAdapter()
        vtt = (
            "WEBVTT\n\n"
            "1\n00:00:01.000 --> 00:00:03.000\n<c>Hello</c> <c>there</c>\n\n"
            "2\n00:00:04.000 --> 00:00:06.000\n<c>Line two</c>\n"
        )
        result = a._parse_vtt(vtt)
        assert result == "Hello there\nLine two"


# ── Runner tests ──────────────────────────────────────────────

class TestRunner:
    def test_get_resolved_content_no_raw_dir(self, tmp_path: Path):
        """get_resolved_content should return None for non-vault paths."""
        from src.personalkm.resolve.runner import get_resolved_content

        fake_path = tmp_path / "some/deep/path/note.md"
        fake_path.parent.mkdir(parents=True)
        fake_path.write_text("# test")

        assert get_resolved_content(fake_path) is None

    def test_get_resolved_content_not_found(self, tmp_path: Path):
        """get_resolved_content should return None when no resolved/ counterpart."""
        from src.personalkm.resolve.runner import get_resolved_content

        # Simulate vault/raw/Tech/note.md
        raw_path = tmp_path / "vault" / "raw" / "Tech" / "note.md"
        raw_path.parent.mkdir(parents=True)
        raw_path.write_text("# test")

        assert get_resolved_content(raw_path) is None

    def test_get_resolved_content_found(self, tmp_path: Path):
        """get_resolved_content should return content when resolved/ counterpart exists."""
        from src.personalkm.resolve.runner import get_resolved_content

        # Simulate vault/raw/Tech/note.md  + vault/resolved/Tech/note.md
        raw_path = tmp_path / "vault" / "raw" / "Tech" / "note.md"
        raw_path.parent.mkdir(parents=True)
        raw_path.write_text("# raw note")

        resolved_path = tmp_path / "vault" / "resolved" / "Tech" / "note.md"
        resolved_path.parent.mkdir(parents=True)
        resolved_path.write_text("# Resolved content with full article text")

        content = get_resolved_content(raw_path)
        assert content is not None
        assert "Resolved content" in content

    def test_create_social_auth_stub_marks_worker_pending(self, tmp_path: Path):
        from src.personalkm.resolve.runner import _create_stub

        raw = tmp_path / "vault" / "raw" / "Tech" / "x.md"
        raw.parent.mkdir(parents=True)
        raw.write_text("# X post\n\ncaption from user")

        stubs = tmp_path / "vault" / "wiki" / "stubs"
        _create_stub(
            stubs,
            Path("Tech/x.md"),
            "https://x.com/user/status/123",
            "auth_required",
            raw_path=raw,
        )

        stub = stubs / "Tech" / "x.md"
        content = stub.read_text(encoding="utf-8")
        assert "platform: x" in content
        assert "content_type: social_post" in content
        assert "needs_local_worker: true" in content
        assert "worker_status: pending" in content
        assert "caption from user" in content
