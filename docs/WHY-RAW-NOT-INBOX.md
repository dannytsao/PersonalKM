# Why Raw, Not Inbox

**Status:** Design rationale (restored 2026-07-07 after vault split orphaned the original)
**Author:** Original lost in git-filter-repo rewrite; content reconstructed from project conventions.

---

## The Question

When a LINE message comes in, should the note land in an `Inbox/` folder (to be triaged later) or go straight to `raw/` (to await weekly ingestion)?

## Decision: `raw/` Always

Incoming notes go directly to `raw/<Category>/<date>-<seq>-<slug>.md`. No inbox staging.

## Rationale

| Factor | Inbox approach | Raw approach (chosen) |
|--------|---------------|----------------------|
| **Capture latency** | Note sits in Inbox until triaged | Immediately available for ingestion |
| **Lineage** | Multiple moves (Inbox → raw → wiki) | Single hop (raw → wiki) |
| **Idempotency** | Must check both Inbox and raw for duplicates | Single source of truth |
| **User mental model** | "I need to do something with this" | "System will handle it automatically" |
| **Failure mode** | Inbox fills up, notes are forgotten | Weekly ingestion processes everything |

## How It Works

```
LINE message
  ↓
Render webhook → raw/<Category>/<date>-<slug>.md
  ↓
(Git commit + push to vault repo)
  ↓
Mac Mini launchd (hourly) pulls vault
  ↓
Weekly ingestion (Sunday/Monday):
  ├── scan raw/
  ├── LLM synthesis → wiki/entity or wiki/concept
  └── raw/ → archive/ (processed)
```

There is no manual triage step. Every raw note is automatically ingested on the next weekly cycle. Notes with quality problems (partial extraction, empty summary) are flagged by the pre-ingestion health check (`src/personalkm/ingest/health_check.py`) but are still processed — the pipeline attempts LLM synthesis regardless.

## Edge Cases

- **Low-quality notes** (e.g. Instagram without extraction): Classified by `ContentQualityChecker` during ingestion, moved to `archive/` instead of wiki.
- **Platform-blocked**: Flagged as `LOW` in the health check. Not auto-repairable. May produce a low-confidence wiki page.
- **Duplicates**: Handled by the LLM synthesis step — if the same URL appears again, the ingestion pipeline's entity matching consolidates into the existing canonical page.

## Why Not Both?

A two-stage system (Inbox → raw → wiki) adds complexity (two directories to check, two move operations) without clear benefit for this project's use case. The user's flow is "capture and forget" — the system handles everything after the LINE message arrives.