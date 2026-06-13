# Content Quality Filtering — Automated Trash System

**Added:** 2026-06-13 (Post Sunday 07:00 UTC+8:00 Scheduling)  
**Status:** ✅ ACTIVE IN PRODUCTION

---

## What's the Problem?

Raw notes captured from LINE contain many stub/placeholder files:
- Reddit "waiting for verification" pages
- Incomplete captures (< 100 characters)
- Pages that failed to load properly
- Placeholder summaries like "loading..." or "no content"

These 11 files (3.9% of raw/) add noise to the wiki without meaningful content.

---

## The Solution: ContentQualityChecker

### Minimum Content Requirements

Every raw file must pass **ALL** of these checks to be ingested:

| Check | Requirement | Reason |
|-------|-------------|--------|
| Body length | ≥ 100 characters | Ensures meaningful content |
| Body lines | ≥ 3 non-empty lines | Prevents one-liners |
| Summary length | ≥ 30 characters | Summary must be informative |
| No low-quality patterns | Match against 11 patterns | Detects stubs/errors |
| No incomplete summaries | Match against 7 patterns | Detects placeholders |

### Low-Quality Pattern Detection

**Stub/Error Patterns (11 total):**
- `等待驗證` (waiting for verification - Chinese)
- `please wait for verification` (English)
- `正在加載` (loading - Chinese)
- `loading` (English)
- `no content`, `empty page`, `error loading`
- `page not found`, `not found`, `404`, `access denied`
- `このページは` (this page - Japanese)

**Incomplete Summary Patterns (7 total):**
- `placeholder`, `stub`, `incomplete`
- `沒有提供具體` (no concrete info provided - Chinese)
- `沒有具體` (no concrete - Chinese)
- `無法獲取` (unable to fetch - Chinese)
- `暫時無法` (temporarily unable - Chinese)

### Processing Flow

```
raw/*.md
       ↓
[ContentQualityChecker]
    /          \
  PASS        FAIL
   ↓            ↓
wiki/     archive/  (archived, not deleted)
          + logged in wiki/log.md
          + reported in ingestion results
```

---

## Current Results

**Scan of all 284 raw files:**

```
Total files: 284
Low-quality (to trash): 11 files (3.9%)
High-quality (to keep): 273 files (96.1%)
```

### Files Being Trashed

1. `2026-06-13...reddit-please-wait-for-verification.md` — "please wait for verification"
2. `2026-06-10...reddit-please-wait-for-verification.md` — "等待驗證"
3. `2026-06-08-reddit-please-wait-for-verification.md` — "等待驗證"
4. `2026-06-10...reddit-please-wait-for-verification.md` — "等待驗證"
5. `2026-06-08-x-twitter-post.md` — Body too short (85 chars, min 100)
6. `2026-06-07...銀河季開跑!...md` — Summary too short (9 chars, min 30)
7. `2026-06-13...obsidian-with-ollama.md` — "loading" pattern
8. `2026-06-13...reddit-please-wait-for-verification.md` — "please wait for verification"
9. `2026-06-08-youtube.md` — Body too short (98 chars, min 100)
10. `2026-06-08-reddit-please-wait-for-verification.md` — "please wait for verification"
11. (1 additional file) — Similar pattern

---

## Implementation Details

### Code Changes

**New Class:** `ContentQualityChecker` (ingestion_wiki_helpers.py)
- Static methods for robustness
- Supports multilingual pattern detection
- Returns tuple: (is_low_quality: bool, reason: str)

**Updated Function:** `ingest_raw_to_wiki()` (ingestion.py)
- Quality check happens BEFORE ingestion
- Failed files moved to archive/ (not deleted)
- Tracked variables: `trashed`, `trashed_files`
- Reported in ingestion results + wiki/log.md

**Updated Script:** `ingestion_job.py`
- Displays trashed count in job logs
- Reports in outputs/ingestion-reports/

### Safety Features

