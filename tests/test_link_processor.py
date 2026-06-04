from bot.link_processor import fallback_category, parse_caption_tracks, parse_json3_transcript, youtube_video_id


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
