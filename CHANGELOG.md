# Changelog

All completed implementation reports, one-time analyses, and delivery summaries are consolidated here. Root-level docs only keep active files that need ongoing maintenance.

## 2026-07-09

### Added

- **Resolver Layer — Day 1 (MIGRATION.md Step 4)**:
  - `src/personalkm/resolve/url_extractor.py` — 3-tier URL extraction from raw notes (frontmatter → 原文連結 → 內含連結 → regex fallback), with `extract_all_urls()` for multi-link notes.
  - `src/personalkm/resolve/adapters/github.py` — `GitHubAdapter` fetching repo README via `raw.githubusercontent.com`. Handles root, tree/<ref>, blob/<ref> URLs. 404 → `GoneError`, 403/429 → `AuthWallError`.
  - Package `__init__.py` for `resolve/` and `resolve/adapters/` modules.
- **`resolver/adapters` branch** — feature branch for the 5-day Resolver Layer plan.

### Changed

- `.gitignore` — cleaned up duplicates from merge conflict, added `.omo/` and missing patterns.

## 2026-07-05

### Changed

- **Vault split (MIGRATION.md Step 1)**: Content paths (`raw/ wiki/ Attachments/ Trash/ .obsidian/`) moved to new private repo `github.com/dannytsao/Personalkm-vault`. Code repo history rewritten via `git-filter-repo` (force push). All path references updated (9 shell scripts, 3 Python scripts, 3 launchd plists, Render env vars). Mac Mini launchd reloaded. Full backup created (`pkm-code-backup.bundle` + `pkm-worker-backup`).

## 2026-07-04

### Added

- **LLM router wiring (MIGRATION.md Step 3)**: `bot/ingestion_v2.py`, `scripts/ingestion_job.py`, `bot/query_engine.py` now call `personalkm.llm.router.route()` for all LLM calls instead of `bot/llm_clients.py`. Synthesis and entity/tag extraction in `ingestion_v2.py` are split into two router stages (`ingest_synthesis`, `entity_extraction`) matching `config/models.yaml`'s cost tiering. Query answers use the `query_answer` stage.
- **No more silent LLM fallback**: removed all `skip_llm` degraded-output paths (AGENTS.md rule 3) — `LLMError` now propagates from every call site so a failed raw note stays pending and is retried, instead of producing a low-confidence stub page.
- **SPEC.md** — "PersonalKM — 功能規格文件": functional spec covering the full capture flow and not-yet-implemented features.
- **CHECKLIST.md** — "Karpathy LLM Wiki 入口完成檢查表": 29-item completion checklist gating progress to the Distillation Loop.

### Changed

- Archived 13 stale root-level completion reports/status docs into `docs/archive/` (`SESSION-SUMMARY-2026-06-13.md`, `FINAL-STATUS-2026-06-13.txt`, `IMPLEMENTATION-SUMMARY.txt`, `DECAY-SYSTEM-COMPLETE.txt`, `HERMES-COMPLETE.txt`, `DEPLOYMENT-COMPLETE.md`/`.txt`, `RUNNING-LOGS-AND-RETRY.md`, `INGESTION-IMPROVEMENTS.md`, `QUALITY-FILTERING.md`, `PROJECT-DOCUMENTATION-PROCESS.md`, `DOCS-INVENTORY.md`, `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md`) via `git mv` (history preserved).
- Fast-forwarded `origin/main` from `f4bcc15` to `ced0447` to catch up with `restructure/phase-1-scaffold`'s scaffold + router work; untracked `.DS_Store` from git on `main` in a follow-up commit.

### Housekeeping

- Identified two additional local clones of this repo (`~/Documents/Github/PersonalKM` on `main`, now current; `~/Documents/GitHub/DannyTsao/PersonalKM`, stale since 2026-06-08) — neither is referenced by any documented workflow in `AGENTS.md`.

## 2026-06-28

### Added

- **Capture propagation** (`bot/ingestion_v2.py`): `_propagate_to_entity_pages()` — after each ingest, appends a capture excerpt to every canonical entity page mentioned in the body (1 capture → 10–15 entity page updates). Idempotent: skips duplicates.

