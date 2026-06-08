from bot.link_processor import (
    ExtractedContent,
    ensure_food_summary_details,
    extract_food_address,
    extract_food_city,
    extract_food_places,
    extract_food_name,
    extract_page_metadata,
    fallback_category,
    fallback_summary,
    fallback_youtube_deep_note,
    google_ai_mode_context_text,
    google_maps_url,
    google_ai_mode_share_content,
    instagram_content_type,
    instagram_fallback_content,
    is_google_ai_mode_share,
    is_instagram_shell_text,
    is_restricted_platform,
    line_message_context_text,
    line_message_title,
    metadata_text,
    parse_caption_tracks,
    parse_json3_transcript,
    platform_from_url,
    restricted_platform_fallback,
    should_capture_line_message_context,
    to_note,
    youtube_video_id,
)
from bs4 import BeautifulSoup


def test_fallback_category_detects_supported_topics():
    assert fallback_category("台北拍照景點", "") == "photography"
    assert fallback_category("Best cafe", "") == "food"
    assert fallback_category("Python API guide", "") == "tech"
    assert fallback_category("Random note", "") == "general"


def test_food_summary_details_extracts_restaurant_name_and_address():
    title = "「阿嬤家漁村料理」北海岸必吃海鮮"
    text = "店家位於新北市金山區磺港路189號，主打新鮮海鮮與家常料理。"
    summary = fallback_summary(title, text)

    detailed = ensure_food_summary_details(title, text, summary, "food")

    assert extract_food_name(title, text) == "阿嬤家漁村料理"
    assert extract_food_address(text) == "新北市金山區磺港路189號"
    assert extract_food_city("新北市金山區磺港路189號") == "新北市"
    assert detailed.startswith("店名：阿嬤家漁村料理；地址：新北市金山區磺港路189號；摘要：")


def test_food_summary_details_extracts_street_only_address():
    text = "地址是中山北路六段441巷46弄3號，適合聚餐。"

    assert extract_food_address(text) == "中山北路六段441巷46弄3號"


def test_food_note_body_includes_google_maps_link_for_address():
    content = ExtractedContent(
        title="「五年咖啡」天母老宅咖啡",
        text="地址是中山北路六段441巷46弄3號，適合聚餐。",
    )

    note = to_note(content, "https://example.com/food", "店名：五年咖啡；地址：中山北路六段441巷46弄3號；摘要：老宅咖啡。", "food")

    assert "## 店家資訊" in note.body_markdown
    assert "- 店名：五年咖啡" in note.body_markdown
    assert "- 地址：中山北路六段441巷46弄3號 ([Google Maps](" in note.body_markdown
    assert google_maps_url("中山北路六段441巷46弄3號") in note.body_markdown


def test_food_note_body_prefers_summary_restaurant_details():
    content = ExtractedContent(
        title="台北咖啡廳推薦",
        text="臺北市中山區圓山里中山北路三段18 邱顯傑｜台北 桃園｜旅遊 景點 空拍 咖啡廳",
    )
    summary = "店名：Rolling Dough 咖啡廳，地址：臺北市中山區圓山里中山北路三段181號；摘要：適合安排咖啡行程。"

    note = to_note(content, "https://example.com/rolling-dough", summary, "food")

    assert "- 店名：Rolling Dough 咖啡廳" in note.body_markdown
    assert "- 縣市：臺北市" in note.body_markdown
    assert "- 地址：臺北市中山區圓山里中山北路三段181號 ([Google Maps](" in note.body_markdown
    assert note.location_city == "臺北市"
    assert "中山北路三段18 邱顯傑" not in note.body_markdown


def test_food_note_body_includes_multiple_restaurant_locations():
    content = ExtractedContent(
        title="台北5間森林系咖啡廳",
        text="一邊欣賞窗外綠意，一邊喝咖啡。",
    )
    summary = (
        "店家資訊：1. 店名：咖朵咖啡 Caldo Cafe，地址：臺北市士林區至善路二段390號；"
        "2. 店名：CE' & LIB-RARY天母店，地址：臺北市士林區中山北路七段14巷2號；"
        "摘要：整理台北森林系咖啡廳。"
    )

    note = to_note(content, "https://example.com/forest-cafes", summary, "food")

    assert "### 1. 咖朵咖啡 Caldo Cafe" in note.body_markdown
    assert "- 地址：臺北市士林區至善路二段390號 ([Google Maps](" in note.body_markdown
    assert "### 2. CE' & LIB-RARY天母店" in note.body_markdown
    assert "- 地址：臺北市士林區中山北路七段14巷2號 ([Google Maps](" in note.body_markdown
    assert note.location_city == "臺北市"


