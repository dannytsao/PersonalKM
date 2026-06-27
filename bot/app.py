import asyncio
import json
import logging
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from bot.config import get_settings
from bot.git_store import commit_and_push, ensure_vault
from bot.line import LineTextEvent, extract_urls, mark_message_as_read, text_message_events_from_webhook, verify_line_signature
from bot.link_processor import parse_line_message_part, process_line_message_context, process_url, should_capture_line_message_context
from bot.notes import write_note
from bot.notification import notify as send_notification


app = FastAPI(title="Personal KM LINE Link Bot")
logger = logging.getLogger(__name__)
LINE_PARTS_FILE = ".line-message-parts.json"
LINE_LOG_SEQUENCE_FILE = ".line-log-sequence.json"
LINE_LOG_TIMEZONE = ZoneInfo("Asia/Taipei")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/query")
async def query_vault(q: str = "", top_k: int = 10) -> dict:
    """Search the vault with natural language. Returns JSON with matched pages."""
    if not q:
        return {"error": "Missing 'q' parameter (e.g. /query?q=hermes+agent)"}
    from bot.query_engine import query_wiki
    settings = get_settings()
    vault_path = await asyncio.to_thread(ensure_vault, settings)
    result = query_wiki(q, vault_path, top_k=top_k, use_llm=False)
    return result


# ── Helpers ────────────────────────────────────────────────────────────────

def _commit_and_push_wiki(vault_path: Path) -> None:
    """
    Commit and push any wiki/ changes created by ingest_raw_to_wiki().
    Runs after ingest so Phase A captures the full pipeline:
      raw/ → (ingest) → wiki/entities → (this) → git push
    """
    import os
    from bot.config import get_settings
    from bot.git_store import run_git

    settings = get_settings()
    wiki_path = vault_path / "wiki"

    # Check if there are any changes in wiki/
    status = run_git(["status", "--porcelain", "wiki/"], vault_path, settings)
    if not status.strip():
        logger.debug("No wiki changes to commit")
        return

    run_git(["add", "wiki/"], vault_path, settings)
    run_git(["commit", "-m", "🤖 Auto: ingest raw → wiki entities"], vault_path, settings)
    run_git(["push", "origin", settings.vault_branch], vault_path, settings)
    logger.info("Pushed wiki/ changes to GitHub")


async def run_immediate_ingestion(vault_path: Path) -> None:
    """
    Phase A: Immediately ingest all raw files after LINE capture.
    Runs in background — failures are logged but do NOT block the webhook response.
    """
    from bot.config import get_settings
    from bot.git_store import run_git
    from bot.ingestion_v2 import ingest_raw_to_wiki

    settings = get_settings()

    # Pull latest: save_note already pushed raw/ changes, we need them locally
    try:
        run_git(["pull", "--ff-only", "origin", settings.vault_branch], vault_path, settings)
    except Exception as e:
        logger.warning(f"Phase A: git pull failed (may be up-to-date): {e}")

    try:
        logger.info("🚀 Phase A: Starting immediate ingestion...")
        result = await asyncio.to_thread(ingest_raw_to_wiki, vault_path)

        processed = result.get("processed", 0)
        failed = result.get("failed", 0)
        status = result.get("status", "unknown")

        logger.info(
            f"Phase A complete: status={status}, processed={processed}, failed={failed}"
        )

        # Push wiki entities (ingest_raw_to_wiki writes to wiki/ but doesn't git push)
        if processed > 0:
            try:
                _commit_and_push_wiki(vault_path)
            except Exception as e:
                logger.warning(f"Phase A: failed to push wiki changes: {e}")

        if status in ("success", "partial"):
            send_notification(
                title="✅ Ingestion Complete",
                message=f"Processed: {processed} | Failed: {failed}",
                success=True,
            )
        else:
            send_notification(
                title="❌ Ingestion Failed",
                message=result.get("message", "Unknown error"),
                success=False,
            )
    except Exception as e:
        logger.exception(f"Phase A ingestion crashed: {e}")
        send_notification(
            title="❌ Ingestion Crashed",
            message=str(e),
            success=False,
        )


async def save_note(settings, vault_path, note, log_id: str = "") -> None:
    if log_id:
        note = replace(note, log_id=log_id)
    note_path = write_note(vault_path, "raw", note)
    await asyncio.to_thread(commit_and_push, settings, note_path)
    logger.info("✅ Captured LINE note into raw/ → %s", note_path.relative_to(vault_path))


