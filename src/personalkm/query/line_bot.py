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
import math
import os
import re
import secrets
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus, unquote, urlparse

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from personalkm.capture.line import verify_line_signature
from personalkm.llm.base import LLMError
from personalkm.llm.router import route
from personalkm.llm.transcribe import transcribe
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
    "也可以分享你的目前位置（LINE 的「分享位置」功能，或直接貼一個 Google 地圖連結），然後問我：\n"
    "・「附近有什麼美食」（預設約 1 公里內）\n"
    "・「附近 5 公里有什麼景點」\n"
    "・「走路 10 分鐘內有什麼早餐店」\n"
    "・「開車 1 小時內有什麼美食」\n\n"
    "也可以直接傳語音訊息問我，效果跟打字一樣。\n\n"
    "我會根據 Danny 的筆記回答，並標注來源。\n\n"
    "輸入 /health 可以查看我目前載入的知識庫版本。"
)

# ── Nearby (location-based) query tuning ──────────────────────────────────
# Straight-line radius, not a real routed walking distance — this project
# deliberately has no live routing/Places API calls (see
# ASKDANNY-PHASE1-REQUIREMENTS.md §5). "10 分鐘走路" is approximated as a
# straight-line radius using a casual walking pace, discounted by a road-
# indirection factor so it doesn't overclaim precision.
WALK_SPEED_M_PER_MIN = 80.0
ROAD_INDIRECTION_FACTOR = 1.3
DEFAULT_NEARBY_RADIUS_KM = 1.0
MIN_NEARBY_RADIUS_KM = 0.1
MAX_NEARBY_RADIUS_KM = 20.0

# Driving mode: a much cruder approximation than walking — straight-line
# radius from an assumed mixed city/highway average speed, discounted by
# the same road-indirection factor. Still no live routing/traffic API.
DRIVE_SPEED_KM_PER_HOUR = 40.0
DRIVE_ROAD_INDIRECTION_FACTOR = 1.3
DEFAULT_DRIVE_RADIUS_KM = 20.0
MAX_DRIVE_RADIUS_KM = 100.0

NEARBY_TRIGGER_RE = re.compile(r"附近|走路|步行|開車|車程|自駕|公里|公尺|km|分鐘|小時")
DRIVE_TRIGGER_RE = re.compile(r"開車|車程|自駕", re.IGNORECASE)
RADIUS_KM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:公里|km)", re.IGNORECASE)
RADIUS_M_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:公尺|米|m\b)", re.IGNORECASE)
MINUTES_RE = re.compile(r"(\d+(?:\.\d+)?)\s*分鐘")
HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:小時|hr|hour)", re.IGNORECASE)

# Voice queries naturally produce Chinese numerals ("兩公里", "十公里"), not
# Arabic digits — confirmed as a real bug 2026-09-15 via live testing
# (Render logs showed every voice "附近十公里之內..." silently falling back
# to the 1km default because RADIUS_KM_RE only matches \d+). Normalize
# Chinese numerals into Arabic digits, immediately before a known unit
# word, before any of the regexes above ever run.
_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "兩": 2, "倆": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_NUMBER_BEFORE_UNIT_RE = re.compile(
    r"([零〇一二三四五六七八九十兩倆半點]+)(?=\s*(?:公里|km|公尺|米|分鐘|小時|hr|hour))",
    re.IGNORECASE,
)


def _cn_integer_to_value(cn: str) -> int | None:
    if not cn:
        return None
    if cn == "十":
        return 10
    if len(cn) == 1:
        return _CN_DIGITS.get(cn)
    if "十" in cn:
        tens_part, _, ones_part = cn.partition("十")
        tens = _CN_DIGITS.get(tens_part, 1) if tens_part else 1
        ones = _CN_DIGITS.get(ones_part, 0) if ones_part else 0
        if tens_part and tens_part not in _CN_DIGITS:
            return None
        if ones_part and ones_part not in _CN_DIGITS:
            return None
        return tens * 10 + ones
    return None


