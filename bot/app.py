import asyncio
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request

from bot.config import get_settings
from bot.git_store import commit_and_push, ensure_vault
from bot.line import extract_urls, text_messages_from_webhook, verify_line_signature
from bot.link_processor import process_url
from bot.notes import write_note


app = FastAPI(title="Personal KM LINE Link Bot")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/line")
async def line_webhook(request: Request, x_line_signature: Optional[str] = Header(default=None)) -> dict:
    settings = get_settings()
    body = await request.body()
    if not verify_line_signature(body, settings.line_channel_secret, x_line_signature):
        raise HTTPException(status_code=401, detail="Invalid LINE signature")

    payload = await request.json()
    urls: list[str] = []
    for text in text_messages_from_webhook(payload):
        urls.extend(extract_urls(text))

    if not urls:
        return {"ok": True, "processed": 0}

    vault_path = ensure_vault(settings)
    processed = []
    for url in urls:
        note = await process_url(settings, url)
        note_path = write_note(vault_path, settings.inbox_dir, note)
        await asyncio.to_thread(commit_and_push, settings, note_path)
        processed.append({"url": url, "note": str(note_path.relative_to(vault_path))})

    return {"ok": True, "processed": len(processed), "notes": processed}