def line_parts_path(vault_path: Path) -> Path:
    return vault_path / LINE_PARTS_FILE


def line_log_sequence_path(vault_path: Path) -> Path:
    return vault_path / LINE_LOG_SEQUENCE_FILE


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


def load_line_log_sequence(vault_path: Path) -> dict:
    path = line_log_sequence_path(vault_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Ignoring unreadable LINE log sequence cache at %s", path)
        return {}


def save_line_log_sequence(vault_path: Path, cache: dict) -> None:
    line_log_sequence_path(vault_path).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_line_log_id(vault_path: Path, now: Optional[datetime] = None) -> str:
    now = now or datetime.now(LINE_LOG_TIMEZONE)
    if now.tzinfo is None:
        now = now.replace(tzinfo=LINE_LOG_TIMEZONE)
    minute_key = now.astimezone(LINE_LOG_TIMEZONE).strftime("%Y%m%d%H%M")
    cache = load_line_log_sequence(vault_path)
    sequence = int(cache.get("sequence", 0)) + 1 if cache.get("minute") == minute_key else 1
    save_line_log_sequence(vault_path, {"minute": minute_key, "sequence": sequence})
    return f"{minute_key}_{sequence:05d}"


def collect_line_message_part(vault_path: Path, text: str) -> Optional[tuple[str, str]]:
    part = parse_line_message_part(text)
    if not part:
        return text, generate_line_log_id(vault_path)

    cache = load_line_parts(vault_path)
    key = f"{part.label}:{part.total}"
    if key not in cache:
        cache[key] = {
            "total": part.total,
            "parts": {},
            "log_id": generate_line_log_id(vault_path),
            "updated_at": time.time(),
        }
    entry = cache[key]
    entry["parts"][str(part.index)] = text
    entry["updated_at"] = time.time()

    expected = {str(index) for index in range(1, part.total + 1)}
    if set(entry["parts"]) != expected:
        save_line_parts(vault_path, cache)
        logger.info("Stored LINE message part %s/%s for %s", part.index, part.total, part.label)
        return None

    merged = "\n\n".join(entry["parts"][str(index)] for index in range(1, part.total + 1))
    log_id = entry["log_id"]
    cache.pop(key, None)
    save_line_parts(vault_path, cache)
    logger.info("Merged %s LINE message parts for %s", part.total, part.label)
    return merged, log_id


async def mark_line_event_as_read(settings, event: LineTextEvent) -> None:
    try:
        marked = await mark_message_as_read(settings.line_channel_access_token, event.mark_as_read_token)
        if marked:
            logger.info("Marked LINE message as read")
    except Exception:
        logger.exception("Failed to mark LINE message as read")


async def capture_line_messages(events: list[LineTextEvent], background_tasks: BackgroundTasks) -> None:
    settings = get_settings()
    logger.info("Processing %s LINE message(s)", len(events))

    try:
        vault_path = await asyncio.to_thread(ensure_vault, settings)
    except Exception:
        logger.exception("Failed to prepare vault repo")
        return

    for event in events:
        text = event.text
        collected = collect_line_message_part(vault_path, text)
        if collected is None:
            continue
        text, log_id = collected

        saved_any_note = False
        urls = extract_urls(text)
        if should_capture_line_message_context(text, settings.max_page_chars):
            try:
                note = await process_line_message_context(settings, text, urls)
                await save_note(settings, vault_path, note, log_id)
                saved_any_note = True
            except Exception:
                logger.exception("Failed to capture LINE pasted message")

        for url in urls:
            try:
                note = await process_url(settings, url, text)
                await save_note(settings, vault_path, note, log_id)
                saved_any_note = True
                logger.info("✅ Captured LINE URL %s", url)
            except Exception:
                logger.exception("Failed to capture LINE URL %s", url)

        if saved_any_note:
            await mark_line_event_as_read(settings, event)

    # NOTE: Phase A (ingest_raw_to_wiki) moved to Mac Mini cron job.
    # See scripts/ingest_wiki.py + run_mac_mini_phase_a.sh
    # LINE → raw/ → GitHub is handled here; wiki entities are
    # processed asynchronously by the Mac Mini every hour.


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
            log_id = generate_line_log_id(vault_path)
            note = await process_url(settings, url, context_text)
            await save_note(settings, vault_path, note, log_id)
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

    background_tasks.add_task(capture_line_messages, events, background_tasks)
    logger.info("Accepted %s LINE message(s) for background processing", len(events))
    return {"ok": True, "accepted": len(events)}
