import json
from datetime import date
from typing import Optional
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from bot.config import Settings
from bot.notes import LinkNote


CATEGORY_VALUES = {"photography", "food", "tech", "general"}
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
YOUTUBE_LANG_PRIORITY = ("zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "zh", "en")
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
INSTAGRAM_CONTENT_PATHS = {"p", "reel", "reels", "tv"}


async def fetch_page(url: str, timeout_seconds: float, max_chars: int) -> tuple[str, str]:
    headers = {
        "User-Agent": "PersonalKMLineBot/0.1 (+https://github.com/dannytsao/PersonalKM)"
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = " ".join(soup.get_text(" ").split())
    return title[:180], text[:max_chars]


def youtube_video_id(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        return video_id or None

    if host not in YOUTUBE_HOSTS:
        return None

    if parsed.path == "/watch":
        return parse_qs(parsed.query).get("v", [None])[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}:
        return path_parts[1]
    return None


def instagram_content_type(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in INSTAGRAM_HOSTS:
        return None

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in INSTAGRAM_CONTENT_PATHS:
        return path_parts[0]
    return None


def is_instagram_shell_text(text: str) -> bool:
    lowered = text.lower()
    shell_markers = [
        "instagram from meta",
        "about blog jobs help api privacy terms",
        "log in",
        "sign up",
        "meta verified",
    ]
    return "instagram" in lowered and sum(marker in lowered for marker in shell_markers) >= 2


def instagram_fallback_content(content_type: str) -> tuple[str, str]:
    label = "Instagram Reel" if content_type in {"reel", "reels"} else "Instagram post"
    return (
        label,
        (
            f"這是一個 {label} 連結。Instagram 通常需要登入或會阻擋自動化擷取，"
            "目前無法可靠取得貼文或影片內容。請直接開啟原文連結查看。"
        ),
    )


async def fetch_youtube_metadata(client: httpx.AsyncClient, url: str, video_id: str) -> str:
    try:
        response = await client.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
        )
        response.raise_for_status()
        title = response.json().get("title")
        if title:
            return str(title)[:180]
    except httpx.HTTPError:
        pass
    return f"YouTube video {video_id}"


def select_caption_track(tracks: list[dict[str, str]]) -> Optional[dict[str, str]]:
    for language in YOUTUBE_LANG_PRIORITY:
        for track in tracks:
            if track.get("lang_code") == language:
                return track
    return tracks[0] if tracks else None


def parse_caption_tracks(xml_text: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(xml_text)
    tracks = []
    for track in root.findall("track"):
        tracks.append(
            {
                "lang_code": track.attrib.get("lang_code", ""),
                "name": track.attrib.get("name", ""),
                "kind": track.attrib.get("kind", ""),
            }
        )
    return tracks


def parse_json3_transcript(payload: dict) -> str:
    parts = []
    for event in payload.get("events", []):
        for segment in event.get("segs", []):
            text = segment.get("utf8", "").replace("\n", " ").strip()
            if text:
                parts.append(text)
    return " ".join(" ".join(parts).split())


async def fetch_youtube_transcript(client: httpx.AsyncClient, video_id: str, max_chars: int) -> str:
    list_response = await client.get(
        "https://www.youtube.com/api/timedtext",
        params={"type": "list", "v": video_id},
    )
    list_response.raise_for_status()
    track = select_caption_track(parse_caption_tracks(list_response.text))
    if not track:
        return ""

    params = {"fmt": "json3", "v": video_id, "lang": track["lang_code"]}
    if track["name"]:
        params["name"] = track["name"]
    if track["kind"]:
        params["kind"] = track["kind"]

    transcript_response = await client.get("https://www.youtube.com/api/timedtext", params=params)
    transcript_response.raise_for_status()
    return parse_json3_transcript(transcript_response.json())[:max_chars]


async def fetch_youtube_content(settings: Settings, url: str, video_id: str) -> tuple[str, str]:
    headers = {
        "User-Agent": "PersonalKMLineBot/0.1 (+https://github.com/dannytsao/PersonalKM)"
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=settings.request_timeout_seconds,
        headers=headers,
    ) as client:
        title = await fetch_youtube_metadata(client, url, video_id)
        try:
            transcript = await fetch_youtube_transcript(client, video_id, settings.max_page_chars)
        except (ElementTree.ParseError, httpx.HTTPError, json.JSONDecodeError):
            transcript = ""

    if transcript:
        return title, f"YouTube 影片逐字稿：{transcript}"
    return title, "無法擷取該 YouTube 影片的字幕或逐字稿。建議直接點擊連結觀看影片以獲取詳細資訊。"


def fallback_category(title: str, page_text: str) -> str:
    corpus = f"{title} {page_text}".lower()
    if any(keyword in corpus for keyword in ["camera", "photo", "photography", "景點", "拍照", "攝影", "相機"]):
        return "photography"
    if any(keyword in corpus for keyword in ["restaurant", "food", "cafe", "美食", "餐廳", "咖啡", "料理"]):
        return "food"
    if any(keyword in corpus for keyword in ["python", "javascript", "ai", "github", "api", "技術", "程式", "開發"]):
        return "tech"
    return "general"


def fallback_summary(title: str, page_text: str) -> str:
    text = page_text.strip()
    if not text:
        return f"此連結標題為「{title}」。目前無法擷取足夠內文，建議稍後人工補充摘要。"
    clipped = text[:220].rstrip()
    return f"此連結標題為「{title}」。擷取到的內容重點包含：{clipped}"


async def summarize_with_llm(settings: Settings, title: str, url: str, page_text: str) -> tuple[str, str]:
    if not settings.openai_api_key:
        return fallback_summary(title, page_text), fallback_category(title, page_text)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = {
        "title": title,
        "url": url,
        "content": page_text,
        "allowed_categories": sorted(CATEGORY_VALUES),
    }
    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "你是個人知識管理助理。請用繁體中文輸出 JSON，欄位為 "
                    "summary 與 category。summary 為 2-3 句摘要；category 只能是 "
                    "photography, food, tech, general。"
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    summary = str(data.get("summary") or fallback_summary(title, page_text)).strip()
    category = str(data.get("category") or "general").strip()
    if category not in CATEGORY_VALUES:
        category = "general"
    return summary, category


async def process_url(settings: Settings, url: str) -> LinkNote:
    video_id = youtube_video_id(url)
    if video_id:
        title, page_text = await fetch_youtube_content(settings, url, video_id)
        summary, category = await summarize_with_llm(settings, title, url, page_text)
        return LinkNote(
            title=title,
            url=url,
            summary=summary,
            category=category,
            captured_on=date.today(),
        )

    instagram_type = instagram_content_type(url)
    if instagram_type:
        try:
            title, page_text = await fetch_page(url, settings.request_timeout_seconds, settings.max_page_chars)
            if is_instagram_shell_text(page_text):
                title, page_text = instagram_fallback_content(instagram_type)
        except httpx.HTTPError:
            title, page_text = instagram_fallback_content(instagram_type)

        summary, category = await summarize_with_llm(settings, title, url, page_text)
        return LinkNote(
            title=title,
            url=url,
            summary=summary,
            category=category,
            captured_on=date.today(),
        )

    try:
        title, page_text = await fetch_page(url, settings.request_timeout_seconds, settings.max_page_chars)
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        domain = urlparse(url).netloc or url
        title = domain
        page_text = (
            f"無法擷取網頁內容，網站回傳 HTTP {status_code}。"
            "這通常代表網站拒絕自動化擷取，請直接開啟原文連結查看。"
        )
    except httpx.HTTPError as error:
        domain = urlparse(url).netloc or url
        title = domain
        page_text = f"無法擷取網頁內容：{error.__class__.__name__}。請直接開啟原文連結查看。"

    summary, category = await summarize_with_llm(settings, title, url, page_text)
    return LinkNote(
        title=title,
        url=url,
        summary=summary,
        category=category,
        captured_on=date.today(),
    )