- **Sanity check & repair** (`scripts/sanity_check.py`): repair-first vault health checker. Scans all `wiki/entities/` + `wiki/concepts/` pages, repairs fixable frontmatter issues (missing `---` delimiter, nested bracket tags, empty sources, extra non-schema fields), warns on structural problems (type mismatch, auto-promoted stubs). Never deletes files. Idempotent. 73 pages scanned: 57 fixes applied, 41 warnings remain.

- **Query interface** (`scripts/query_wiki.py`): CLI with `--no-llm`, `--json`, `--top-k`, `-i` (interactive REPL) flags. Hybrid search (title exact/prefix/token, frontmatter, body mentions, entity registry); ranked scoring; LLM synthesis with `[[wikilink]]` citations.

- **Web query endpoint**: `GET /query?q=...` on FastAPI (`bot/app.py`), deployed on Render.

### Fixed

- **Render `/query` endpoint**: Added `ensure_vault()` call before search — previously failed with `wiki/ not found` on cold start because vault wasn't cloned.

- **Ingestion cron on Render** (`scripts/ingestion_job.py`): `get_vault_path()` now uses `ensure_vault()` instead of requiring directory to pre-exist — fixes cold-start failure on ephemeral disk.

- **Dirty repo blocking all launchd jobs**: `scripts/ingest_wiki.py` and `bot/app.py` changed `git add wiki/` → `git add --all` so raw file deletions are committed. Changed `git pull --ff-only` → `git pull --rebase` to handle divergent history gracefully. Worker repo cleaned and synced.

- **Root cause — frontmatter cascading bugs**:
  - `bot/ingestion_v2.py` (lines 310/354): replaced `f"tags: {tags}"` with `yaml.dump(tags)` — stops Python repr (single-quoted) being written to YAML, which caused the cascading nested-bracket bug.
  - `bot/entity_dedup.py`: added `if not source_path: return` guard in `add_source_to_frontmatter()` — prevents writing `sources: [""]`.
  - `bot/entity_dedup.py`: fixed `_append_capture()` regex to handle block-style sources (was silently dropping the add) and empty inline `sources: []` → `sources: ["new"]`.

- **Schedule job status verified**: All 5 jobs (Phase A/B/Omnichannel launchd, Render web + cron) confirmed healthy. Last exit codes all 0.

### Changed

- `ensure_vault` now called in `/query` endpoint and ingestion cron for Render ephemeral disk robustness.
- `git add --all` replaces `git add wiki/` in both `scripts/ingest_wiki.py` and `bot/app.py` to capture raw file deletions.

## 2026-06-27

### Fixed

- **Health check false failures** (`bot/ingestion_health_check.py`):
  - Removed `sources/` from `required_dirs` (dir never existed)
  - Moved `contested:`/`confidence:` to `optional_quality_fields` (per SCHEMA.md)
  - Made `knowledge-graph.md` optional (not in SCHEMA.md)
  - Health check now returns `healthy` with 0 failed checks

  Commit: `fb40fa9` — "fix(health-check): align with actual SCHEMA.md"

### Changed

- **CJK slug bug in `extract_title()`** (`bot/ingestion_v2.py`) — `extract_title()` was using `_slugify` from `llm_summarizer.py` which strips all non-ASCII characters. For CJK titles this produced empty strings → filenames like `2026-06-27-.md`. Fixed by replacing `_slugify` with `normalize_entity_name` from `entity_dedup.py` which preserves CJK characters.

  Commit: `2d040b8` — "fix: use normalize_entity_name for title extraction (preserve CJK)"

- **Empty-slug files cleaned up** — `wiki/entities/2026-06-27-.md` and `wiki/concepts/2026-06-27-.md` were renamed to proper CJK slugs. Duplicate entity/concept entries from the double-processing run were deduplicated.

- **Ingestion routing confirmed working** — Phase A manual run processed 55 raw files. Routing to `wiki/entities/` (specific entities, places, people) and `wiki/concepts/` (topics, ideas, how-to) is functioning correctly. Both destinations use `normalize_entity_name` for slug generation.
- Phase A vault is clean (no dirty-repo skip conditions), ready for next hourly launchd trigger.

