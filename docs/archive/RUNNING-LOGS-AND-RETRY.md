# Running Logs & Auto-Retry System

**Added:** 2026-06-13 23:00 UTC (After quality filtering + cron setup)  
**Status:** ✅ PRODUCTION READY

---

## Problem Solved

### Issue 1: No visibility into ingestion progress
- Cron jobs run silently (no real-time feedback)
- Errors only visible in Render logs (hard to inspect)
- Can't see exactly where/when failures occur
- No audit trail of what happened during ingestion

### Issue 2: Intermittent API failures
- If OpenAI API temporarily unavailable → entire job fails
- No automatic recovery or retry logic
- User has to manually re-run next week (or wait)
- No indication of how long to wait before retrying

---

## Solution: Two-Part System

### Part 1: Running Log (Real-Time Progress Tracking)

**What it does:**
- Records every step of the ingestion process
- Includes timestamps and elapsed time
- Tracks success/warnings/errors
- Creates timestamped log files in outputs/ingestion-logs/

**Log file format:**
```
outputs/ingestion-logs/ingestion-YYYY-MM-DD-HHMMSS.log
```

**Example log contents:**
```
================================================================================
Ingestion Log Started: 2026-06-13T21:59:42.441685
Job Type: ingestion
================================================================================

[21:59:42 +0.0s] [INIT   ] INIT — Starting ingestion process
[21:59:42 +0.1s] [✅ OK   ] CHECK — Checking raw/ folder: vault/raw
[21:59:42 +0.1s] [✅ OK   ] INIT_SCHEMA — Loading wiki schema
[21:59:42 +0.1s] [✅ OK   ] INIT_INDEX — Loading wiki index
[21:59:42 +0.1s] [✅ OK   ] INIT_LOG — Loading wiki log
[21:59:42 +0.1s] [✅ OK   ] SCAN — Found 284 files
[21:59:42 +0.3s] [✅ OK   ] FILTER — Filtered 11 low-quality files
[21:59:42 +0.6s] [✅ OK   ] PROCESS — Processing 273 files
[21:59:43 +0.7s] [✅ OK   ] GRAPH — Knowledge graph updated
[21:59:43 +0.7s] [✅ OK   ] SAVE_INDEX — Wiki index saved
[21:59:43 +0.7s] [✅ OK   ] SAVE_LOG — Wiki log saved

================================================================================
Ingestion Log Finished: 2026-06-13T21:59:43.162870
Result: success
Processed: 273
Trashed: 11
Failed: 0
Log File: outputs/ingestion-logs/ingestion-2026-06-13-215942.log
================================================================================
```

### Part 2: Auto-Retry Mechanism (Resilience)

**What it does:**
- Checks OpenAI client availability before starting
- If unavailable, waits and retries
- Automatic retry up to 10 times with increasing delays
- Total retry window: ~100 minutes
- Logs each attempt and wait time

**Retry strategy:**
```
Attempt 1: Immediate check
Attempt 2: Wait 5 minutes, try again
Attempt 3: Wait 10 minutes, try again
Attempt 4: Wait 10 minutes, try again
...
Attempt 10: Wait 10 minutes, try again
Total: ~100 minutes of retry window

If client available anytime during retry:
  → Ingestion proceeds immediately
  → Full audit trail of retry history in log
```

---

## How It Works

### Ingestion Flow with Logging

```
ingestion_job.py starts
    ↓
Check OpenAI client availability
    ├─ AVAILABLE → proceed to ingestion
    └─ UNAVAILABLE → auto-retry (5-10 min delays)
        ├─ After 10 retries: FAIL with message
        └─ When available: proceed to ingestion
    ↓
RunningLog initialized
    ↓
ingest_raw_to_wiki() starts
    ├─ INIT: Initialize schema/index/log
    ├─ SCAN: Find raw files
    ├─ FILTER: Quality check (trash low-quality)
    ├─ PROCESS: Ingest each file
    ├─ GRAPH: Build knowledge graph
    └─ SAVE: Update index/log
    ↓
Each step logged with:
    - Timestamp
    - Elapsed time since start
    - Status (✅ OK / ⚠️ WARN / ❌ ERROR)
    - Details message
    ↓
RunningLog finished (with summary)
    ↓
Report saved to outputs/ingestion-reports/
    ↓
Log file saved to outputs/ingestion-logs/
```

---

## Log File Locations

### Running Logs (Per Ingestion)

```
outputs/ingestion-logs/
├── ingestion-2026-06-15-070000.log   (Week 1)
├── ingestion-2026-06-22-070000.log   (Week 2)
├── ingestion-2026-06-29-070000.log   (Week 3)
└── ...
```

Each file is timestamped: `ingestion-YYYY-MM-DD-HHMMSS.log`

### Ingestion Reports (Per Day, Summary)

```
outputs/ingestion-reports/
├── ingestion-2026-06-15.md
├── ingestion-2026-06-22.md
├── ingestion-2026-06-29.md
└── ...
```

Each file covers one day's ingestion with summary metrics.

### Comparison

| Log Type | Purpose | Location | Frequency |
|----------|---------|----------|-----------|
| Running Log | Real-time progress + detailed steps | ingestion-logs/ | Per ingestion (1/week) |
| Ingestion Report | Summary metrics + results | ingestion-reports/ | Per ingestion (1/week) |
| Wiki Log | Integration with wiki audit trail | wiki/log.md | On each ingest (grows) |

---

## Retry Configuration

### Current Settings

```python
MAX_RETRIES = 10           # Up to 10 retry attempts
RETRY_WAIT = 600           # 10 minutes between retries
MIN_WAIT = 300             # 5 minutes before first retry
```

### Total Retry Window

