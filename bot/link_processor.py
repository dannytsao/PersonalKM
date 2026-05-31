import json
from datetime import date

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from bot.config import Settings
from bot.notes import LinkNote


CATEGORY_VALUES = {"photography", "food", "tech", "general"}


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
    title, page_text = await fetch_page(url, settings.request_timeout_seconds, settings.max_page_chars)
    summary, category = await summarize_with_llm(settings, title, url, page_text)
    return LinkNote(
        title=title,
        url=url,
        summary=summary,
        category=category,
        captured_on=date.today(),
    )
