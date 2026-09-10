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
    ASKDANNY_GOOGLE_CLIENT_ID     Google OAuth client ID（選填）
    ASKDANNY_GOOGLE_CLIENT_SECRET Google OAuth client secret（選填）
    ASKDANNY_GOOGLE_REDIRECT_URI  Google OAuth callback URL（選填）

執行（Render）:
    bash scripts/start_askdanny_render.sh
"""
from __future__ import annotations

import asyncio
from html import escape
import json
import logging
import os
import re
import secrets
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from personalkm.capture.line import verify_line_signature
from personalkm.llm.router import route
from personalkm.query.google_sheets import (
    export_to_google_sheet,
    google_authorization_url,
    google_oauth_config_from_env,
)
from personalkm.query.search_index import build_search_index, query_terms, search

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
    "美食": ("美食",),
    "早午餐": ("早午餐", "brunch"),
    "牛肉麵": ("牛肉麵", "牛肉面"),
    "拉麵": ("拉麵", "拉面", "ramen"),
    "住宿": ("住宿", "旅館", "民宿", "飯店", "酒店", "lodging"),
    "咖啡廳": ("咖啡廳", "咖啡館", "咖啡店", "cafe", "coffee"),
    "餐廳": ("餐廳", "restaurant"),
}
BROAD_SUBJECTS = {
    "美食": ("餐廳", "小吃", "早午餐", "咖啡廳", "甜點", "酒吧"),
    "牛肉麵": ("小吃", "餐廳"),
    "拉麵": ("小吃", "餐廳"),
}
SUBJECT_MATCH_TERMS = {
    "牛肉麵": ("牛肉麵", "牛肉面"),
    "拉麵": ("拉麵", "拉面", "ramen"),
}
QUERY_GENERIC_TERMS = (
    "有什麼", "什麼", "推薦", "好吃", "好吃的", "地區", "附近", "哪裡", "適合", "可以", "想找", "請問",
)
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
MORE_COMMAND_RE = re.compile(r"^(?:(?:再看|更多|看更多)\s*)?(\d{1,3})\s*(?:筆|列)?$")
TERMINATE_COMMANDS = frozenset(("2", "終止", "終止輸出", "停止輸出", "取消"))
EXPORT_COMMANDS = frozenset(("3", "匯出", "匯出到 Google Sheet", "匯出 Google Sheet"))
LOCATION_CONFIRM_YES = frozenset(("1", "是", "是的", "要", "包含", "包含這些地區", "好", "可以"))
LOCATION_CONFIRM_NO = frozenset(("2", "否", "不是", "不要", "不包含", "取消"))
SESSION_TTL_SECONDS = 1800


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
    gps: tuple[float, float] | None
    highlights: tuple[str, ...]
    rating: float | None
    rating_count: int | None
    status: str
    phone: str = ""
    reservation_url: str = ""
    google_maps_url: str = ""


@dataclass(frozen=True, slots=True)
class QuerySession:
    entries: tuple[RegistryEntry, ...]
    offset: int
    created_at: float = field(default_factory=time.monotonic)


@dataclass(frozen=True, slots=True)
class PendingGoogleExport:
    user_id: str
    entries: tuple[RegistryEntry, ...]
    created_at: float


@dataclass(frozen=True, slots=True)
class LocationIntent:
    subject: str
    scope: str
    locations: tuple[str, ...]
    needs_confirmation: bool


@dataclass(frozen=True, slots=True)
class PendingLocationConfirmation:
    user_id: str
    query: str
    intent: LocationIntent
    created_at: float


QUERY_SESSIONS: dict[str, QuerySession] = {}
PENDING_GOOGLE_EXPORTS: dict[str, PendingGoogleExport] = {}
PENDING_LOCATION_CONFIRMATIONS: dict[str, PendingLocationConfirmation] = {}


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


async def push_message(access_token: str, user_id: str, text: str) -> bool:
    if not access_token or not user_id:
        return False
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/push",
                headers=headers,
                json=payload,
            )
            if response.status_code >= 400:
                logger.error("LINE push failed: %s %s", response.status_code, response.text[:300])
                return False
            return True
    except Exception:
        logger.exception("LINE push request failed")
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
        phone = raw.get("phone")
        reservation_url = raw.get("reservation_url") or raw.get("booking_url")
        google_maps_url = raw.get("google_maps_url")
        highlights = raw.get("highlights", [])
        rating = raw.get("rating")
        rating_count = raw.get("rating_count")
        gps_raw = raw.get("gps")
        gps = (
            (float(gps_raw[0]), float(gps_raw[1]))
            if isinstance(gps_raw, list)
            and len(gps_raw) == 2
            and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in gps_raw)
            else None
        )
        entries.append(
            RegistryEntry(
                city=str(raw.get("city", "")).strip(),
                subject=str(raw.get("subject", "")).strip(),
                store=str(raw.get("store", "")).strip(),
                source=str(raw.get("source", "")).strip(),
                address=str(raw.get("address", "")).strip(),
                gps=gps,
                highlights=tuple(
                    item.strip() for item in highlights if isinstance(item, str) and item.strip()
                )
                if isinstance(highlights, list)
                else (),
                rating=float(rating) if isinstance(rating, (int, float)) else None,
                rating_count=int(rating_count) if isinstance(rating_count, int) else None,
                status=str(raw.get("status", "")).strip(),
                phone=phone.strip() if isinstance(phone, str) else "",
                reservation_url=(
                    reservation_url.strip() if isinstance(reservation_url, str) else ""
                ),
                google_maps_url=(
                    google_maps_url.strip() if isinstance(google_maps_url, str) else ""
                ),
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


def _entry_location_labels(entry: RegistryEntry) -> set[str]:
    labels = {entry.city} if entry.city else set()
    labels.update(
        f"{district}{suffix}"
        for district, suffix in re.findall(r"(?:市|縣)([\u4e00-\u9fff]{2,4})(區|鄉|鎮)", entry.address)
    )
    return labels


def _registry_location_labels(entries: list[RegistryEntry]) -> tuple[str, ...]:
    return tuple(sorted({label for entry in entries for label in _entry_location_labels(entry)}))


def _conservative_location_intent(
    query: str,
    subject: str,
    labels: tuple[str, ...],
    entries: list[RegistryEntry],
) -> LocationIntent | None:
    candidates = [
        label
        for label in labels
        if label in query or label.removesuffix("市") in query
        or label.removesuffix("區") in query
        or label.removesuffix("鄉") in query
        or label.removesuffix("鎮") in query
    ]
    query_term = query
    for alias in SUBJECT_ALIASES.get(subject, ()):
        query_term = query_term.replace(alias, "")
    query_term = re.sub(r"[\s，。？！?！、]+", "", query_term)
    if len(query_term) >= 2:
        for entry in entries:
            if entry.subject != subject or query_term not in f"{entry.store}{entry.address}":
                continue
            candidates.extend(_entry_location_labels(entry) - {entry.city})
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1:
        candidates = [label for label in labels if label in candidates]
    if not candidates:
        return None
    return LocationIntent(
        subject=subject,
        scope="exact" if len(candidates) == 1 else "regional",
        locations=tuple(candidates),
        needs_confirmation=True,
    )


def _registry_matches_for_locations(
    subject: str,
    locations: tuple[str, ...],
    entries: list[RegistryEntry],
) -> list[RegistryEntry]:
    allowed_subjects = BROAD_SUBJECTS.get(subject, (subject,))
    matches = [
        entry
        for entry in entries
        if entry.subject in allowed_subjects
        and _entry_matches_subject(subject, entry)
        and _entry_location_labels(entry).intersection(locations)
    ]
    return sorted(matches, key=lambda entry: (-(entry.rating or 0), entry.store))


def _indexed_registry_matches(
    query: str,
    entries: list[RegistryEntry],
    index: object,
) -> list[RegistryEntry]:
    subject = _query_subject(query)
    all_aliases = [alias for aliases in SUBJECT_ALIASES.values() for alias in aliases]
    ignored = [*QUERY_GENERIC_TERMS, *all_aliases]
    if subject in SUBJECT_MATCH_TERMS:
        ignored = [term for term in ignored if term not in SUBJECT_MATCH_TERMS[subject]]
    labels = _registry_location_labels(entries)
    ignored.extend(labels)
    ignored.extend(
        label.removesuffix(suffix)
        for label in labels
        for suffix in ("市", "縣", "區", "鄉", "鎮")
        if len(label.removesuffix(suffix)) >= 2
    )
    terms = query_terms(query, ignored=ignored)
    if not terms:
        return []
    allowed_subjects = BROAD_SUBJECTS.get(subject, (subject,)) if subject else None
    return search(
        index,
        terms,
        predicate=lambda entry: (
            _entry_matches_location(query, entry)
            and (allowed_subjects is None or entry.subject in allowed_subjects)
            and (subject is None or _entry_matches_subject(subject, entry))
        ),
    )


def _tianmu_food_matches(query: str, root: Path, entries: list[RegistryEntry]) -> list[RegistryEntry] | None:
    if "天母" not in query:
        return None
    subject = _query_subject(query)
    # Accept all food-related subjects (美食, 早午餐, 咖啡廳, 小吃, etc.)
    all_food_subjects = BROAD_SUBJECTS.get("美食", ()) + ("美食", "早午餐", "咖啡廳", "甜點", "酒吧", "小吃", "餐廳")
    if subject not in all_food_subjects:
        return None
    page_path = root / "wiki" / "concepts" / "tianmu-food.md"
    try:
        body = page_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    section = re.search(r"## 天母[^\n]*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if section is None:
        return None
    stores = {
        match.group(1).strip().removesuffix(" 👤")
        for match in re.finditer(r"^\|\s*[^|]+\|\s*([^|]+)\|", section.group(1), re.MULTILINE)
    }
    stores -= {"Store", "---"}
    matches = [
        entry
        for entry in entries
        if entry.store.removesuffix(" 👤") in stores
        and entry.subject in BROAD_SUBJECTS["美食"]
    ]
    return sorted(matches, key=lambda entry: (-(entry.rating or 0), entry.store)) if matches else None


def _entry_matches_subject(subject: str, entry: RegistryEntry) -> bool:
    terms = SUBJECT_MATCH_TERMS.get(subject)
    if terms is None:
        return True
    haystack = " ".join((entry.store, *entry.highlights)).lower()
    return any(term.lower() in haystack for term in terms)


def _query_location_intent(
    query: str,
    entries: list[RegistryEntry],
) -> tuple[LocationIntent | None, bool]:
    subject = _query_subject(query)
    if subject is None:
        return None, False
    labels = _registry_location_labels(entries)
    prompt = (
        "你是 AskDanny 的查詢意圖解析器，只能輸出 JSON，不要回答問題。"
        "請將使用者查詢轉為 subject、scope、locations、needs_confirmation。"
        "subject 必須使用指定主題；locations 只能從可用行政區清單選取。"
        "exact 代表單一明確行政區；regional 代表旅遊區或跨行政區概念，必須要求確認；"
        "unknown 代表無法安全判斷地區。不要選店家、不要補造資料。\n"
        f"指定 subject：{subject}\n"
        f"可用行政區清單：{json.dumps(labels, ensure_ascii=False)}\n"
        f"使用者查詢：{query}\n"
        'JSON 格式：{"subject":"...","scope":"exact|regional|unknown",'
        '"locations":["..."],"needs_confirmation":true|false}'
    )
    try:
        raw = route("query_answer", prompt, expect_json=True)
    except Exception:
        logger.exception("Query intent normalization failed")
        fallback = _conservative_location_intent(query, subject, labels, entries)
        return fallback, fallback is None

    def invalid_intent() -> tuple[LocationIntent | None, bool]:
        fallback = _conservative_location_intent(query, subject, labels, entries)
        return fallback, fallback is None

    if not isinstance(raw, dict) or raw.get("subject") != subject:
        return invalid_intent()
    scope = raw.get("scope")
    locations_raw = raw.get("locations")
    if scope not in {"exact", "regional", "unknown"} or not isinstance(locations_raw, list):
        return invalid_intent()
    if not all(isinstance(location, str) for location in locations_raw):
        return invalid_intent()
    locations = tuple(dict.fromkeys(location.strip() for location in locations_raw if location.strip()))
    if any(location not in labels for location in locations):
        return invalid_intent()
    if scope == "unknown" and locations:
        return invalid_intent()
    if scope == "exact" and len(locations) != 1:
        return invalid_intent()
    if scope == "regional" and not locations:
        return invalid_intent()
    needs_confirmation = scope == "regional" or bool(raw.get("needs_confirmation"))
    if needs_confirmation and not locations:
        return invalid_intent()
    return (
        LocationIntent(
            subject=subject,
            scope=scope,
            locations=locations,
            needs_confirmation=needs_confirmation,
        ),
        False,
    )


def _registry_matches(query: str, entries: list[RegistryEntry]) -> list[RegistryEntry] | None:
    subject = _query_subject(query)
    if subject is None:
        return None
    if not any(_entry_matches_location(query, entry) for entry in entries):
        return None
    matches = [
        entry
        for entry in entries
        if entry.subject in BROAD_SUBJECTS.get(subject, (subject,))
        and _entry_matches_subject(subject, entry)
        and _entry_matches_location(query, entry)
    ]
    return sorted(matches, key=lambda entry: (-(entry.rating or 0), entry.store))


def _render_registry_answer(entries: list[RegistryEntry]) -> str:
    displayed_entries = entries[:5]
    if len(entries) > len(displayed_entries):
        lines = [
            f"目前整理到 {len(entries)} 筆符合條件的資料，先列出前 {len(displayed_entries)} 筆："
        ]
    else:
        lines = [f"目前整理到 {len(entries)} 筆符合條件的資料："]
    for entry in displayed_entries:
        lines.extend(_render_registry_entry_lines(entry))
    return "\n".join(lines)


def _render_registry_entry_lines(entry: RegistryEntry) -> list[str]:
    maps_url = _registry_entry_maps_url(entry)
    store_line = f"- 店名：{entry.store}"
    if maps_url:
        store_line += f"（Google 地圖：{maps_url}）"
    lines = [f"\n- 主題：{entry.subject}", store_line]
    if entry.address:
        lines.append(f"- 地址：{entry.address}")
    if entry.phone:
        lines.append(f"- 電話：{entry.phone}")
    if entry.reservation_url:
        lines.append(f"- 預約連結：{entry.reservation_url}")
    if entry.rating is not None:
        rating_text = f"{entry.rating:g}"
        if entry.rating_count is not None:
            rating_text += f"（{entry.rating_count} 則）"
        lines.append(f"- Google 星等：⭐ {rating_text}")
    if entry.highlights:
        lines.append(f"- 特色說明：{'；'.join(entry.highlights[:3])}")
    return lines


def _registry_entry_maps_url(entry: RegistryEntry) -> str:
    """Return Google Maps search URL by store name (preferred) or fallback.

    Searching by store name returns the actual business listing with
    reviews, hours, and photos — coordinates only show a bare pin.
    """
    if entry.store and entry.store != "未提供":
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(entry.store)}"
    if entry.google_maps_url:
        return entry.google_maps_url
    if entry.address:
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(entry.address)}"
    if entry.gps:
        latitude, longitude = entry.gps
        coords = f"{latitude:.7f}".rstrip("0").rstrip(".") + "," + f"{longitude:.7f}".rstrip("0").rstrip(".")
        return f"https://www.google.com/maps/search/?api=1&query={coords}"
    return ""


def _render_registry_page(
    entries: tuple[RegistryEntry, ...],
    start: int,
    end: int,
) -> str:
    page_entries = entries[start:end]
    lines = [f"目前顯示第 {start + 1}–{end} 筆，共 {len(entries)} 筆："]
    for entry in page_entries:
        lines.extend(_render_registry_entry_lines(entry))
    return "\n".join(lines)


def _render_query_options(has_more: bool) -> str:
    lines = ["\n\n請選擇下一步："]
    if has_more:
        lines.append("1. 再看幾筆（例如：再看 10 筆）")
    else:
        lines.append("1. 已沒有更多資料")
    lines.append("2. 終止輸出")
    lines.append("3. 匯出目前已顯示的資料到我的 Google Sheet")
    return "\n".join(lines)


def _registry_entry_rows(entries: tuple[RegistryEntry, ...]) -> list[list[str]]:
    rows = [["主題", "店名", "地址", "電話", "預約連結", "Google 星等", "特色說明", "GPS"]]
    for entry in entries:
        rating = ""
        if entry.rating is not None:
            rating = f"⭐ {entry.rating:g}"
            if entry.rating_count is not None:
                rating += f"（{entry.rating_count} 則）"
        gps = ""
        if entry.gps:
            gps = _registry_entry_maps_url(entry)
        rows.append([
            entry.subject,
            entry.store,
            entry.address,
            entry.phone,
            entry.reservation_url,
            rating,
            "；".join(entry.highlights[:3]),
            gps,
        ])
    return rows


def _parse_more_count(text: str) -> int | None:
    match = MORE_COMMAND_RE.fullmatch(text.strip())
    return int(match.group(1)) if match else None


def _prune_pending_exports() -> None:
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    expired = [
        state
        for state, pending in PENDING_GOOGLE_EXPORTS.items()
        if pending.created_at < cutoff
    ]
    for state in expired:
        PENDING_GOOGLE_EXPORTS.pop(state, None)


def _prune_query_sessions() -> None:
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    expired = [
        user_id
        for user_id, session in QUERY_SESSIONS.items()
        if session.created_at < cutoff
    ]
    for user_id in expired:
        QUERY_SESSIONS.pop(user_id, None)


def _prune_location_confirmations() -> None:
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    expired = [
        user_id
        for user_id, pending in PENDING_LOCATION_CONFIRMATIONS.items()
        if pending.created_at < cutoff
    ]
    for user_id in expired:
        PENDING_LOCATION_CONFIRMATIONS.pop(user_id, None)


def _location_confirmation_text(query: str, intent: LocationIntent) -> str:
    locations = "、".join(intent.locations)
    return (
        f"「{query}」可能是區域查詢。是否要將以下行政區一起納入：{locations}？\n"
        "1. 包含這些地區\n"
        "2. 不包含，請重新指定地區"
    )


async def _handle_location_confirmation_event(
    cfg: dict,
    event: AskDannyEvent,
    text: str,
) -> bool:
    _prune_location_confirmations()
    text = unicodedata.normalize("NFKC", text).strip()
    pending = PENDING_LOCATION_CONFIRMATIONS.get(event.user_id)
    if pending is None:
        return False
    if text in LOCATION_CONFIRM_YES:
        PENDING_LOCATION_CONFIRMATIONS.pop(event.user_id, None)
        root = vault_root(cfg)
        if not root:
            await reply_message(cfg["access_token"], event.reply_token, "知識庫目前沒有設定好，請通知 Danny。")
            return True
        entries = _load_registry_entries(root)
        matches = _registry_matches_for_locations(
            pending.intent.subject, pending.intent.locations, entries
        )
        if not matches:
            await reply_message(
                cfg["access_token"], event.reply_token,
                "目前 Danny 的 Lifestyle Vault 沒有整理到確認範圍內的相關資料。",
            )
            return True
        answer = _render_registry_answer(matches)
        session = QuerySession(entries=tuple(matches), offset=min(5, len(matches)))
        QUERY_SESSIONS[event.user_id] = session
        answer += _render_query_options(session.offset < len(session.entries))
        await reply_message(
            cfg["access_token"], event.reply_token,
            answer + "\n📚 來源：" + REGISTRY_SOURCE_TITLE,
        )
        return True
    if text in LOCATION_CONFIRM_NO:
        PENDING_LOCATION_CONFIRMATIONS.pop(event.user_id, None)
        await reply_message(
            cfg["access_token"], event.reply_token,
            "好的，請重新指定行政區或地點，我不會自行擴大搜尋範圍。",
        )
        return True
    PENDING_LOCATION_CONFIRMATIONS.pop(event.user_id, None)
    return False


async def _start_google_export(cfg: dict, event: AskDannyEvent, session: QuerySession) -> None:
    config = google_oauth_config_from_env()
    if config is None:
        await reply_message(
            cfg["access_token"],
            event.reply_token,
            "Google Sheet 匯出尚未設定，請先通知 Danny 設定 Google OAuth。",
        )
        return

    _prune_pending_exports()
    state = secrets.token_urlsafe(32)
    displayed_entries = session.entries[: session.offset]
    PENDING_GOOGLE_EXPORTS[state] = PendingGoogleExport(
        user_id=event.user_id,
        entries=displayed_entries,
        created_at=time.monotonic(),
    )
    QUERY_SESSIONS.pop(event.user_id, None)
    url = google_authorization_url(config, state)
    await reply_message(
        cfg["access_token"],
        event.reply_token,
        "請點擊以下連結，用你的 Google 帳號授權建立 Sheet；完成後這次輸出會結束：\n" + url,
    )


async def _handle_query_session_event(
    cfg: dict,
    event: AskDannyEvent,
    text: str,
) -> bool:
    _prune_query_sessions()
    session = QUERY_SESSIONS.get(event.user_id)
    if session is None:
        return False
    if text in TERMINATE_COMMANDS:
        QUERY_SESSIONS.pop(event.user_id, None)
        await reply_message(cfg["access_token"], event.reply_token, "已終止這次輸出。")
        return True
    if text == "1":
        if session.offset >= len(session.entries):
            await reply_message(cfg["access_token"], event.reply_token, "已沒有更多資料。")
            return True
        await reply_message(
            cfg["access_token"], event.reply_token, "請輸入想再看的筆數，例如：再看 10 筆。"
        )
        return True
    if text in EXPORT_COMMANDS:
        await _start_google_export(cfg, event, session)
        return True

    count = _parse_more_count(text)
    if count is None:
        return False
    if count < 1:
        await reply_message(cfg["access_token"], event.reply_token, "筆數請輸入 1 以上。")
        return True
    if session.offset >= len(session.entries):
        await reply_message(cfg["access_token"], event.reply_token, "已沒有更多資料。")
        return True

    start = session.offset
    end = min(start + count, len(session.entries))
    QUERY_SESSIONS[event.user_id] = QuerySession(
        entries=session.entries,
        offset=end,
        created_at=session.created_at,
    )
    answer = _render_registry_page(session.entries, start, end)
    answer += _render_query_options(end < len(session.entries))
    await reply_message(cfg["access_token"], event.reply_token, answer)
    return True


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


def _query_tokens(query: str) -> set[str]:
    tokens = set(TOKEN_RE.findall(query.lower()))
    for phrase in re.findall(r"[\u4e00-\u9fff]{2,}", query.lower()):
        tokens.update(phrase[index : index + 2] for index in range(len(phrase) - 1))
    return tokens


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
    registry_entries = _load_registry_entries(root)
    neighborhood_matches = _tianmu_food_matches(query, root, registry_entries)
    if neighborhood_matches:
        return {
            "answer": _render_registry_answer(neighborhood_matches),
            "sources": [REGISTRY_SOURCE_TITLE],
            "error": None,
            "registry_entries": tuple(neighborhood_matches),
        }
    registry_index = build_search_index(registry_entries)
    indexed_matches = _indexed_registry_matches(query, registry_entries, registry_index)
    if indexed_matches:
        return {
            "answer": _render_registry_answer(indexed_matches),
            "sources": [REGISTRY_SOURCE_TITLE],
            "error": None,
            "registry_entries": tuple(indexed_matches),
        }
    registry_matches = _registry_matches(query, registry_entries)
    if registry_matches is not None:
        if registry_matches:
            return {
                "answer": _render_registry_answer(registry_matches),
                "sources": [REGISTRY_SOURCE_TITLE],
                "error": None,
                "registry_entries": tuple(registry_matches),
            }

    subject = _query_subject(query)
    if subject is not None:
        intent, intent_failed = _query_location_intent(query, registry_entries)
        if intent_failed:
            return {
                "answer": "抱歉，我暫時無法判斷這個地區範圍，請稍後再試。",
                "sources": [],
                "error": "llm_failed",
            }
        if intent is not None and intent.locations:
            if intent.needs_confirmation:
                return {
                    "answer": None,
                    "sources": [],
                    "error": "needs_location_confirmation",
                    "location_intent": intent,
                }
            normalized_matches = _registry_matches_for_locations(
                subject, intent.locations, registry_entries
            )
            if not normalized_matches:
                return {"answer": None, "sources": [], "error": "no_match"}
            return {
                "answer": _render_registry_answer(normalized_matches),
                "sources": [REGISTRY_SOURCE_TITLE],
                "error": None,
                "registry_entries": tuple(normalized_matches),
            }
        if registry_matches == []:
            return {"answer": None, "sources": [], "error": "no_match"}

    wiki_root = root / "wiki"
    query_lower = query.lower().strip()
    query_tokens = _query_tokens(query_lower)

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

    if await _handle_location_confirmation_event(cfg, event, text):
        return
    if await _handle_query_session_event(cfg, event, text):
        return

    if text.lower() in ("/help", "help", "說明", "怎麼用"):
        await reply_message(cfg["access_token"], event.reply_token, cfg["help_text"])
        return

    root = vault_root(cfg)
    if not root:
        await reply_message(cfg["access_token"], event.reply_token, "知識庫目前沒有設定好，請通知 Danny。")
        return

    QUERY_SESSIONS.pop(event.user_id, None)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _query_all, text, root)

    if result.get("error") == "no_match":
        await reply_message(
            cfg["access_token"], event.reply_token,
            "目前 Danny 的 Lifestyle Vault 沒有整理到相關資料。\n可以換個問法，或問我 /help 看看我能回答什麼。",
        )
        return
    if result.get("error") == "needs_location_confirmation":
        intent = result.get("location_intent")
        if isinstance(intent, LocationIntent):
            _prune_location_confirmations()
            PENDING_LOCATION_CONFIRMATIONS[event.user_id] = PendingLocationConfirmation(
                user_id=event.user_id,
                query=text,
                intent=intent,
                created_at=time.monotonic(),
            )
            await reply_message(
                cfg["access_token"], event.reply_token,
                _location_confirmation_text(text, intent),
            )
            return

    answer = (result.get("answer") or "").strip()
    registry_entries = result.get("registry_entries")
    if isinstance(registry_entries, tuple) and registry_entries:
        session = QuerySession(entries=registry_entries, offset=min(5, len(registry_entries)))
        QUERY_SESSIONS[event.user_id] = session
        answer += _render_query_options(session.offset < len(session.entries))
    sources = result.get("sources") or []
    lines = [answer]
    if sources:
        lines.append("\n📚 來源：" + "、".join(sources[:6]))
    await reply_message(cfg["access_token"], event.reply_token, "\n".join(lines))


@app.get("/oauth/google/callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> HTMLResponse:
    if error:
        return HTMLResponse("<h1>Google 授權已取消</h1><p>你可以關閉這個頁面，回到 LINE。</p>")
    if not code or not state:
        return HTMLResponse("<h1>Google 授權資料不完整</h1>", status_code=400)

    pending = PENDING_GOOGLE_EXPORTS.pop(state, None)
    if pending is None or time.monotonic() - pending.created_at > SESSION_TTL_SECONDS:
        return HTMLResponse("<h1>這個匯出連結已失效</h1><p>請回到 LINE 重新操作。</p>", status_code=400)

    config = google_oauth_config_from_env()
    if config is None:
        return HTMLResponse("<h1>Google Sheet 匯出尚未設定</h1>", status_code=503)

    try:
        result = await export_to_google_sheet(config, code, _registry_entry_rows(pending.entries))
    except (httpx.HTTPError, ValueError):
        logger.exception("Google Sheet export failed")
        return HTMLResponse("<h1>Google Sheet 匯出失敗</h1><p>請回到 LINE 稍後重試。</p>", status_code=502)

    cfg = askdanny_settings()
    await push_message(cfg["access_token"], pending.user_id, f"Google Sheet 已建立：{result.url}")
    safe_url = escape(result.url, quote=True)
    return HTMLResponse(
        f'<h1>匯出完成</h1><p><a href="{safe_url}">開啟 Google Sheet</a></p>'
    )


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