1. **No data loss:** Files moved to archive/, not deleted
2. **Traceable:** All trashed files logged with reasons
3. **Reversible:** Can restore from archive/ if needed
4. **Configurable:** Thresholds in ContentQualityChecker class
5. **Auditable:** Full audit trail in wiki/log.md

---

## How to Use

### Default Behavior (Automatic)

Every Sunday at 07:00 UTC+8:00 (Saturday 23:00 UTC):
1. Cron job runs ingestion
2. ContentQualityChecker filters raw files
3. Low-quality files → archive/
4. High-quality files → wiki/ (normal flow)
5. Report includes trashed count

### Check Quality Manually

```python
from bot.ingestion_wiki_helpers import ContentQualityChecker
from pathlib import Path

file_path = Path("raw/Some/note.md")
is_low_quality, reason = ContentQualityChecker.is_low_quality(file_path)

if is_low_quality:
    print(f"Would trash: {reason}")
else:
    print("Would keep")
```

### Customize Thresholds

Edit ingestion_wiki_helpers.py, ContentQualityChecker class:

```python
MIN_BODY_CHARS = 100  # Change this
MIN_BODY_LINES = 3    # Or this
MIN_SUMMARY_CHARS = 30  # Or this
```

### Add Custom Patterns

Edit lists in ContentQualityChecker:

```python
LOW_QUALITY_PATTERNS = [
    r'your-pattern-here',
    r'another-pattern',
]
```

---

## Ingestion Results Format

**New fields in ingestion result dict:**

```json
{
  "status": "success",
  "processed": 273,
  "trashed": 11,
  "failed": 0,
  "total": 284,
  "created_pages": [...],
  "trashed_files": [
    "2026-06-13...reddit-please-wait-for-verification.md",
    "..."
  ],
  "timestamp": "2026-06-13T23:00:00",
  "graph_updated": true,
  "index_updated": true,
  "log_updated": true
}
```

---

## Expected Behavior (Next Sunday 07:00 UTC+8:00)

**Ingestion run will:**
1. ✅ Scan all 284 raw files
2. ✅ Identify 11 low-quality stubs
3. ✅ Move them to archive/
4. ✅ Process 273 high-quality files
5. ✅ Update wiki/ with valid content
6. ✅ Log audit trail: "11 notes trashed (low-quality)"
7. ✅ Generate report with counts

**Result visible in:**
- Render logs: trashed count
- outputs/ingestion-reports/ingestion-YYYY-MM-DD.md
- wiki/log.md: audit entry
- archive/: moved stub files

---

## FAQ

**Q: What if I want to keep a trashed file?**  
A: It's in archive/. Manually move it back to raw/ before next ingestion.

**Q: Can I make thresholds stricter/looser?**  
A: Yes, edit ContentQualityChecker in ingestion_wiki_helpers.py.

**Q: Does this lose data?**  
A: No. All trashed files are archived (not deleted).

**Q: How often does this check run?**  
A: Every Sunday 07:00 UTC+8:00 during the weekly ingestion cron job.

**Q: Can I disable it?**  
A: Yes, comment out the quality check in ingest_raw_to_wiki():
```python
# if is_low_quality: ... (comment out)
```

**Q: What about existing wiki pages?**  
A: Only affects new ingestion from raw/. Existing wiki/ pages untouched.

---

## Technical Details

**Files Modified:**
- `bot/ingestion_wiki_helpers.py` (+130 lines, new ContentQualityChecker class)
- `bot/ingestion.py` (+25 lines, quality filtering logic)
- `scripts/ingestion_job.py` (+1 line, report trashed count)

**Commit:** `feat: add content quality checking - auto-trash low-quality notes`

**Backward Compatibility:** ✅ 100% — Existing ingested content unaffected

---

## Summary

✅ **Automated quality filtering active**  
✅ **11 stub files identified and will be archived**  
✅ **Zero data loss (all files archived, not deleted)**  
✅ **Full audit trail (logged + reported)**  
✅ **Production ready**

**Next ingestion:** Sunday 2026-06-15 at 07:00 UTC+8:00  
**Result:** 273 quality files ingested, 11 stubs archived, 0 data loss
