from bot.link_processor import fallback_category


def test_fallback_category_detects_supported_topics():
    assert fallback_category("台北拍照景點", "") == "photography"
    assert fallback_category("Best cafe", "") == "food"
    assert fallback_category("Python API guide", "") == "tech"
    assert fallback_category("Random note", "") == "general"