```
First attempt: Immediate
Attempts 2-10: Every 10 minutes
Total: Up to ~100 minutes

Example timeline:
  00:00 - Start job, check client
  00:00 - Client unavailable
  05:00 - Retry 1: still unavailable
  15:00 - Retry 2: still unavailable
  ...
  100:00 - Retry 10: FAIL if still unavailable
```

### How to Customize

Edit `scripts/ingestion_job.py`:

```python
# Retry configuration
MAX_RETRIES = 10  # Change this (0 = no retry)
RETRY_WAIT = 600  # Change this (seconds)
MIN_WAIT = 300    # Change this (seconds)
```

---

## Usage Examples

### View Running Log (After Ingestion)

```bash
# See most recent ingestion log
tail -f outputs/ingestion-logs/ingestion-*.log

# Search for errors in logs
grep -n "ERROR\|WARN" outputs/ingestion-logs/ingestion-*.log

# View specific day's log
cat outputs/ingestion-logs/ingestion-2026-06-15-*.log
```

### Monitor Retry Attempts

When running locally or in Render logs, you'll see:

```
📡 Checking OpenAI client connectivity (attempt 1/11)
✅ OpenAI client is available
✅ Client available, starting ingestion...

# OR if client unavailable:

📡 Checking OpenAI client connectivity (attempt 1/11)
⚠️ Client not available, retrying in 5 minutes...
[wait 5 minutes]
📡 Checking OpenAI client connectivity (attempt 2/11)
⚠️ Client not available, retrying in 10 minutes...
[wait 10 minutes]
📡 Checking OpenAI client connectivity (attempt 3/11)
✅ OpenAI client is available
✅ Client available, starting ingestion...
```

### Check Ingestion Results

```bash
# View report summary
cat outputs/ingestion-reports/ingestion-2026-06-15.md

# Check log file path
grep "Running log:" <report_file>

# See full running log
cat outputs/ingestion-logs/ingestion-2026-06-15-*.log
```

---

## What's Logged

### RunningLog Class Methods

| Method | Purpose | Log Format |
|--------|---------|-----------|
| `step(name, msg, status)` | Generic step | `[TIME +ELAPSED] [STATUS] NAME — MSG` |
| `success(name, msg)` | Success ✅ | `[TIME +ELAPSED] [✅ OK] NAME — MSG` |
| `warning(name, msg)` | Warning ⚠️ | `[TIME +ELAPSED] [⚠️ WARN] NAME — MSG` |
| `error(name, msg)` | Error ❌ | `[TIME +ELAPSED] [❌ ERROR] NAME — MSG` |
| `retry(name, attempt, wait)` | Retry ⏳ | Warning with attempt info |
| `finish(result)` | Completion | Summary + stats |

### Ingestion Steps Logged

In `ingest_raw_to_wiki()`:

1. **INIT** — Job starting
2. **CHECK** — Verifying raw/ folder exists
3. **INIT_SCHEMA** — Loading tag taxonomy
4. **INIT_INDEX** — Loading page index
5. **INIT_LOG** — Loading audit log
6. **SCAN** — Finding markdown files
7. **FILTER** — Quality checking (trashing low-quality)
8. **PROCESS** — Ingesting each file
9. **GRAPH** — Building knowledge graph
10. **SAVE_INDEX** — Saving updated index
11. **SAVE_LOG** — Saving updated log
12. **EXCEPTION** — If error occurs

---

## Error Cases

### Case 1: OpenAI Client Unavailable

```
📡 Checking OpenAI client connectivity (attempt 1/11)
⚠️ OpenAI client check failed: ...
⏳ Client not available, retrying in 5 minutes...

[5 minutes pass]

📡 Checking OpenAI client connectivity (attempt 2/11)
⚠️ OpenAI client check failed: ...
⏳ Client not available, retrying in 10 minutes...

[10 minutes pass]

📡 Checking OpenAI client connectivity (attempt 3/11)
✅ OpenAI client is available
→ Ingestion proceeds...
```

### Case 2: Running Log I/O Error

If logging fails (disk full, permissions), the code gracefully continues:
- Main ingestion proceeds (log not critical)
- Error is logged to standard logger
- Process doesn't crash

### Case 3: Complete Retry Exhaustion

```
❌ INGESTION JOB FAILED
Could not connect to OpenAI after 10 retries
[Check /logs/ for retry history]
```

---

## Monitoring Checklist

### Every Sunday After 07:00 UTC+8:00

- [ ] Check Render logs for ingestion start
- [ ] Look for "✅ INGESTION JOB COMPLETED SUCCESSFULLY" message
- [ ] Verify reports in `outputs/ingestion-reports/ingestion-YYYY-MM-DD.md`
- [ ] Check running log: `outputs/ingestion-logs/ingestion-YYYY-MM-DD-*.log`
- [ ] Count processed/trashed/failed files in report
- [ ] Verify no ❌ ERROR lines in running log

### If Ingestion Fails

1. Check running log for which step failed
2. Look at the specific error message
3. Verify OpenAI API status (if client error)
4. Check vault permissions and disk space
5. Review wiki/log.md for any concurrent conflicts

---

## Summary

✅ **Real-time visibility:** All ingestion steps logged with timestamps  
✅ **Automatic recovery:** Retries every 10 minutes if API down  
✅ **Full audit trail:** Every step recorded in timestamped files  
✅ **User-friendly:** Clear status symbols (✅/⚠️/❌)  
✅ **Zero data loss:** Log failures don't affect ingestion  

**Next ingestion:** Sunday 2026-06-15 at 07:00 UTC+8:00
- Full running log will be created: `outputs/ingestion-logs/ingestion-2026-06-15-*.log`
- Report will be saved: `outputs/ingestion-reports/ingestion-2026-06-15.md`
- Both files will show exact timeline and status of every step
