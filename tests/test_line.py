from bot.line import extract_urls


def test_extract_urls_deduplicates_and_trims_punctuation():
    text = "看這個 https://example.com/a?x=1，還有 https://example.com/a?x=1。"

    assert extract_urls(text) == ["https://example.com/a?x=1"]
