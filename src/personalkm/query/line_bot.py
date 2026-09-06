#!/usr/bin/env python3
"""
AskDanny — PersonalKM LINE Query Bot
=====================================
親戚朋友透過 LINE 用自然語言查詢知識庫。Bot 回傳 LLM 合成答案 +
來源頁面標題。**永不暴露原始 MD 檔案**：回應只含答案文字與來源名稱，
不含任何檔案路徑、frontmatter 或原始內容全文。

優先查詢結構化 registry；無法用結構化條件命中時，才查詢兩個補充頁面。

架構:
    LINE → LINE Platform → Render (uvicorn)
                            ├─ registry 先依地區／類型篩選
                            ├─ 未命中結構化條件才讀取補充頁面
                            ├─ build_llm_context → route("query_answer")
                            └─ reply → LINE

環境變數:
    ASKDANNY_CHANNEL_SECRET       LINE Messaging API channel secret (必填)
    ASKDANNY_CHANNEL_ACCESS_TOKEN LINE Messaging API access token (必填)
    ASKDANNY_ALLOWED_USERS        逗號分隔 LINE userId 白名單；空 = 全開放
    ASKDANNY_LIFESTYLE_VAULT      lifestyle vault 路徑
    ASKDANNY_HELP_TEXT            自訂 help 訊息（選填）

執行（Render）:
    bash scripts/start_askdanny_render.sh
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from personalkm.capture.line import verify_line_signature
from personalkm.llm.router import route

app = FastAPI(title="AskDanny — PersonalKM LINE Query Bot")
logger = logging.getLogger(__name__)

DEFAULT_LIFESTYLE_VAULT = Path("~/Documents/PersonalKM/Personalkm-lifestyle-vault").expanduser()

GENERIC_DENY_TEXT = (
    "不好意思，這個機器人目前只開放給特定親友使用 🙏\n"
    "如果你認識 Danny，請直接跟他說一聲。"
)
DEFAULT_HELP_TEXT = (
    "嗨！我是 AskDanny 🤖 你可以用自然語言問我 Danny 的知識庫（美食、旅遊、攝影），例如：\n"
    "・「天母有什麼好吃的？」\n"
    "・「三芝海邊咖啡廳推薦」\n"
    "・「陽明山步道」\n\n"
    "我會根據 Danny 的筆記回答，並標注來源。"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff\-_]+")

# ── Only these two pages are queryable ────────────────────────────────────

ALLOWED_PAGES = [
    "wiki/concepts/city-subject-store.md",
    "wiki/concepts/tianmu-food.md",
]

REGISTRY_SOURCE_TITLE = "城市 × 主題 × 店家彙整"
SUBJECT_ALIASES = {
    "早午餐": ("早午餐", "brunch"),
    "住宿": ("住宿", "旅館", "民宿", "飯店", "酒店", "lodging"),
    "咖啡廳": ("咖啡廳", "咖啡館", "咖啡店", "cafe", "coffee"),
    "餐廳": ("餐廳", "restaurant"),
}
REASONING_BLOCK_RE = re.compile(
    r"<(?:think|analysis)>.*?</(?:think|analysis)>", re.IGNORECASE | re.DOTALL
)
REASONING_TAG_RE = re.compile(r"</?(?:think|analysis)\b", re.IGNORECASE)
INTERNAL_MARKERS = (
    "我先檢視",
    "接下來搜尋",
    "接下來需要確認",
    "我發現",
    "tool_calls",
    "function_call",
)


# ── Event model ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AskDannyEvent:
    reply_token: str
    user_id: str
    text: str


@dataclass(frozen=True)
class RegistryEntry:
    city: str
    subject: str
    store: str
    source: str
    address: str
    highlights: tuple[str, ...]
    rating: float | None
    rating_count: int | None
    status: str


def askdanny_events_from_webhook(payload: dict) -> list[AskDannyEvent]:
    events: list[AskDannyEvent] = []
    for event in payload.get("events", []):
        message = event.get("message", {})
        if event.get("type") == "message" and message.get("type") == "text":
            reply_token = event.get("replyToken", "")
            user_id = event.get("source", {}).get("userId", "")
            text = message.get("text", "")
            if reply_token and text:
                events.append(AskDannyEvent(reply_token=reply_token, user_id=user_id, text=text))
    return events


# ── Config helpers ─────────────────────────────────────────────────────────

def askdanny_settings() -> dict:
    return {
        "channel_secret": os.getenv("ASKDANNY_CHANNEL_SECRET", ""),
        "access_token": os.getenv("ASKDANNY_CHANNEL_ACCESS_TOKEN", ""),
        "allowed_users": {
            uid.strip()
            for uid in os.getenv("ASKDANNY_ALLOWED_USERS", "").split(",")
            if uid.strip()
        },
        "lifestyle_vault": Path(os.getenv("ASKDANNY_LIFESTYLE_VAULT", DEFAULT_LIFESTYLE_VAULT)).expanduser(),
        "help_text": os.getenv("ASKDANNY_HELP_TEXT", DEFAULT_HELP_TEXT),
    }


def vault_root(cfg: dict) -> Optional[Path]:
    root = cfg["lifestyle_vault"]
    if root.exists():
        return root
    logger.warning("Lifestyle vault path %s does not exist", root)
    return None


# ── LINE reply API ─────────────────────────────────────────────────────────

async def reply_message(access_token: str, reply_token: str, text: str) -> bool:
    if not access_token or not reply_token:
        return False
    if len(text) > 4800:
        cut = text.rfind("\n", 0, 4800)
        text = text[: cut if cut > 0 else 4800] + "\n…（已截斷）"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/reply",
                headers=headers,
                json=payload,
            )
            if response.status_code >= 400:
                logger.error("LINE reply failed: %s %s", response.status_code, response.text[:300])
                return False
            return True
    except Exception:
        logger.exception("LINE reply request failed")
        return False


# ── Read + search the 2 allowed pages ─────────────────────────────────────

def _read_page(wiki_root: Path, rel_path: str) -> Optional[dict]:
    """Read a wiki page, parse frontmatter, return {'title', 'body', 'slug'}."""
    fpath = wiki_root.parent / rel_path
    if not fpath.exists():
        return None
    try:
        content = fpath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    title = ""
    body = content
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            fm_block = content[3:end]
            body = content[end + 3:].strip()
            for line in fm_block.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    if k.strip() == "title":
                        title = v.strip().strip("\"'")
    slug = fpath.stem
    if not title:
        title = slug
    return {"title": title, "slug": slug, "body": body, "rel_path": rel_path}


def _load_registry_entries(root: Path) -> list[RegistryEntry]:
    registry_path = root / "wiki" / "_registry" / "city-subject-store.json"
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Lifestyle registry unavailable at %s", registry_path)
        return []

    raw_entries = payload.get("entries", []) if isinstance(payload, dict) else []
    if not isinstance(raw_entries, list):
        return []

    entries: list[RegistryEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict) or raw.get("status") == "removed":
            continue
        highlights = raw.get("highlights", [])
        rating = raw.get("rating")
        rating_count = raw.get("rating_count")
        entries.append(
            RegistryEntry(
                city=str(raw.get("city", "")).strip(),
                subject=str(raw.get("subject", "")).strip(),
                store=str(raw.get("store", "")).strip(),
                source=str(raw.get("source", "")).strip(),
                address=str(raw.get("address", "")).strip(),
                highlights=tuple(
                    item.strip() for item in highlights if isinstance(item, str) and item.strip()
                )
                if isinstance(highlights, list)
                else (),
                rating=float(rating) if isinstance(rating, (int, float)) else None,
                rating_count=int(rating_count) if isinstance(rating_count, int) else None,
                status=str(raw.get("status", "")).strip(),
            )
        )
    return entries


def _query_subject(query: str) -> str | None:
    query_lower = query.lower()
    for subject, aliases in SUBJECT_ALIASES.items():
        if any(alias.lower() in query_lower for alias in aliases):
            return subject
    return None


def _entry_matches_location(query: str, entry: RegistryEntry) -> bool:
    query_lower = query.lower()
    city = entry.city.lower()
    if city and (city in query_lower or city.removesuffix("市") in query_lower):
        return True
    districts = re.findall(r"(?:市|縣)([\u4e00-\u9fff]{2,4})(區|鄉|鎮)", entry.address)
    for district, suffix in districts:
        full_name = f"{district}{suffix}".lower()
        if full_name in query_lower or district.lower() in query_lower:
            return True
    return False


def _registry_matches(query: str, entries: list[RegistryEntry]) -> list[RegistryEntry] | None:
    subject = _query_subject(query)
    if subject is None:
        return None
    if not any(_entry_matches_location(query, entry) for entry in entries):
        return None
    matches = [
        entry
        for entry in entries
        if entry.subject == subject and _entry_matches_location(query, entry)
    ]
    return sorted(matches, key=lambda entry: (-(entry.rating or 0), entry.store))


def _render_registry_answer(entries: list[RegistryEntry]) -> str:
    lines = [f"目前整理到 {len(entries)} 筆符合條件的資料："]
    for entry in entries[:5]:
        lines.append(f"\n- {entry.store}")
        if entry.address:
            lines.append(f"  地址：{entry.address}")
        if entry.rating is not None:
            rating_text = f"{entry.rating:g}"
            if entry.rating_count is not None:
                rating_text += f"（{entry.rating_count} 則）"
            lines.append(f"  評分：{rating_text}")
        if entry.highlights:
            lines.append(f"  特色：{'；'.join(entry.highlights[:3])}")
    return "\n".join(lines)


def _safe_llm_answer(answer: str) -> str | None:
    cleaned = REASONING_BLOCK_RE.sub("", answer).strip()
    if not cleaned or REASONING_TAG_RE.search(cleaned):
        return None
    if any(marker in cleaned for marker in INTERNAL_MARKERS):
        return None
    return cleaned


def _score_page(query_tokens: set[str], page: dict) -> int:
    """Simple keyword match score: 5 for title hit, 2 per keyword in body."""
    haystack = f"{page['title']}\n{page['body']}".lower()
    score = 0
    for token in query_tokens:
        if len(token) > 1 and token in haystack:
            score += 2
    if any(t in page["title"].lower() for t in query_tokens if len(t) > 1):
        score += 5
    return score


def _summary_excerpt(body: str, max_chars: int = 300) -> str:
    """Extract first meaningful paragraph as summary."""
    m = re.search(r"## Summary\s*\n\n(.+?)(?:\n\n|$)", body, re.DOTALL)
    if m:
        return m.group(1).strip()[:max_chars]
    for p in re.split(r"\n\n+", body):
        p = p.strip()
        if p and not p.startswith("#") and len(p) > 30:
            return p[:max_chars]
    return body[:max_chars]


def _build_context(pages: list[dict], max_chars: int = 16000) -> str:
    """Build context string for LLM: title + body of each page."""
    chunks = []
    total = 0
    for p in pages:
        entry = f"## {p['title']}\n{p['body']}\n\n"
        if total + len(entry) > max_chars:
            # Flat character truncation — no "---" boundary logic because
            # the registry page uses "---" as horizontal rules AND table
            # separators (|---|---|), so rfind("---") would find the
            # early table separator and cut off ALL data rows.
            entry = entry[:max_chars - total]
        chunks.append(entry)
        total += len(entry)
    return "".join(chunks)


def _query_all(query: str, root: Path) -> dict:
    """Search allowed pages, run ONE LLM synthesis. Returns {answer, sources, error}."""
    registry_matches = _registry_matches(query, _load_registry_entries(root))
    if registry_matches is not None:
        if not registry_matches:
            return {"answer": None, "sources": [], "error": "no_match"}
        return {
            "answer": _render_registry_answer(registry_matches),
            "sources": [REGISTRY_SOURCE_TITLE],
            "error": None,
        }

    wiki_root = root / "wiki"
    query_lower = query.lower().strip()
    query_tokens = set(TOKEN_RE.findall(query_lower))

    pages = []
    for rel in ALLOWED_PAGES:
        page = _read_page(wiki_root, rel)
        if page:
            pages.append(page)

    if not pages:
        return {"answer": None, "sources": [], "error": "no_match"}

    scored = []
    for p in pages:
        s = _score_page(query_tokens, p)
        scored.append((s, p))
    scored.sort(key=lambda x: -x[0])

    relevant_pages = [p for score, p in scored if score > 0]
    if not relevant_pages:
        relevant_pages = [scored[0][1]]
    context = _build_context(relevant_pages, max_chars=12000)
    source_titles = [p["title"] for p in relevant_pages]

    prompt = (
            "你是一個個人知識庫助手。根據以下 Danny 的筆記回答問題。"
            "如果上下文資訊不足，請誠實說不知道。回答時用[[wikilink]]標註來源。"
            "注意：回覆是傳給 LINE 純文字訊息，不要使用表格、不要使用 @url: 連結、不要使用 markdown 格式。"
            "用簡單的條列式（- 項目）和文字描述即可。"
            "重要：以下包含一個全區域的店家彙整表 (registry) 和一個北海岸主題彙整頁。"
            "registry 裡有完整的地址資料，優先依 registry 的店家資訊回答。"
            "如果主題頁提到某區域的清單「未收錄於本頁」，那只是該頁面的限制，不代表 registry 也沒有。"
            "\n\n上下文（按相關性排序）：\n"
            f"{context}\n\n"
            f"問題：{query}\n\n"
            "回答（用[[wikilink]]標註來源，純文字條列式）："
        )

    try:
        completion = route("query_answer", prompt)
        answer_text = _safe_llm_answer(completion.text)
        if answer_text is None:
            return {
                "answer": "抱歉，我目前無法把這筆資料整理成可靠的簡短回答，請換個問法。",
                "sources": source_titles,
                "error": "unsafe_llm_output",
            }
        answer_text = WIKILINK_RE.sub(r"\1", answer_text)
        # Strip any @url: references (safety net for LLM-generated links)
        answer_text = re.sub(r"@url:`[^`]+`", "", answer_text)
        answer_text = re.sub(r"https?://\S+", "", answer_text)
    except Exception:
        logger.exception("LLM synthesis failed")
        return {
            "answer": "抱歉，我暫時無法回答 🤖 可能是知識庫或模型暫時出狀況，請晚點再試。",
            "sources": source_titles,
            "error": "llm_failed",
        }

    return {"answer": answer_text, "sources": source_titles, "error": None}


# ── Webhook handler ────────────────────────────────────────────────────────

def is_allowed(cfg: dict, user_id: str) -> bool:
    if not cfg["allowed_users"]:
        return True
    return user_id in cfg["allowed_users"]


async def handle_text_event(cfg: dict, event: AskDannyEvent) -> None:
    if not is_allowed(cfg, event.user_id):
        await reply_message(cfg["access_token"], event.reply_token, GENERIC_DENY_TEXT)
        return

    text = event.text.strip()
    logger.info("AskDanny query from %s: %r", event.user_id[:8] or "?", text[:80])

    if text.lower() in ("/help", "help", "說明", "怎麼用"):
        await reply_message(cfg["access_token"], event.reply_token, cfg["help_text"])
        return

    root = vault_root(cfg)
    if not root:
        await reply_message(cfg["access_token"], event.reply_token, "知識庫目前沒有設定好，請通知 Danny。")
        return

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _query_all, text, root)

    if result.get("error") == "no_match":
        await reply_message(
            cfg["access_token"], event.reply_token,
            "目前 Danny 的 Lifestyle Vault 沒有整理到相關資料。\n可以換個問法，或問我 /help 看看我能回答什麼。",
        )
        return

    answer = (result.get("answer") or "").strip()
    sources = result.get("sources") or []
    lines = [answer]
    if sources:
        lines.append("\n📚 來源：" + "、".join(sources[:6]))
    await reply_message(cfg["access_token"], event.reply_token, "\n".join(lines))


@app.post("/webhook/line/askdanny")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: Optional[str] = Header(default=None),
) -> dict:
    cfg = askdanny_settings()
    if not cfg["channel_secret"] or not cfg["access_token"]:
        logger.error("ASKDANNY_CHANNEL_SECRET / ASKDANNY_CHANNEL_ACCESS_TOKEN not set")
        raise HTTPException(status_code=500, detail="AskDanny not configured")

    body = await request.body()
    if not verify_line_signature(body, cfg["channel_secret"], x_line_signature):
        logger.warning("Rejected AskDanny webhook with invalid signature")
        raise HTTPException(status_code=401, detail="Invalid LINE signature")

    payload = await request.json()
    events = askdanny_events_from_webhook(payload)
    if not events:
        return {"ok": True, "accepted": 0}

    for event in events:
        background_tasks.add_task(handle_text_event, cfg, event)
    logger.info("Accepted %s AskDanny message(s)", len(events))
    return {"ok": True, "accepted": len(events)}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "bot": "askdanny"}
