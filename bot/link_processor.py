import json
from dataclasses import dataclass
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
RESTRICTED_PLATFORM_HOSTS = {
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
    "m.instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "www.tiktok.com": "tiktok",
    "vm.tiktok.com": "tiktok",
    "x.com": "x",
    "www.x.com": "x",
    "twitter.com": "x",
    "www.twitter.com": "x",
    "threads.net": "threads",
    "www.threads.net": "threads",
}


@dataclass(frozen=True)
class ExtractedContent:
    title: str
    text: str
    platform: str = "web"
    extraction_status: str = "ok"
    needs_review: bool = False


async def fetch_page(url: str, timeout_seconds: float, max_chars: int) -> ExtractedContent:
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
    metadata = extract_page_metadata(soup)
    content_text = metadata_text(metadata) or text
    return ExtractedContent(
        title=(metadata.get("title") or title)[:180],
        text=content_text[:max_chars],
        platform=platform_from_url(url),
    )


def platform_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host in RESTRICTED_PLATFORM_HOSTS:
        return RESTRICTED_PLATFORM_HOSTS[host]
    if host in YOUTUBE_HOSTS:
        return "youtube"
    return "web"


def extract_page_metadata(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        content = tag.get("content")
        if key and content:
            metadata[key.lower()] = " ".join(content.split())

    title = metadata.get("og:title") or metadata.get("twitter:title")
    description = (
        metadata.get("og:description")
        or metadata.get("twitter:description")
        or metadata.get("description")
    )
    result = {}
    if title:
        result["title"] = title
    if description:
        result["description"] = description
    return result


def metadata_text(metadata: dict[str, str]) -> str:
    parts = [metadata.get("title", ""), metadata.get("description", "")]
    return " ".join(part for part in parts if part).strip()


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


def blocked_platform_content(platform: str, content_label: str) -> ExtractedContent:
    return ExtractedContent(
        title=content_label,
        text=(
            f"這是一個 {content_label} 連結。{platform} 通常需要登入或會阻擋自動化擷取，"
            "目前無法可靠取得貼文或影片內容。請直接開啟原文連結查看。"
        ),
        platform=platform,
        extraction_status="blocked",
        needs_review=True,
    )


def instagram_fallback_content(content_type: str) -> ExtractedContent:
    label = "Instagram Reel" if content_type in {"reel", "reels"} else "Instagram post"
    return blocked_platform_content("instagram", label)


def restricted_platform_fallback(url: str) -> ExtractedContent:
    platform = platform_from_url(url)
    labels = {
        "tiktok": "TikTok video",
        "x": "X/Twitter post",
        "threads": "Threads post",
    }
    return blocked_platform_content(platform, labels.get(platform, f"{platform} link"))


def is_restricted_platform(url: str) -> bool:
    return platform_from_url(url) in {"instagram", "tiktok", "x", "threads"}


def is_restricted_shell_text(platform: str, text: str) -> bool:
    lowered = text.lower()
    if platform == "instagram":
        return is_instagram_shell_text(text)

    markers = {
        "tiktok": ["log in", "sign up", "tiktok"],
        "x": ["log in", "sign up", "x.com", "twitter"],
        "threads": ["log in", "threads", "instagram"],
    }
    platform_markers = markers.get(platform, [])
    return bool(platform_markers) and sum(marker in lowered for marker in platform_markers) >= 2


def to_note(content: ExtractedContent, url: str, summary: str, category: str) -> LinkNote:
    return LinkNote(
        title=content.title,
        url=url,
        summary=summary,
        category=category,
        captured_on=date.today(),
        platform=content.platform,
        extraction_status=content.extraction_status,
        needs_review=content.needs_review,
    )


def http_error_content(url: str, error: httpx.HTTPStatusError) -> ExtractedContent:
    status_code = error.response.status_code
    domain = urlparse(url).netloc or url
    platform = platform_from_url(url)
    return ExtractedContent(
        title=domain,
        text=(
            f"無法擷取網頁內容，網站回傳 HTTP {status_code}。"
            "這通常代表網站拒絕自動化擷取，請直接開啟原文連結查看。"
        ),
        platform=platform,
        extraction_status="blocked" if platform != "web" else "error",
        needs_review=platform != "web",
    )


def generic_http_error_content(url: str, error: httpx.HTTPError) -> ExtractedContent:
    domain = urlparse(url).netloc or url
    platform = platform_from_url(url)
    return ExtractedContent(
        title=domain,
        text=f"無法擷取網頁內容：{error.__class__.__name__}。請直接開啟原文連結查看。",
        platform=platform,
        extraction_status="blocked" if platform != "web" else "error",
        needs_review=platform != "web",
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


async def fetch_youtube_content(settings: Settings, url: str, video_id: str) -> ExtractedContent:
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
        return ExtractedContent(
            title=title,
            text=f"YouTube 影片逐字稿：{transcript}",
            platform="youtube",
        )
    return ExtractedContent(
        title=title,
        text="無法擷取該 YouTube 影片的字幕或逐字稿。建議直接點擊連結觀看影片以獲取詳細資訊。",
        platform="youtube",
        extraction_status="partial",
        needs_review=True,
    )


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
        content = await fetch_youtube_content(settings, url, video_id)
        summary, category = await summarize_with_llm(settings, content.title, url, content.text)
        return to_note(content, url, summary, category)

    instagram_type = instagram_content_type(url)
    if instagram_type:
        try:
            content = await fetch_page(url, settings.request_timeout_seconds, settings.max_page_chars)
            if is_instagram_shell_text(content.text):
                content = instagram_fallback_content(instagram_type)
        except httpx.HTTPError:
            content = instagram_fallback_content(instagram_type)

        summary, category = await summarize_with_llm(settings, content.title, url, content.text)
        return to_note(content, url, summary, category)

    if is_restricted_platform(url):
        try:
            content = await fetch_page(url, settings.request_timeout_seconds, settings.max_page_chars)
            if is_restricted_shell_text(content.platform, content.text):
                content = restricted_platform_fallback(url)
        except httpx.HTTPError:
            content = restricted_platform_fallback(url)

        summary, category = await summarize_with_llm(settings, content.title, url, content.text)
        return to_note(content, url, summary, category)

    try:
        content = await fetch_page(url, settings.request_timeout_seconds, settings.max_page_chars)
    except httpx.HTTPStatusError as error:
        content = http_error_content(url, error)
    except httpx.HTTPError as error:
        content = generic_http_error_content(url, error)

    summary, category = await summarize_with_llm(settings, content.title, url, content.text)
    return to_note(content, url, summary, category)