## 2026-06-23

### Added

- **LLM-Wiki v2** — full 5-phase upgrade to the knowledge ingestion pipeline.

  New `bot/` modules:
  - `llm_summarizer.py` — AI distillation (MiniMax or fallback) + `distill_to_markdown()` + `detect_entity_mentions()`. Replaces long raw transcripts with scannable 300–500 char summaries.
  - `entity_dedup.py` — `EntityRegistry` indexes 323 existing wiki pages. New captures about the same entity are merged into the existing page instead of creating duplicates.
  - `wikilinks.py` — `WikilinkManager` adds bidirectional links. New page → links to entity; entity page → backlink to new page.
  - `ingestion_v2.py` — integrated pipeline wiring all 4 phases together. Runs in Render cron every Saturday 23:00 UTC.

  New scripts:
  - `scripts/migrate_wiki_to_v2.py` — one-time migration of 375 existing wiki pages to distilled format (536,571 chars saved).
  - `scripts/fix_broken_wikilinks.py` — removed orphan wikilinks from 215 wiki files (42,479 chars saved).

  `bot/config.py` — added `MINIMAX_API_KEY` and `MINIMAX_MODEL` environment variables.

- **Phase 2 migration**: all 375 wiki pages now distilled. Bodies reduced ~80–85% while preserving `sources:`, `tags:`, frontmatter. Original content untouched in `raw/`.

- **Phase 3 migration**: entity deduplication index built. 323 entities indexed. Confirmed `claude-code` ↔ `Claude Code` fuzzy matching works.

- **Phase 4 migration**: bidirectional wikilinks active. 0 broken links across 376 wiki files. Health check: **healthy**.

- **`docs/llm-wiki-v2-plan.md`** — full v2 plan with phase specs, exit conditions, rollback plan, and execution log.

### Changed

- `bot/ingestion.py` remains v1 (legacy). v2 lives in `bot/ingestion_v2.py`. Both can coexist during transition.
- Cron schedule shifted from **Sunday 09:00 UTC+8** to **Saturday 23:00 UTC** (Sunday 07:00 UTC+8).
- Ingestion now skips files with `confidence: low` pattern match, empty content, or 404-style content before processing.

### Removed

- `LLM-WIKI-BOT-INTEGRATION-PLAN.md` — superseded by `docs/llm-wiki-v2-plan.md`.
- `LLM-WIKI-DEPLOYMENT-GUIDE.md` — content moved to plan document.
- `OPTION-B-COMPLETE.md` — delivery complete.
- `OPTION-B-SUMMARY.md` — delivery complete.
- `PHASE-4-MONITORING-CHECKLIST.md` — one-time monitoring done.
- `LLMWIKI-INTEGRATION-CHANGENOTE.md` — superseded by this changelog entry.

## 2026-06-11

### Added

- Added Layer 1 URL hygiene before raw note creation.
  - Filters obvious ad/tracking/redirect URLs from LINE messages.
  - Removes common tracking query parameters such as `utm_*`, `fbclid`, `igsh`, and `gclid`.
  - Keeps normal source URLs such as Facebook group permalinks.
- Added `IMPROVEMENT-BACKLOG.md` as the active backlog.
- Added Layer 2 content cleaning to the backlog.
  - Goal: clean ad blocks, recommendation blocks, navigation/footer text, share widgets, and unrelated links from fetched page text before writing `raw/`.
- Added project documentation governance.
  - `DOCS-INVENTORY.md` tracks current docs, owners, purpose, and review cadence.
  - `PROJECT-DOCUMENTATION-PROCESS.md` defines how docs are created, updated, archived, and removed.

### Changed

- Updated `README.md` with 2026-06-11 system status.
- Updated `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md` to include URL hygiene and Layer 2 content cleaning status.

## 2026-06-10

### Added

- Added Mac mini omnichannel worker.
  - Render writes partial or blocked notes into `raw/` with queue metadata.
  - GitHub repo acts as durable queue.
  - Mac mini worker uses local tools for enrichment when the machine is available.
