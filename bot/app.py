import asyncio
import logging
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from bot.config import get_settings
from bot.git_store import commit_and_push, ensure_vault
from bot.hermes_enrich import enrich_note
from bot.knowledge_decay import analyze_on_capture
from bot.line import extract_urls, text_messages_from_webhook, verify_line_signature
from bot.link_processor import process_line_message_context, process_url, should_capture_line_message_context
from bot.notes import write_note


app = FastAPI(title="Personal KM LINE Link Bot")
logger = logging.getLogger(__name__)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def save_note(settings, vault_path, note) -> None:
    note_path = write_note(vault_path, "raw", note)
    await asyncio.to_thread(enrich_note, note_path)
    await asyncio.to_thread(analyze_on_capture, note_path)
    await asyncio.to_thread(commit_and_push, settings, note_path)
    logger.info("✅ Captured and enriched LINE note into raw/ → %s", note_path.relative_to(vault_path))


async def capture_line_messages(messages: list[str]) -> None:
    settings = get_settings()
    logger.info("Processing %s LINE message(s)", len(messages))

    try:
        vault_path = await asyncio.to_thread(ensure_vault, settings)
    except Exception:
        logger.exception("Failed to prepare vault repo")
        return

    for text in messages:
        urls = extract_urls(text)
        if should_capture_line_message_context(text, settings.max_page_chars):
            try:
                note = await process_line_message_context(settings, text, urls)
                await save_note(settings, vault_path, note)
            except Exception:
                logger.exception("Failed to capture LINE pasted message")

        for url in urls:
            try:
                note = await process_url(settings, url, text)
                await save_note(settings, vault_path, note)
                logger.info("✅ Captured LINE URL %s", url)
            except Exception:
                logger.exception("Failed to capture LINE URL %s", url)


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
    messages = text_messages_from_webhook(payload)
    urls = [(url, text) for text in messages for url in extract_urls(text)]

    if not urls:
        logger.info("LINE webhook received no URLs")
        return {"ok": True, "accepted": 0}

    background_tasks.add_task(capture_line_messages, messages)
    logger.info("Accepted %s LINE URL(s) for background processing", len(urls))
    return {"ok": True, "accepted": len(urls)}
