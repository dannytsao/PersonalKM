#!/usr/bin/env python3
"""
AskDanny — PersonalKM LINE Query Bot
=====================================
親戚朋友透過 LINE 用自然語言查詢知識庫。Bot 回傳 LLM 合成答案 +
來源頁面標題。**永不暴露原始 MD 檔案**：回應只含答案文字與來源名稱，
不含任何檔案路徑、frontmatter 或原始內容全文。

架構（只查 lifestyle vault）:
    LINE → LINE Platform → Render (uvicorn)
                            ├─ search_vault (lifestyle wiki only)
                            ├─ build_llm_context → route("query_answer")
                            └─ reply → LINE

環境變數:
    ASKDANNY_CHANNEL_SECRET       LINE Messaging API channel secret (必填)
    ASKDANNY_CHANNEL_ACCESS_TOKEN LINE Messaging API access token (必填)
    ASKDANNY_ALLOWED_USERS        逗號分隔 LINE userId 白名單；空 = 全開放
    ASKDANNY_LIFESTYLE_VAULT      lifestyle vault 路徑（預設 ~/Documents/PersonalKM/Personalkm-lifestyle-vault）
    ASKDANNY_HELP_TEXT            自訂 help 訊息（選填）

執行（Render）:
    bash scripts/start_askdanny_render.sh
"""
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from personalkm.capture.line import verify_line_signature
from personalkm.query.query_engine import (
    answer_with_llm,
    build_llm_context,
)

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


# ── Event model ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AskDannyEvent:
    reply_token: str
    user_id: str
    text: str


def askdanny_events_from_webhook(payload: dict) -> list[AskDannyEvent]:
    """Extract text-message events WITH replyToken (capture.line lacks it)."""
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
    """AskDanny-specific settings, resolved from env with sane defaults."""
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


def vault_roots(cfg: dict) -> list[Path]:
    """Return the lifestyle vault root if it exists."""
    path = cfg["lifestyle_vault"]
    if path.exists():
        return [path]
    logger.warning("Lifestyle vault path %s does not exist", path)
    return []


# ── LINE reply API ─────────────────────────────────────────────────────────

async def reply_message(access_token: str, reply_token: str, text: str) -> bool:
    """Send a text reply via LINE Messaging API reply endpoint."""
    if not access_token or not reply_token:
        return False
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    # LINE text message limit is 5000 chars — trim safely at a line boundary.
    if len(text) > 4800:
        cut = text.rfind("\n", 0, 4800)
        text = text[: cut if cut > 0 else 4800] + "\n…（已截斷）"
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/reply",
                headers=headers,
                json=payload,
            )
            if response.status_code >= 400:
                logger.error(
                    "LINE reply failed: %s %s",
                    response.status_code,
                    response.text[:300],
                )
                return False
            return True
    except Exception:
        logger.exception("LINE reply request failed")
        return False


# ── Query pipeline (combined across vaults) ───────────────────────────────

ALLOWED_PAGES = [
    "wiki/concepts/city-subject-store.md",
    "wiki/concepts/tianmu-food.md",
]


