import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from bot.config import get_settings
from bot.git_store import commit_and_push, ensure_vault
from bot.hermes_enrich import enrich_note
from bot.knowledge_decay import analyze_on_capture
from bot.line import LineTextEvent, extract_urls, mark_message_as_read, text_message_events_from_webhook, verify_line_signature
from bot.link_processor import parse_line_message_part, process_line_message_context, process_url, should_capture_line_message_context
from bot.notes import write_note


app = FastAPI(title="Personal KM LINE Link Bot")
logger = logging.getLogger(__name__)
LINE_PARTS_FILE = ".line-message-parts.json"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def save_note(settings, vault_path, note) -> None:
    note_path = write_note(vault_path, "raw", note)
    await asyncio.to_thread(enrich_note, note_path)
    await asyncio.to_thread(analyze_on_capture, note_path)
    await asyncio.to_thread(commit_and_push, settings, note_path)
    logger.info("✅ Captured and enriched LINE note into raw/ → %s", note_path.relative_to(vault_path))


def line_parts_path(vault_path: Path) -> Path:
    return vault_path / LINE_PARTS_FILE


def load_line_parts(vault_path: Path) -> dict:
    path = line_parts_path(vault_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Ignoring unreadable LINE parts cache at %s", path)
        return {}


def save_line_parts(vault_path: Path, cache: dict) -> None:
    line_parts_path(vault_path).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_line_message_part(vault_path: Path, text: str) -> Optional[str]:
    part = parse_line_message_part(text)
    if not part:
        return text

    cache = load_line_parts(vault_path)
    key = f"{part.label}:{part.total}"
    entry = cache.setdefault(key, {"total": part.total, "parts": {}, "updated_at": time.time()})
    entry["parts"][str(part.index)] = text
    entry["updated_at"] = time.time()

    expected = {str(index) for index in range(1, part.total + 1)}
    if set(entry["parts"]) != expected:
        save_line_parts(vault_path, cache)
        logger.info("Stored LINE message part %s/%s for %s", part.index, part.total, part.label)
        return None

    merged = "\n\n".join(entry["parts"][str(index)] for index in range(1, part.total + 1))
    cache.pop(key, None)
    save_line_parts(vault_path, cache)
    logger.info("Merged %s LINE message parts for %s", part.total, part.label)
    return merged


async def mark_line_event_as_read(settings, event: LineTextEvent) -> None:
    try:
        marked = await mark_message_as_read(settings.line_channel_access_token, event.mark_as_read_token)
        if marked:
            logger.info("Marked LINE message as read")
    except Exception:
        logger.exception("Failed to mark LINE message as read")


async def capture_line_messages(events: list[LineTextEvent]) -> None:
    settings = get_settings()
    logger.info("Processing %s LINE message(s)", len(events))

    try:
        vault_path = await asyncio.to_thread(ensure_vault, settings)
    except Exception:
        logger.exception("Failed to prepare vault repo")
        return

    for event in events:
        text = event.text
        text = collect_line_message_part(vault_path, text)
        if text is None:
            continue

        saved_any_note = False
        urls = extract_urls(text)
        if should_capture_line_message_context(text, settings.max_page_chars):
            try:
                note = await process_line_message_context(settings, text, urls)
                await save_note(settings, vault_path, note)
                saved_any_note = True
            except Exception:
                logger.exception("Failed to capture LINE pasted message")

        for url in urls:
            try:
                note = await process_url(settings, url, text)
                await save_note(settings, vault_path, note)
                saved_any_note = True
                logger.info("✅ Captured LINE URL %s", url)
            except Exception:
                logger.exception("Failed to capture LINE URL %s", url)

        if saved_any_note:
            await mark_line_event_as_read(settings, event)


async def capture_urls(urls: list[tuple[str, str]]) -> None:
    settings = get_settings()
    logger.info("Processing %s LINE URL(s)", len(urls))

    try:
        vault_path = await asyncio.to_thread(ensure_vault, settings)
    except Exception:
        logger.exception("Failed to prepare vault repo")
        return

    for url, context_text in urls:
        try:
            note = await process_url(settings, url, context_text)
            await save_note(settings, vault_path, note)
            logger.info("✅ Captured LINE URL %s", url)
        except Exception:
            logger.exception("Failed to capture LINE URL %s", url)


@app.post("/webhook/line")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: Optional[str] = Header(default=None),
) -> dict:
    settings = get_settings()
    body = await request.body()
    if not verify_line_signature(body, settings.line_channel_secret, x_line_signature):
        logger.warning("Rejected LINE webhook with invalid signature")
        raise HTTPException(status_code=401, detail="Invalid LINE signature")

    payload = await request.json()
    events = text_message_events_from_webhook(payload)
    urls = [(url, event.text) for event in events for url in extract_urls(event.text)]
    has_capturable_text = any(
        parse_line_message_part(event.text) or should_capture_line_message_context(event.text, settings.max_page_chars)
        for event in events
    )

    if not urls and not has_capturable_text:
        logger.info("LINE webhook received no capturable text or URLs")
        return {"ok": True, "accepted": 0}

    background_tasks.add_task(capture_line_messages, events)
    logger.info("Accepted %s LINE message(s) for background processing", len(events))
    return {"ok": True, "accepted": len(events)}
