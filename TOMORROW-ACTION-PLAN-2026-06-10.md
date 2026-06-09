# 2026-06-10 Action Plan: Repo Queue + Mac mini Omnichannel Markdown Worker

## Goal

Build the next step of PersonalKM so Render keeps acting as the reliable LINE receiver, while the repo becomes the durable queue for Mac mini local enrichment. Mac mini may be offline, so every task must be recoverable from GitHub after the machine comes back online.

## Target Architecture

```text
LINE message / URL / pasted text
  -> Render LINE Bot
  -> raw/*.md with queue metadata in YAML
  -> GitHub repo as durable queue
  -> Mac mini worker pulls repo when online
  -> local extractors: yt-dlp / Whisper / Ollama
  -> canonical Markdown update
  -> commit + push back to GitHub
  -> Obsidian sync
```

## Action Items In Sequence

1. Define the repo queue contract in YAML.
   - Add fields for `needs_local_worker`, `worker_status`, `worker_type`, `worker_retry_count`, `worker_error`, `worker_processed_at`, and `worker_name`.
   - Keep existing `log_id`, `extraction_status`, `needs_review`, `platform`, and `content_type`.
   - Make the contract work without a separate database or Render local storage.

2. Update Render-side note generation.
   - When a note is fully captured, set `needs_local_worker: false` and `worker_status: not_required`.
   - When YouTube/social content is partial or blocked, set `needs_local_worker: true` and `worker_status: pending`.
   - Preserve the same `log_id` across original LINE message notes and derived URL notes.

3. Add tests for queue metadata.
   - Verify partial YouTube notes are marked pending for local worker.
   - Verify normal web notes are not unnecessarily queued.
   - Verify canonical Markdown still renders stable YAML and body sections.

4. Create the Mac mini worker scaffold.
   - Add `tools/omnichannel_md/`.
   - Add a scanner that finds notes with `needs_local_worker: true` and `worker_status: pending`.
   - Start read-only first: list candidate files and log planned actions without modifying notes.

5. Implement safe Git workflow for the worker.
   - `git pull --rebase origin main` before processing.
   - Process one note at a time.
   - Commit each successful enrichment or small batch with a clear message.
   - Push after commit.
   - If push fails, rebase and retry without overwriting user or Render changes.

6. Implement YouTube recovery first.
   - Try existing subtitle endpoint.
   - Try YouTube watch-page caption tracks.
   - Try `yt-dlp` subtitles.
   - If no subtitle is available, prepare the hook for local audio transcription with Whisper.
   - Keep download/transcription on Mac mini only, not Render.

7. Add Ollama summarization adapter.
   - Use Ollama only after raw text or transcript exists.
   - Default model: `qwen3:8b`.
   - If Mac mini has 24 GB or 32 GB RAM, test `qwen3:14b` after the 8B path is stable.
   - Keep `gemma3:4b` as an optional lightweight fallback model.
   - Generate summary, key points, tags/category, and canonical Markdown sections.
   - Fall back to deterministic local summary if Ollama is unavailable.

8. Update the note in place.
   - Keep filename and `log_id` stable.
   - Replace weak fallback original content with recovered transcript/content.
   - Set `extraction_status: ok` on success.
   - Set `needs_local_worker: false`, `worker_status: done`, `worker_processed_at`, and `worker_name: mac-mini-omnichannel`.

9. Handle failures explicitly.
   - On recoverable failure, increment `worker_retry_count`.
   - Set `worker_status: failed` only after a clear failure reason is known.
   - Preserve the original note and source URL.
   - Never delete queue metadata unless the note is successfully enriched.

10. Add Mac mini launch instructions.
    - Document required tools: `git`, `ffmpeg`, `yt-dlp`, `ollama`, and Whisper option.
    - Add a simple launch command for manual execution first.
    - Add `launchd` automation only after manual workflow is stable.

11. Run verification.
    - Run relevant unit tests.
    - Run worker in dry-run mode against current partial YouTube notes.
    - Process one real partial YouTube note end to end.
    - Confirm the updated note appears correctly in Obsidian.
    - Confirm Render `/health` remains OK.

12. Commit and push.
    - Commit code, tests, and documentation.
    - Push to `origin/main`.
    - Confirm `HEAD == origin/main`.

## Acceptance Criteria

- Render can persist partial/blocked work into the repo without relying on Render local filesystem.
- Mac mini can be offline without losing any tasks.
- Mac mini can later discover pending work from repo metadata.
- At least one partial YouTube note can be recovered or marked with a precise failure reason.
- Canonical Markdown remains consistent for Obsidian.
- The workflow keeps cost low by avoiding paid transcription unless explicitly enabled later.

## Ollama Model Decision

- Start with `qwen3:8b` as the default model for the Mac mini worker.
- Prefer Qwen3 because the worker needs Chinese/English mixed summarization, instruction following, and canonical Markdown generation.
- If Mac mini memory allows, compare `qwen3:14b` for higher quality after the end-to-end worker is stable.
- Keep `gemma3:4b` as a fast fallback only; do not make it the primary summarization model.
- Do not start with larger models such as `qwen3:30b` or `gpt-oss:20b` until the queue, scanner, and single-note recovery flow are proven.

## Non-goals For Tomorrow

- Do not replace the Render LINE bot.
- Do not add a paid database, Redis, or Render persistent disk.
- Do not require Mac mini to be always on.
- Do not make Whisper/API transcription mandatory on day one.
- Do not rewrite all historical notes in bulk before the single-note recovery path is proven.