def query_all_vaults(query: str, roots: list[Path], top_k: int = 6) -> dict:
    """
    Search only ALLOWED_PAGES within the lifestyle vault, run LLM synthesis.

    Returns dict with keys: answer, sources (list of titles), error.
    Uses query_engine's existing pieces — never exposes raw file paths.
    """
    query_lower = query.lower().strip()

    all_results = []
    for root in roots:
        wiki_path = root / "wiki"
        for rel_path_str in ALLOWED_PAGES:
            fpath = wiki_path.parent / rel_path_str
            if not fpath.exists():
                logger.warning("Allowed page not found: %s", fpath)
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Simple keyword scoring against the page content
            title = ""
            frontmatter_end = content.find("---", 3)
            body = content
            if content.startswith("---") and frontmatter_end > 0:
                fm_block = content[3:frontmatter_end]
                body = content[frontmatter_end + 3:].strip()
                for line in fm_block.strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        if key.strip() == "title":
                            title = val.strip().strip("\"'")

            slug = fpath.stem
            if not title:
                title = slug

            haystack = f"{title}\n{body}".lower()
            score = 0.0
            tokens = set(re.findall(r"[a-z0-9\u4e00-\u9fff\-_]+", query_lower))
            for token in tokens:
                if len(token) > 1 and token in haystack:
                    score += 2
            if any(t in title.lower() for t in tokens if len(t) > 1):
                score += 5

            if score > 0:
                # Extract summary excerpt
                summary_excerpt = ""
                summary_match = re.search(
                    r"## Summary\s*\n\n(.+?)(?:\n\n|$)", body, re.DOTALL
                )
                if summary_match:
                    summary_excerpt = summary_match.group(1).strip()[:300]
                if not summary_excerpt:
                    paras = [p.strip() for p in re.split(r"\n\n+", body)
                             if p.strip() and not p.strip().startswith("#")]
                    for p in paras:
                        if len(p) > 30:
                            summary_excerpt = p[:300]
                            break

                all_results.append({
                    "page": rel_path_str,
                    "slug": slug,
                    "title": title,
                    "source_kind": "wiki",
                    "type": "concept",
                    "topic": "",
                    "tags": "",
                    "confidence": "medium",
                    "score": score,
                    "match_reason": "keyword_match",
                    "sources": "",
                    "summary_excerpt": summary_excerpt,
                    "url": "",
                    "_body": body,
                })
            else:
                # Still include unscored pages so user can ask about them
                # even if query has no keyword overlap.
                all_results.append({
                    "page": rel_path_str,
                    "slug": slug,
                    "title": title,
                    "source_kind": "wiki",
                    "type": "concept",
                    "topic": "",
                    "tags": "",
                    "confidence": "medium",
                    "score": 0,
                    "match_reason": "no_match",
                    "sources": "",
                    "summary_excerpt": "",
                    "url": "",
                    "_body": body,
                })

    if not all_results:
        return {"answer": None, "sources": [], "error": "no_match"}

    all_results.sort(key=lambda r: -r["score"])
    all_results = all_results[:top_k]
    context = build_llm_context(all_results, max_chars=5000)

    source_titles = []
    for r in all_results:
        title = (r.get("title") or "").strip()
        if title and title not in source_titles:
            source_titles.append(title)

    try:
        result = answer_with_llm(query, context, roots[0] / "wiki")
    except Exception:
        logger.exception("LLM synthesis failed")
        return {
            "answer": "抱歉，我暫時無法回答 🤖 可能是知識庫或模型暫時出狀況，請晚點再試。",
            "sources": source_titles,
            "error": "llm_failed",
        }

    return {"answer": result.get("answer", ""), "sources": source_titles, "error": None}


def format_reply(query: str, result: dict) -> str:
    """Build the LINE-facing text: cleaned answer + cited source titles."""
    answer = result.get("answer") or ""
    # Strip internal wiki syntax so [[x|y]] and [[slug]] become plain text.
    answer = WIKILINK_RE.sub(r"\1", answer)
    answer = answer.strip()

    sources = result.get("sources") or []
    lines = [answer]
    if sources:
        lines.append("\n📚 來源：" + "、".join(sources[:6]))
    return "\n".join(lines)


# ── Webhook handler ────────────────────────────────────────────────────────

def is_allowed(cfg: dict, user_id: str) -> bool:
    """Whitelist gate. Empty allowed set = fully open (先建 bot，白名單最後處理)."""
    if not cfg["allowed_users"]:
        return True
    return user_id in cfg["allowed_users"]


async def handle_text_event(cfg: dict, event: AskDannyEvent) -> None:
    """Process one text message: whitelist gate → query → reply."""
    if not is_allowed(cfg, event.user_id):
        await reply_message(cfg["access_token"], event.reply_token, GENERIC_DENY_TEXT)
        return

    text = event.text.strip()
    logger.info("AskDanny query from %s: %r", event.user_id[:8] or "?", text[:80])

    if text.lower() in ("/help", "help", "說明", "怎麼用"):
        await reply_message(cfg["access_token"], event.reply_token, cfg["help_text"])
        return

    roots = vault_roots(cfg)
    if not roots:
        await reply_message(
            cfg["access_token"],
            event.reply_token,
            "知識庫目前沒有設定好（找不到 vault 資料夾），請通知 Danny。",
        )
        return

    # Run the query in a thread so the event loop stays free.
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, query_all_vaults, text, roots)

    if result.get("error") == "no_match":
        await reply_message(
            cfg["access_token"],
            event.reply_token,
            "我查了一下知識庫，好像沒有找到相關的資料 🤔\n"
            "可以換個問法，或問我 /help 看看我能回答什麼。",
        )
        return

    reply_text = format_reply(text, result)
    await reply_message(cfg["access_token"], event.reply_token, reply_text)


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