def _cn_number_to_value(cn: str) -> float | None:
    if cn in ("半",):
        return 0.5
    if "點" in cn:
        int_part, _, frac_part = cn.partition("點")
        int_value = _cn_integer_to_value(int_part) if int_part else 0
        if int_value is None:
            return None
        frac_digits = "".join(str(_CN_DIGITS[ch]) for ch in frac_part if ch in _CN_DIGITS)
        if not frac_digits:
            return None
        return float(f"{int_value}.{frac_digits}")
    return _cn_integer_to_value(cn)


def _normalize_chinese_numerals(text: str) -> str:
    def _replace(match: re.Match) -> str:
        value = _cn_number_to_value(match.group(1))
        if value is None:
            return match.group(0)
        return str(int(value)) if value == int(value) else str(value)

    return _CN_NUMBER_BEFORE_UNIT_RE.sub(_replace, text)

# ── Location from a pasted Google Maps link ────────────────────────────────
# A "pin on map" link (@lat,lng) or a query-param link (q=/ll=lat,lng)
# carries plain coordinates we can parse for free. A "share this place"
# link (the most common share-sheet format) carries only an opaque place
# ID + human-readable name — resolving THAT to coordinates needs a live
# Places API Text Search call (see _geocode_via_places_api). Both paths are
# a deliberate, narrow exception to this project's "no live external calls"
# default, scoped only to a pasted Maps link the user explicitly shared.
MAPS_URL_RE = re.compile(r"https?://\S+")
ALLOWED_MAPS_HOSTS = {"maps.app.goo.gl", "www.google.com", "google.com", "maps.google.com"}
MAPS_PLACE_COORD_RE = re.compile(r"!3d(-?\d{1,3}\.\d+)!4d(-?\d{1,3}\.\d+)")
MAPS_AT_COORD_RE = re.compile(r"@(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)")
MAPS_QUERY_COORD_RE = re.compile(r"[?&](?:q|query|ll)=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)")
MAPS_PLACE_NAME_RE = re.compile(r"/maps/place/([^/?]+)")
PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

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
    "早午餐": ("早午餐", "brunch", "早餐", "早餐店"),
    "牛肉麵": ("牛肉麵", "牛肉面"),
    "拉麵": ("拉麵", "拉面", "ramen"),
    "眷村菜": ("眷村菜", "眷村"),
    "住宿": ("住宿", "旅館", "民宿", "飯店", "酒店", "lodging"),
    "咖啡廳": ("咖啡廳", "咖啡館", "咖啡店", "cafe", "coffee"),
    "餐廳": ("餐廳", "restaurant"),
    "景點": ("景點",),
    "海鮮": ("海鮮", "海產"),
}
BROAD_SUBJECTS = {
    "美食": ("餐廳", "小吃", "早午餐", "咖啡廳", "甜點", "酒吧"),
    "牛肉麵": ("小吃", "餐廳"),
    "拉麵": ("小吃", "餐廳"),
    "眷村菜": ("小吃", "餐廳"),
    "海鮮": ("小吃", "餐廳"),
}
SUBJECT_MATCH_TERMS = {
    "牛肉麵": ("牛肉麵", "牛肉面"),
    "拉麵": ("拉麵", "拉面", "ramen"),
    # Deliberately just "眷村", not "眷村菜" — real registry entries say
    # "眷村老店"/"眷村味合菜"/"眷村家常餐館" etc., never the bare compound
    # "眷村菜" itself. Bug found 2026-09-15: without this subject existing
    # at all, "台北地區眷村菜" matched via plain keyword search with NO
    # category filter, pulling in 蟾蜍山煥民新村 (subject 景點, a preserved
    # military-village historic site) alongside the actual restaurants.
    "眷村菜": ("眷村",),
    # "海鮮"/"海產" are used interchangeably in registry highlights (e.g.
    # "現撈活海產" vs "海鮮料理"). Bug found 2026-09-21: "萬里海鮮" matched
    # only entries containing the literal string "海鮮", silently dropping
    # 討海人食堂 whose highlight says "現撈活海產" instead. See also the
    # general SYNONYM_GROUPS expansion in search_index.py, which applies
    # this same 海鮮/海產 pairing to any keyword search, not just this
    # subject's exact-match filter.
    "海鮮": ("海鮮", "海產"),
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
class AskDannyAudioEvent:
    reply_token: str
    user_id: str
    message_id: str


@dataclass(frozen=True)
class AskDannyLocationEvent:
    reply_token: str
    user_id: str
    latitude: float
    longitude: float


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
    # Only ever set transiently by nearby-search matching, never loaded from
    # the registry — distance from the user's last shared location.
    distance_km: float | None = None


@dataclass(frozen=True, slots=True)
class QuerySession:
    entries: tuple[RegistryEntry, ...]
    offset: int
    created_at: float = field(default_factory=time.monotonic)
    # Set only right after prompting "請輸入想再看的筆數" (option "1") — while
    # true, the next message is treated as a raw count even if it's "1"/"2"/
    # "3", which would otherwise collide with the fixed menu option numbers
    # (再看幾筆/終止輸出/匯出). Bug found via real usage 2026-09-15: asking
    # for exactly 1-3 more results after that prompt silently hit the wrong
    # branch (terminate/export) instead.
    awaiting_count: bool = False


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


@dataclass(frozen=True, slots=True)
class PendingLocation:
    user_id: str
    latitude: float
    longitude: float
    created_at: float = field(default_factory=time.monotonic)


QUERY_SESSIONS: dict[str, QuerySession] = {}
PENDING_GOOGLE_EXPORTS: dict[str, PendingGoogleExport] = {}
PENDING_LOCATION_CONFIRMATIONS: dict[str, PendingLocationConfirmation] = {}
PENDING_LOCATIONS: dict[str, PendingLocation] = {}


def askdanny_events_from_webhook(
    payload: dict,
) -> list[AskDannyEvent | AskDannyLocationEvent | AskDannyAudioEvent]:
    events: list[AskDannyEvent | AskDannyLocationEvent | AskDannyAudioEvent] = []
    for raw_event in payload.get("events", []):
        if raw_event.get("type") != "message":
            continue
        message = raw_event.get("message", {})
        reply_token = raw_event.get("replyToken", "")
        user_id = raw_event.get("source", {}).get("userId", "")
        if not reply_token:
            continue
        message_type = message.get("type")
        if message_type == "text":
            text = message.get("text", "")
            if text:
                events.append(AskDannyEvent(reply_token=reply_token, user_id=user_id, text=text))
        elif message_type == "location":
            latitude = message.get("latitude")
            longitude = message.get("longitude")
            if (
                isinstance(latitude, (int, float)) and not isinstance(latitude, bool)
                and isinstance(longitude, (int, float)) and not isinstance(longitude, bool)
            ):
                events.append(
                    AskDannyLocationEvent(
                        reply_token=reply_token,
                        user_id=user_id,
                        latitude=float(latitude),
                        longitude=float(longitude),
                    )
                )
        elif message_type == "audio":
            message_id = message.get("id")
            if isinstance(message_id, str) and message_id:
                events.append(
                    AskDannyAudioEvent(reply_token=reply_token, user_id=user_id, message_id=message_id)
                )
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


async def _download_line_audio_content(access_token: str, message_id: str) -> bytes | None:
    if not access_token or not message_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://api-data.line.me/v2/bot/message/{message_id}/content",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.content
    except httpx.HTTPError:
        logger.warning("Failed to download LINE audio content for message %s", message_id)
        return None


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
    # Neighborhood → district alias map. These are non-administrative
    # toponyms that users commonly ask about but that never appear in
    # address fields (which only carry 區/鄉/鎮).
    NEIGHBORHOOD_ALIASES = {
        "天母": "士林區",
        "芝山": "士林區",
        "石牌": "北投區",
        "陽明山": "北投區",
    }
    candidates = [
        label
        for label in labels
        if label in query or label.removesuffix("市") in query
        or label.removesuffix("區") in query
        or label.removesuffix("鄉") in query
        or label.removesuffix("鎮") in query
    ]
    # Resolve neighborhood aliases to their parent district
    for neighborhood, district in NEIGHBORHOOD_ALIASES.items():
        if neighborhood in query and district in labels:
            candidates.append(district)
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
    if "天母" not in query or _query_subject(query) != "美食":
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


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * earth_radius_km * math.asin(min(1.0, math.sqrt(a)))


def _detect_nearby_mode(text: str) -> str:
    return "drive" if DRIVE_TRIGGER_RE.search(text) else "walk"


def _parse_nearby_radius(text: str) -> tuple[float, str]:
    text = _normalize_chinese_numerals(text)
    mode = _detect_nearby_mode(text)
    match = RADIUS_KM_RE.search(text)
    if match:
        radius_km = float(match.group(1))
    else:
        match = RADIUS_M_RE.search(text)
        if match:
            radius_km = float(match.group(1)) / 1000.0
        elif mode == "drive":
            hours_match = HOURS_RE.search(text)
            if hours_match:
                hours = float(hours_match.group(1))
            else:
                minutes_match = MINUTES_RE.search(text)
                hours = float(minutes_match.group(1)) / 60.0 if minutes_match else None
            if hours is None:
                radius_km = DEFAULT_DRIVE_RADIUS_KM
            else:
                radius_km = hours * DRIVE_SPEED_KM_PER_HOUR / DRIVE_ROAD_INDIRECTION_FACTOR
        else:
            minutes_match = MINUTES_RE.search(text)
            if minutes_match:
                minutes = float(minutes_match.group(1))
                radius_km = minutes * WALK_SPEED_M_PER_MIN / ROAD_INDIRECTION_FACTOR / 1000.0
            else:
                radius_km = DEFAULT_NEARBY_RADIUS_KM
    max_radius_km = MAX_DRIVE_RADIUS_KM if mode == "drive" else MAX_NEARBY_RADIUS_KM
    return max(MIN_NEARBY_RADIUS_KM, min(radius_km, max_radius_km)), mode


def _nearby_registry_matches(
    subject: str | None,
    latitude: float,
    longitude: float,
    radius_km: float,
    entries: list[RegistryEntry],
) -> list[RegistryEntry]:
    allowed_subjects = BROAD_SUBJECTS.get(subject, (subject,)) if subject else None
    matches: list[RegistryEntry] = []
    for entry in entries:
        if entry.gps is None:
            continue
        if allowed_subjects is not None and entry.subject not in allowed_subjects:
            continue
        if subject is not None and not _entry_matches_subject(subject, entry):
            continue
        distance_km = _haversine_km(latitude, longitude, entry.gps[0], entry.gps[1])
        if distance_km <= radius_km:
            matches.append(replace(entry, distance_km=distance_km))
    matches.sort(key=lambda entry: entry.distance_km)
    return matches


def _extract_maps_coords(url: str) -> tuple[float, float] | None:
    for pattern in (MAPS_PLACE_COORD_RE, MAPS_AT_COORD_RE, MAPS_QUERY_COORD_RE):
        match = pattern.search(url)
        if not match:
            continue
        try:
            latitude, longitude = float(match.group(1)), float(match.group(2))
        except ValueError:
            continue
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude
    return None


def _extract_maps_place_name(url: str) -> str | None:
    match = MAPS_PLACE_NAME_RE.search(url)
    if not match:
        return None
    name = unquote(match.group(1)).replace("+", " ").strip()
    return name or None


async def _geocode_via_places_api(query: str) -> tuple[float, float] | None:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key or not query:
        return None
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.post(
                PLACES_TEXT_SEARCH_URL,
                json={"textQuery": query},
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.location",
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        logger.warning("Places API geocode call failed for pasted Maps link")
        return None
    places = data.get("places") or []
    if not places:
        return None
    location = places[0].get("location") or {}
    latitude, longitude = location.get("latitude"), location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return None
    return float(latitude), float(longitude)


async def _resolve_location_from_text(text: str) -> tuple[float, float] | None:
    url_match = MAPS_URL_RE.search(text)
    if not url_match:
        return None
    url = url_match.group(0)
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return None
    if host not in ALLOWED_MAPS_HOSTS:
        return None

    coords = _extract_maps_coords(url)
    if coords is not None:
        return coords

    resolved_url = url
    if host == "maps.app.goo.gl":
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                response = await client.get(url)
        except httpx.HTTPError:
            logger.warning("Failed to resolve Maps short link")
            return None
        resolved_url = str(response.url)
        coords = _extract_maps_coords(resolved_url)
        if coords is not None:
            return coords

    place_name = _extract_maps_place_name(resolved_url)
    if place_name is None:
        return None
    return await _geocode_via_places_api(place_name)


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
    if entry.distance_km is not None:
        lines.append(f"- 距離：約 {entry.distance_km:.1f} 公里（直線距離估算，非實際路徑）")
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
    show_distance = any(entry.distance_km is not None for entry in entries)
    header = ["主題", "店名", "地址", "電話", "預約連結", "Google 星等", "特色說明", "GPS"]
    if show_distance:
        header.insert(3, "距離（公里）")
    rows = [header]
    for entry in entries:
        rating = ""
        if entry.rating is not None:
            rating = f"⭐ {entry.rating:g}"
            if entry.rating_count is not None:
                rating += f"（{entry.rating_count} 則）"
        gps = ""
        if entry.gps:
            gps = _registry_entry_maps_url(entry)
        row = [
            entry.subject,
            entry.store,
            entry.address,
            entry.phone,
            entry.reservation_url,
            rating,
            "；".join(entry.highlights[:3]),
            gps,
        ]
        if show_distance:
            row.insert(3, f"{entry.distance_km:.1f}" if entry.distance_km is not None else "")
        rows.append(row)
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


def _prune_pending_locations() -> None:
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    expired = [
        user_id
        for user_id, pending in PENDING_LOCATIONS.items()
        if pending.created_at < cutoff
    ]
    for user_id in expired:
        PENDING_LOCATIONS.pop(user_id, None)


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


NEARBY_PROMPT_TEXT = (
    "想找什麼可以這樣問我：\n"
    "・「附近有什麼美食」（預設約 1 公里內）\n"
    "・「附近 5 公里有什麼景點」\n"
    "・「走路 10 分鐘內有什麼早餐店」\n"
    "・「開車 1 小時內有什麼美食」"
)


async def handle_location_event(cfg: dict, event: AskDannyLocationEvent) -> None:
    if not is_allowed(cfg, event.user_id):
        await reply_message(cfg["access_token"], event.reply_token, GENERIC_DENY_TEXT)
        return
    _prune_pending_locations()
    PENDING_LOCATIONS[event.user_id] = PendingLocation(
        user_id=event.user_id,
        latitude=event.latitude,
        longitude=event.longitude,
    )
    minutes = SESSION_TTL_SECONDS // 60
    await reply_message(
        cfg["access_token"], event.reply_token,
        f"收到你的位置了！{NEARBY_PROMPT_TEXT}\n"
        f"（這個位置 {minutes} 分鐘內有效，之後要請你重新分享位置。）",
    )


async def handle_audio_event(cfg: dict, event: AskDannyAudioEvent) -> None:
    if not is_allowed(cfg, event.user_id):
        await reply_message(cfg["access_token"], event.reply_token, GENERIC_DENY_TEXT)
        return

    audio_bytes = await _download_line_audio_content(cfg["access_token"], event.message_id)
    if audio_bytes is None:
        await reply_message(
            cfg["access_token"], event.reply_token,
            "抱歉，我沒辦法下載這段語音，請再傳一次，或直接打字問我。",
        )
        return

    try:
        text = await transcribe(audio_bytes, filename="voice.m4a")
    except LLMError:
        logger.exception("Voice transcription failed for user %s", event.user_id[:8] or "?")
        await reply_message(
            cfg["access_token"], event.reply_token,
            "抱歉，我暫時沒辦法辨識這段語音，可以直接打字問我，或稍後再試一次語音。",
        )
        return

    if not text:
        await reply_message(
            cfg["access_token"], event.reply_token,
            "抱歉，我聽不清楚這段語音內容，可以再說一次，或直接打字問我。",
        )
        return

    logger.info("AskDanny voice query from %s transcribed: %r", event.user_id[:8] or "?", text[:80])
    # Reuse the exact same pipeline a typed message goes through — allowlist
    # was already checked above, but handle_text_event checks it again
    # (harmless) and this keeps voice from ever bypassing any of the
    # nearby/maps-link/session/output-gating logic built for text.
    await handle_text_event(cfg, AskDannyEvent(reply_token=event.reply_token, user_id=event.user_id, text=text))


async def _answer_nearby_query(
    cfg: dict,
    reply_token: str,
    user_id: str,
    latitude: float,
    longitude: float,
    text: str,
) -> None:
    subject = _query_subject(text)
    radius_km, mode = _parse_nearby_radius(text)
    mode_label = "開車" if mode == "drive" else "走路"

    root = vault_root(cfg)
    if not root:
        await reply_message(cfg["access_token"], reply_token, "知識庫目前沒有設定好，請通知 Danny。")
        return

    entries = _load_registry_entries(root)
    matches = _nearby_registry_matches(subject, latitude, longitude, radius_km, entries)

    if not matches:
        await reply_message(
            cfg["access_token"], reply_token,
            f"目前 Danny 的 Lifestyle Vault 在你分享的位置附近（{mode_label}約 {radius_km:.1f} 公里內）"
            "沒有整理到相關資料，可以試試擴大範圍或換個類型。",
        )
        return

    QUERY_SESSIONS.pop(user_id, None)
    answer = _render_registry_answer(matches)
    session = QuerySession(entries=tuple(matches), offset=min(5, len(matches)))
    QUERY_SESSIONS[user_id] = session
    answer += _render_query_options(session.offset < len(session.entries))
    answer += (
        f"\n📍 搜尋範圍：{mode_label}約 {radius_km:.1f} 公里內"
        "（直線距離估算，含粗略路網修正，非實際路徑或即時路況）"
    )
    await reply_message(
        cfg["access_token"], reply_token,
        answer + "\n📚 來源：" + REGISTRY_SOURCE_TITLE,
    )


async def _handle_nearby_event(cfg: dict, event: AskDannyEvent, text: str) -> bool:
    _prune_pending_locations()
    pending = PENDING_LOCATIONS.get(event.user_id)
    if pending is None or not NEARBY_TRIGGER_RE.search(text):
        return False
    await _answer_nearby_query(cfg, event.reply_token, event.user_id, pending.latitude, pending.longitude, text)
    return True


async def _handle_maps_link_event(cfg: dict, event: AskDannyEvent, text: str) -> bool:
    if not MAPS_URL_RE.search(text):
        return False
    if not is_allowed(cfg, event.user_id):
        # Allowlist is already enforced earlier in handle_text_event before
        # this is ever reached — this is a defense-in-depth no-op guard so a
        # future caller of this function directly can't skip FR-01.
        return True

    location = await _resolve_location_from_text(text)
    if location is None:
        await reply_message(
            cfg["access_token"], event.reply_token,
            "抱歉，我沒辦法從這個地圖連結取得座標，可以改用 LINE 的「分享位置」功能，"
            "或分享一個有標示經緯度的地圖連結。",
        )
        return True

    latitude, longitude = location
    _prune_pending_locations()
    PENDING_LOCATIONS[event.user_id] = PendingLocation(
        user_id=event.user_id, latitude=latitude, longitude=longitude,
    )
    remaining_text = MAPS_URL_RE.sub("", text).strip()
    if not NEARBY_TRIGGER_RE.search(remaining_text):
        minutes = SESSION_TTL_SECONDS // 60
        await reply_message(
            cfg["access_token"], event.reply_token,
            f"收到你分享的地圖位置了！{NEARBY_PROMPT_TEXT}\n"
            f"（這個位置 {minutes} 分鐘內有效，之後要請你重新分享位置。）",
        )
        return True

    await _answer_nearby_query(cfg, event.reply_token, event.user_id, latitude, longitude, remaining_text)
    return True


async def _handle_query_session_event(
    cfg: dict,
    event: AskDannyEvent,
    text: str,
) -> bool:
    _prune_query_sessions()
    session = QUERY_SESSIONS.get(event.user_id)
    if session is None:
        return False

    if session.awaiting_count:
        count = _parse_more_count(text)
        if count is not None:
            return await _show_more_query_entries(cfg, event, session, count)
        # Not parseable as a count — fall through to the normal menu
        # handling below (e.g. the user typed "終止" instead of a number).

    if text in TERMINATE_COMMANDS:
        QUERY_SESSIONS.pop(event.user_id, None)
        await reply_message(cfg["access_token"], event.reply_token, "已終止這次輸出。")
        return True
    if text == "1":
        if session.offset >= len(session.entries):
            await reply_message(cfg["access_token"], event.reply_token, "已沒有更多資料。")
            return True
        QUERY_SESSIONS[event.user_id] = replace(session, awaiting_count=True)
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
    return await _show_more_query_entries(cfg, event, session, count)


async def _show_more_query_entries(
    cfg: dict,
    event: AskDannyEvent,
    session: QuerySession,
    count: int,
) -> bool:
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
    if await _handle_maps_link_event(cfg, event, text):
        return
    if await _handle_nearby_event(cfg, event, text):
        return

    if text.lower() in ("/help", "help", "說明", "怎麼用"):
        await reply_message(cfg["access_token"], event.reply_token, cfg["help_text"])
        return

    if text.lower() in ("/health", "/status"):
        await reply_message(cfg["access_token"], event.reply_token, _vault_status_text(cfg))
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
        if isinstance(event, AskDannyLocationEvent):
            background_tasks.add_task(handle_location_event, cfg, event)
        elif isinstance(event, AskDannyAudioEvent):
            background_tasks.add_task(handle_audio_event, cfg, event)
        else:
            background_tasks.add_task(handle_text_event, cfg, event)
    logger.info("Accepted %s AskDanny message(s)", len(events))
    return {"ok": True, "accepted": len(events)}


def _vault_diagnostics(cfg: dict) -> dict:
    """Report what data this running process actually has loaded, so a stale
    vault clone (only pulled at process startup — see
    scripts/start_askdanny_render.sh) is visible from the outside instead of
    silently producing under-counted query results."""
    root = vault_root(cfg)
    if root is None:
        return {"vault_found": False}
    entry_count = len(_load_registry_entries(root))
    commit, commit_date = None, None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%h %cI"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            commit, commit_date = result.stdout.strip().split(" ", 1)
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "vault_found": True,
        "vault_path": str(root),
        "registry_entry_count": entry_count,
        "vault_git_commit": commit,
        "vault_git_commit_date": commit_date,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "bot": "askdanny", **_vault_diagnostics(askdanny_settings())}


def _vault_status_text(cfg: dict) -> str:
    diag = _vault_diagnostics(cfg)
    if not diag.get("vault_found"):
        return "⚠️ 知識庫目前沒有載入，請通知 Danny。"
    commit = diag.get("vault_git_commit") or "未知"
    commit_date = diag.get("vault_git_commit_date") or "未知"
    return (
        "📊 AskDanny 知識庫狀態\n"
        f"筆數：{diag.get('registry_entry_count')} 筆\n"
        f"版本：{commit}\n"
        f"更新時間：{commit_date}"
    )
