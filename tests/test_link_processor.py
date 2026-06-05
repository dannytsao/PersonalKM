from bot.link_processor import (
    extract_page_metadata,
    fallback_category,
    fallback_youtube_deep_note,
    instagram_content_type,
    instagram_fallback_content,
    is_instagram_shell_text,
    is_restricted_platform,
    metadata_text,
    parse_caption_tracks,
    parse_json3_transcript,
    platform_from_url,
    restricted_platform_fallback,
    youtube_video_id,
)
from bs4 import BeautifulSoup


def test_fallback_category_detects_supported_topics():
    assert fallback_category("台北拍照景點", "") == "photography"
    assert fallback_category("Best cafe", "") == "food"
    assert fallback_category("Python API guide", "") == "tech"
    assert fallback_category("Random note", "") == "general"


def test_youtube_video_id_supports_common_url_shapes():
    assert youtube_video_id("https://youtu.be/abc123?si=xyz") == "abc123"
    assert youtube_video_id("https://www.youtube.com/watch?v=abc123&t=10s") == "abc123"
    assert youtube_video_id("https://m.youtube.com/shorts/abc123") == "abc123"
    assert youtube_video_id("https://www.youtube.com/embed/abc123") == "abc123"
    assert youtube_video_id("https://example.com/watch?v=abc123") is None


def test_instagram_content_type_supports_reels_and_posts():
    assert instagram_content_type("https://www.instagram.com/reel/DYqdHRZSr59/?igsh=abc") == "reel"
    assert instagram_content_type("https://instagram.com/p/abc123/") == "p"
    assert instagram_content_type("https://example.com/reel/DYqdHRZSr59/") is None


def test_instagram_shell_text_detects_login_template():
    text = "Instagram from Meta Log in Sign up About Blog Jobs Help API Privacy Terms"

    assert is_instagram_shell_text(text)


def test_instagram_fallback_content_is_not_platform_description():
    content = instagram_fallback_content("reel")

    assert content.title == "Instagram Reel"
    assert content.platform == "instagram"
    assert content.extraction_status == "blocked"
    assert content.needs_review
    assert "無法可靠取得貼文或影片內容" in content.text


def test_platform_from_url_detects_restricted_platforms():
    assert platform_from_url("https://www.instagram.com/reel/abc/") == "instagram"
    assert platform_from_url("https://www.tiktok.com/@user/video/1") == "tiktok"
    assert platform_from_url("https://x.com/user/status/1") == "x"
    assert platform_from_url("https://www.threads.net/@user/post/1") == "threads"
    assert platform_from_url("https://example.com/a") == "web"


def test_restricted_platform_fallback_sets_review_metadata():
    content = restricted_platform_fallback("https://x.com/user/status/1")

    assert content.platform == "x"
    assert content.extraction_status == "blocked"
    assert content.needs_review
    assert content.title == "X/Twitter post"


def test_is_restricted_platform():
    assert is_restricted_platform("https://www.tiktok.com/@user/video/1")
    assert not is_restricted_platform("https://example.com/a")


def test_extract_page_metadata_reads_open_graph_and_twitter_cards():
    soup = BeautifulSoup(
        """
        <html><head>
          <meta property="og:title" content="OG Title">
          <meta name="twitter:description" content="Twitter description">
        </head><body>Body text</body></html>
        """,
        "html.parser",
    )

    metadata = extract_page_metadata(soup)

    assert metadata == {"title": "OG Title", "description": "Twitter description"}
    assert metadata_text(metadata) == "OG Title Twitter description"


def test_parse_caption_tracks_reads_youtube_track_list():
    tracks = parse_caption_tracks(
        """
        <transcript_list>
          <track id="0" name="" lang_code="en" lang_original="English" />
          <track id="1" name="繁體中文" lang_code="zh-Hant" lang_original="繁體中文" />
        </transcript_list>
        """
    )

    assert tracks == [
        {"lang_code": "en", "name": "", "kind": ""},
        {"lang_code": "zh-Hant", "name": "繁體中文", "kind": ""},
    ]


def test_parse_json3_transcript_flattens_segments():
    payload = {
        "events": [
            {"segs": [{"utf8": "第一句"}, {"utf8": "\n"}, {"utf8": "摘要"}]},
            {"segs": [{"utf8": "第二句"}]},
        ]
    }

    assert parse_json3_transcript(payload) == "第一句 摘要 第二句"


def test_fallback_youtube_deep_note_has_required_sections():
    summary, category, body = fallback_youtube_deep_note(
        "AI 工具教學",
        "https://youtu.be/example",
        "這支影片介紹 AI 工具如何規劃與執行工作。",
    )

    assert summary
    assert category == "tech"
    assert "## 一句話重點" in body
    assert "## 核心摘要" in body
    assert "## 重點條列" in body
    assert "## 可行動項目" in body
    assert "## 關鍵概念" in body
    assert "## 原文連結\nhttps://youtu.be/example" in body
