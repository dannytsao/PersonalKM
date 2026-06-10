# Mac mini Omnichannel Markdown Worker

This worker lets the repo act as the durable queue. Render writes partial or blocked notes into `raw/`, and Mac mini can enrich them later when it is online.

## Required Tools

- `git`
- `ffmpeg`
- `yt-dlp`
- `ollama`
- Optional: `whisper.cpp` or `faster-whisper` for local audio transcription

## Ollama Model

Start with:

```bash
ollama pull qwen3:8b
```

If the Mac mini has 24 GB or 32 GB RAM, test this after the 8B path is stable:

```bash
ollama pull qwen3:14b
```

Optional lightweight fallback:

```bash
ollama pull gemma3:4b
```

## Manual Run

From the repo root:

```bash
python3 -m tools.omnichannel_md.worker --dry-run
```

Backfill worker metadata into legacy raw notes:

```bash
python3 -m tools.omnichannel_md.backfill_worker_metadata
python3 -m tools.omnichannel_md.backfill_worker_metadata --apply
```

Process one pending note without Git automation:

```bash
python3 -m tools.omnichannel_md.worker --process-one --no-git
```

Process a specific pending note by `log_id`:

```bash
python3 -m tools.omnichannel_md.worker --process-one --log-id 202606101106_00001 --no-git
```

Process one pending note with Git pull/rebase, commit, and push:

```bash
python3 -m tools.omnichannel_md.worker --process-one
```

## Queue Contract

Pending notes use frontmatter like:

```yaml
needs_local_worker: true
worker_status: pending
worker_type: omnichannel_md
worker_retry_count: 0
```

Successful enrichment changes the note to:

```yaml
extraction_status: ok
needs_review: false
needs_local_worker: false
worker_status: done
worker_type: omnichannel_md
worker_processed_at: 2026-06-10T10:00:00+08:00
worker_name: mac-mini-omnichannel
```

Failures stay visible in the repo:

```yaml
needs_local_worker: true
worker_status: failed
worker_error: yt_dlp_not_installed;whisper_transcription_not_configured
worker_retry_count: 1
```

## Launchd

Add `launchd` only after manual processing is stable. The worker is intentionally manual-first so it cannot rewrite many historical notes before the single-note path is proven.

## 2026-06-10 Implementation Status

- Render-side note generation now writes worker queue metadata for new notes.
- The repo scanner can find both new explicit pending notes and older legacy partial/blocked notes.
- Dry-run has been verified against the current repo.
- Whisper fallback is now wired into the worker. If YouTube subtitles fail, the worker downloads audio with `yt-dlp`, transcribes it with `whisper-cli`, then summarizes with Ollama.
- Local Whisper model path: `~/.cache/personalkm/whisper/ggml-base.bin`.
- One real YouTube partial note was recovered in `--process-one --no-git` mode and updated to `extraction_status: ok`.
- One earlier YouTube note remains marked `worker_status: failed`, which verifies failures stay visible instead of being silently ignored.

Local setup commands:

```bash
brew install ffmpeg yt-dlp
brew install whisper-cpp
ollama pull qwen3:8b
```

After those tools are ready, rerun:

```bash
python3 -m tools.omnichannel_md.worker --process-one --no-git
```