- Added worker queue metadata to legacy raw notes.
  - `needs_local_worker`
  - `worker_status`
  - `worker_type`
  - `worker_retry_count`
- Added launchd automation for Mac mini worker every 15 minutes.
- Added worker documentation at `docs/mac-mini-omnichannel-worker.md`.

### Changed

- Current architecture became: Render LINE Bot + GitHub durable queue + Obsidian Git + Mac mini local worker.
- YouTube local recovery now prioritizes `yt-dlp` subtitles, then `whisper.cpp` transcription when needed, then Ollama summary generation.

### Removed From Root Docs

- `TOMORROW-ACTION-PLAN-2026-06-10.md`
  - Outcome captured by current worker docs and system requirements document.

## 2026-06-09

### Changed

- Fixed capture time basis to Asia/Taipei.
- Added `threads.com` and `www.threads.com` platform routing.
- Confirmed LINE bot capture, GitHub push, and Obsidian sync path.
- Established `call it a day` wrap-up practice in `AGENTS.md`.

## 2026-06-08

### Added

- Added canonical Markdown normalization for URLs, social posts, Google AI Mode pasted text, and long LINE text.
- Added `log_id` tracking for each LINE capture.
- Added multipart long-text merge support, such as `[文章 1/3]`.
- Added LINE mark-as-read after successful repo write.

### Changed

- Render service moved to Starter plan to avoid Free plan idle spin down.
- Google AI Mode share links are no longer hard-fetched when blocked or rate limited.
- Full pasted LINE text is saved before processing contained URLs.

## 2026-06-07

### Added

- Implemented Phase 1 + Phase 4 of the raw/wiki/outputs system.
  - `raw/` became the capture area.
  - `wiki/` became the organized knowledge area.
  - `outputs/` became the report area.
  - Weekly ingestion organizes `raw/` into `wiki/`.
- Migrated old `Inbox/` notes into `Archive/inbox-history-before-2026-06-07/`.
- Added YouTube summary enhancement from short generic summaries to structured bullet points.
- Added knowledge decay detection concept and monthly report workflow.
- Added health-check and recovery design for notes that are missing, partial, generic, or blocked.

### Changed

- Replaced the old `Inbox/`-first flow with `raw/` as the primary capture layer.
- Documented why `raw/` and `Inbox/` should not be treated as the same concept.

### Removed From Root Docs

These completed implementation reports and decision drafts were consolidated into this changelog:

- `00-README-PHASE-1-4.md`
- `ANALYSIS-COMPLETE-DECISION-TIME.md`
- `ARCHIVE-STRATEGY.md`
- `COMPARISON-KARPATHY-VS-PERSONALKM.md`
- `DEBUG-YOUTUBE-NOT-FOUND.md`
- `DEPLOYMENT-CHECKLIST.md`
- `DEPLOYMENT-COMPLETE.md`
- `ENHANCEMENT-ANALYSIS.md`
- `ENHANCEMENT-DECISION.md`
- `HEALTH-CHECK-SYSTEM.md`
- `IMPLEMENTATION-DELIVERY.md`
- `INBOX-MIGRATION-LOG.md`
- `KARPATHY-ENHANCEMENT-SUMMARY.md`
- `PHASE-1-4-COMPLETE.md`
- `PHASE-1-4-ROADMAP.md`
- `PREVENTION-SYSTEM-COMPLETE.md`
- `QUICK-REFERENCE.md`
- `SYSTEM-SUMMARY.md`
- `TODAY-SUMMARY-2026-06-07.md`
- `UNIVERSAL-HEALTH-CHECK-v2.md`
- `UNIVERSAL-SYSTEM-COMPLETE.md`
- `WHY-RAW-NOT-INBOX.md`
- `YOUTUBE-SUMMARY-ENHANCEMENT.md`

## 2026-06-06

### Added

- Added initial AI enrichment workflow with OpenAI.
- Added initial knowledge decay report prototype.

### Removed From Root Docs

- `TEST-decay-report.md`
  - Temporary generated report; not needed as a maintained project document.
