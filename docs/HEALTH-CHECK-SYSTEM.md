# 🏥 PersonalKM Note Health Check & Auto-Recovery System

**Purpose:** Periodically scan raw notes for quality issues and auto-repair what can be fixed.
**Schedule:** Every Tuesday 10:00 AM (UTC+8) — `personalkm-health-check` cron job.
**Status:** ⚠️ Needs path/API update — currently blocked on OpenRouter token limits (see [Recovery](#recovery)).

---

## Why This Exists

Raw notes captured via LINE Bot can have quality issues before they're ingested into the wiki:

| Problem | Cause | Impact |
|---------|-------|--------|
| `extraction_status: partial` | Network/API failure during fetch | Incomplete content — user sees broken notes |
| Generic summary ("此連結標題...") | YouTube transcript fetch failed, AI guessed | Useless summary, no real value |
| `summary: ""` | AI generation failed | No summary at all |
| `tags: []` | Tag generation skipped | Note won't be found by tag search |
| `extraction_status: blocked` | Platform requires login (Instagram/TikTok) | Can't auto-extract — needs manual review |

These are **pre-ingestion** quality problems — they happen after capture but before weekly wiki ingestion (`raw/ → wiki/` transformation). The existing `bot/ingestion_health_check.py` only checks **post-ingestion** wiki integrity, not raw note quality.

---

## What It Checks

| # | Check | Auto-Repairable? | Severity |
|---|-------|-----------------|----------|
| 1 | `extraction_status: partial` | ✅ Retry fetch | HIGH |
| 2 | `extraction_status: error` | ✅ Retry fetch | HIGH |
| 3 | `summary: ""` (empty) | ✅ Generate via LLM | HIGH |
| 4 | Generic summary (pattern match) | ✅ Replace with 5-point summary | MEDIUM |
| 5 | `tags: []` (missing) | ✅ Infer from content | MEDIUM |
| 6 | `extraction_status: blocked` | ❌ Manual review only | LOW |
| 7 | YouTube no transcript | ⚠️ Improved summary (no source content) | MEDIUM |

---

## Architecture

### Scripts (at `~/.hermes/scripts/`)

```
~/.hermes/scripts/
├── health-check.py              # Main scanner + reporter
│   └── HealthCheckReport        # Scans raw/ notes, classifies issues
├── universal-health-check.py    # Enhanced v2 with platform-specific analyzers
│   ├── PlatformAnalyzer         # Per-platform rules (YouTube, Instagram, etc.)
│   └── UniversalHealthCheck     # Full scan + auto-repair orchestrator
└── weekly-health-check.py       # Cron entry point
```

### Data Flow

```
LINE Bot captures → raw/*.md
       ↓
(Tuesday 10:00 AM) Health Check
  ├── Scan all raw/ notes
  ├── Detect quality issues (7 types)
  ├── Auto-repair where possible via LLM
  └── Save report to outputs/health-reports/
       ↓
(Sunday weekly ingestion) raw/ → wiki/
  ├── bot/ingestion_health_check.py verifies wiki integrity
  └── Both checks are complementary
```

### Relation to Existing Code

| Component | Scope | When | In Repo? |
|-----------|-------|------|----------|
| `personalkm-health-check` (cron) | **raw/** note quality | Weekly Tuesday | ❌ Scripts only in `~/.hermes/scripts/` |
| `bot/ingestion_health_check.py` | **wiki/** integrity | Post-ingestion | ✅ `IngestionHealthCheck` class |
| `scripts/sanity_check.py` | **wiki/** frontmatter repair | On-demand | ✅ Repair script |

The cron job is **not redundant** — it covers raw note quality which neither `ingestion_health_check.py` nor `sanity_check.py` addresses.

---

## Cron Job Details

```
Name:       personalkm-health-check
Job ID:     1b058c7b65a9
Schedule:   0 10 * * 2 (Tuesday 10:00 AM UTC+8)
Toolsets:   terminal
Created:    2026-06-07
```

### Current Status

| Run | Result | Reason |
|-----|--------|--------|
| 2026-07-07 | ❌ Failed | HTTP 402 — OpenRouter credits insufficient (requested 65k tokens, can only afford 8k) |
| 2026-06-30 | ❌ Likely failed | Same issue |
| 2026-06-09 (first auto-run) | ❌ Likely failed | Same issue |

The job has been **blocked since creation** because:
1. It inherits the session's OpenRouter provider with a high `max_tokens` (65k)
2. OpenRouter credits are insufficient
3. No per-job model override was set

---

## Recovery

To fix this cron job, either:

1. **Pin a cheaper model** on the job (e.g. `openai/gpt-4o-mini` with low `max_tokens`)
2. **Reduce `max_tokens`** for the inherited OpenRouter model
3. **Top up OpenRouter credits**

Alternatively, integrate the health check logic into the existing weekly ingestion pipeline (`src/personalkm/ingest/`) as a step that runs alongside `bot/ingestion_health_check.py` — eliminating the need for a separate cron job entirely.

---

## History

| Date | Event |
|------|-------|
| 2026-06-07 | Created cron job + scripts + design doc `HEALTH-CHECK-SYSTEM.md` (lost in vault split) |
| 2026-06-07 | Enhanced version `universal-health-check.py` created |
| 2026-07-05 | Vault split: code→`/GitHub/DannyTsao/PersonalKM`, vault→`/Personalkm-vault` — docs were orphaned |
| Now | Docs re-created here. Scripts remain at `~/.hermes/scripts/`. Job blocked on OpenRouter credits. |

---

## Seeing the Health Report

```bash
# List health reports (if any were generated)
ls ~/Documents/PersonalKM/Personalkm-vault/outputs/health-reports/

# Read latest
cat ~/Documents/PersonalKM/Personalkm-vault/outputs/health-reports/health-check-*.txt
```

> Note: Reports are saved to the vault path because they're knowledge artifacts, not code.