"""Contract: wiki page filenames must fit Linux's 255-BYTE filename limit.

macOS (APFS) allows 255 characters, so CJK-heavy names that work on the
Mac fail on Linux (Render, cloud sessions) where ext4 caps at 255 bytes —
each CJK character is 3 bytes in UTF-8. Seven 2026-07..09 lifestyle-vault
notes named after full social-post titles (269-314 bytes) broke `git
checkout` on Linux until they were renamed on 2026-11-10. New names are
capped by normalize_entity_name (af57ce7); this contract keeps it that way.
"""

from personalkm.propagate.entity_dedup import normalize_entity_name

LINUX_NAME_MAX_BYTES = 255

# Real titles that produced >255-byte filenames before the cap.
LONG_TITLES = (
    (
        '冰淇淋貓的軟爛生活 on Instagram: "🔥都市旁的仙境，山裡的米其林農家菜！菜色跟著農場採收變化，'
        "苦茶油雞的炸薑片脆得像洋芋片，苦茶油麵線很有水準。吃飯就像到山裡朋友家作客。記得先訂位，"
        "沒預約真的可能會像我們第一次一樣白跑一趟😝…"
    ),
    (
        "台北自家烘焙咖啡廳，捷運石牌站咖啡廳，台北咖啡廳推薦，隱身北投老宅咖啡廳，Alofi Coffee位於"
        "臺北市北投區致遠二路147巷2號，石牌商圈，巷弄美食，小巧深色咖啡色的木質調空間，店有可愛家貓，"
        "提供手沖咖啡與義式咖啡，這裡咖啡高手雲集…"
    ),
    (
        "三灣粉愛花草園│三灣粉紅草│苗栗粉紅草》苗栗三灣新亮點，細長粉色的芒草像是毛絨絨的粉嫩花毯 "
        "怎麼拍都好迷人像是一幅畫 秋季粉芒草即將旋風席捲全台【三灣粉紅芒草】【三灣新景點】 | "
        "GO阿綸@旅人狂潮 | 休閒旅遊分享 | 痞客邦 | PIXNET"
    ),
    "あ" * 300,  # kana: also 3 bytes per char
    "한" * 300,  # hangul: also 3 bytes per char
)


def test_date_prefixed_page_filename_fits_linux_byte_limit() -> None:
    for title in LONG_TITLES:
        slug = normalize_entity_name(title)
        assert slug, title
        # Longest form written: entity_dedup's collision name
        # "{YYYY-MM-DD}-{slug}-{6-hex}.md" (ingestion_v2 omits the suffix).
        filename = f"2026-11-10-{slug}-abcdef.md"
        assert len(filename.encode("utf-8")) <= LINUX_NAME_MAX_BYTES, (
            len(filename.encode("utf-8")),
            filename,
        )