def test_single_food_note_dedupes_summary_and_body_details():
    content = ExtractedContent(
        title="Chew The Day 嚼日子",
        text="店名：Chew The Day 嚼日子 地址：大同區庫倫街13巷2弄2號",
    )
    summary = "店名：Chew The Day 嚼日子，地址：大同區庫倫街13巷2弄2號；摘要：單店家咖啡廳。"

    note = to_note(content, "https://example.com/chew-the-day", summary, "food")

    assert "### 1." not in note.body_markdown
    assert note.body_markdown.count("- 店名：Chew The Day 嚼日子") == 1
    assert note.body_markdown.count("大同區庫倫街13巷2弄2號") == 2
    assert "店名：店名" not in note.body_markdown


def test_food_place_extraction_reads_instagram_pin_sections():
    text = (
        "📍咖朵咖啡 Caldo Cafe @caldocafe2011 時間：12:00-18:00 "
        "地址：臺北市士林區至善路二段390號 "
        "📍passer @passer 時間：10:00-18:00 地址：臺北市大安區瑞安街120巷10弄3號"
    )

    places = extract_food_places("台北5間森林系咖啡廳", text, "")

    assert places[0].name == "咖朵咖啡 Caldo Cafe"
    assert places[0].address == "臺北市士林區至善路二段390號"
    assert places[1].name == "passer"
    assert places[1].address == "臺北市大安區瑞安街120巷10弄3號"


def test_food_note_body_marks_city_missing_when_address_has_no_city():
    content = ExtractedContent(
        title="「五年咖啡」天母老宅咖啡",
        text="地址是中山北路六段441巷46弄3號，適合聚餐。",
    )

    note = to_note(content, "https://example.com/food", "店名：五年咖啡；地址：中山北路六段441巷46弄3號；摘要：老宅咖啡。", "food")

    assert "- 縣市：未提供" in note.body_markdown
    assert note.location_city == ""


def test_food_summary_details_marks_missing_fields_as_not_provided():
    detailed = ensure_food_summary_details("台北美食推薦", "今天介紹一家餐廳。", "這是一篇美食摘要。", "food")

    assert detailed.startswith("店名：未提供；地址：未提供；摘要：")


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
    assert platform_from_url("https://share.google/aimode/8uyYWVgle7A2ZDGFx") == "google-ai-mode"
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


def test_google_ai_mode_share_detection_and_fallback_content():
    content = google_ai_mode_share_content("https://share.google/aimode/8uyYWVgle7A2ZDGFx")

    assert is_google_ai_mode_share("https://share.google/aimode/8uyYWVgle7A2ZDGFx")
    assert is_google_ai_mode_share("https://www.share.google/aimode/8uyYWVgle7A2ZDGFx")
    assert not is_google_ai_mode_share("https://share.google/example")
    assert content.title == "Google AI Mode share"
    assert content.platform == "google-ai-mode"
    assert content.extraction_status == "blocked"
    assert content.needs_review
    assert "HTTP 429" in content.text
    assert "把 AI Mode 回答內容貼到 LINE" in content.text


def test_google_ai_mode_context_text_removes_share_url():
    url = "https://share.google/aimode/8uyYWVgle7A2ZDGFx"
    text = f"{url}\nAI Mode 回答：這篇內容整理 agent workflow 與自動化。"

    assert google_ai_mode_context_text(url, text, 200) == "AI Mode 回答：這篇內容整理 agent workflow 與自動化。"


def test_line_message_context_helpers_preserve_pasted_article_text():
    text = (
        "這是一篇很長的 LINE 貼文，介紹 Codex 如何搭配 ComfyUI 使用，並整理多個實作案例。"
        "內容包含工作流、節點相容性、批量出圖，以及學習心得。"
        "https://example.com/article"
    )

    assert "https://example.com/article" not in line_message_context_text(text, 500)
    assert should_capture_line_message_context(text, 500)
    assert line_message_title(text).startswith("這是一篇很長的 LINE 貼文")


def test_line_message_context_ignores_short_link_only_messages():
    assert not should_capture_line_message_context("看這個 https://example.com", 500)


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
