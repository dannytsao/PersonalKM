# Phase 4 Monitoring Checklist

**Phase:** 4 (Monitoring & Validation)  
**Start Date:** Saturday 2026-06-14 23:00 UTC / Sunday 2026-06-15 07:00 UTC+8:00  
**Duration:** 3 weeks (Weeks 1-3)  
**Status:** Ready to begin

---

## Overview

Monitor the first 3 automatic ingestions to ensure all systems are working correctly:
- Running logs created properly
- Quality filtering working (11 files trashed)
- Auto-retry mechanism functional (if needed)
- Reports generated
- Wiki updates successful
- Archive directory managed correctly

---

## Week 1 Checklist

**Date:** Saturday 2026-06-14 23:00 UTC / Sunday 2026-06-15 07:00 UTC+8:00

### Before Ingestion
- [ ] Verify cron job is scheduled in render.yaml
- [ ] Check Render dashboard shows personal-km-weekly-ingestion service
- [ ] Verify OpenAI API key is set in Render environment

### During Ingestion (or immediately after)
- [ ] Check Render logs for job start
- [ ] Look for: "WEEKLY INGESTION JOB STARTED"
- [ ] Verify no "❌ ERROR" messages in logs
- [ ] Check for client availability check + result

### After Ingestion (check results directory)
- [ ] Running log exists: `outputs/ingestion-logs/ingestion-2026-06-15-*.log`
- [ ] Report exists: `outputs/ingestion-reports/ingestion-2026-06-15.md`
- [ ] Running log size > 1 KB (not empty/minimal)
- [ ] Report shows: processed=273, trashed=11, failed=0

### Verify Files & Structure
- [ ] archive/ directory exists and contains 11 files (trashed items)
- [ ] wiki/index.md was updated with new pages
- [ ] wiki/log.md has new entry for ingestion
- [ ] wiki/knowledge-graph.md was regenerated
- [ ] raw/ folder is empty or archived

### Check Running Log Contents
```bash
cat outputs/ingestion-logs/ingestion-2026-06-15-*.log
```
Should contain:
- [ ] "Ingestion Log Started" header
- [ ] Multiple steps with timestamps
- [ ] All steps show "✅ OK" status
- [ ] Final summary with counts
- [ ] "Ingestion Log Finished" footer

### Check Report Contents
```bash
cat outputs/ingestion-reports/ingestion-2026-06-15.md
```
Should show:
- [ ] Total processed: 273
- [ ] Total trashed: 11
- [ ] Total failed: 0
- [ ] Timestamp of ingestion
- [ ] Link to running log

### Sample Expected Log
```
[HH:MM:SS +0.0s] [✅ OK   ] INIT — Starting ingestion process
[HH:MM:SS +0.1s] [✅ OK   ] CHECK — Checking raw/ folder
[HH:MM:SS +0.1s] [✅ OK   ] INIT_SCHEMA — Loading wiki schema
[HH:MM:SS +0.1s] [✅ OK   ] INIT_INDEX — Loading wiki index
[HH:MM:SS +0.1s] [✅ OK   ] INIT_LOG — Loading wiki log
[HH:MM:SS +0.1s] [✅ OK   ] SCAN — Found 284 files
[HH:MM:SS +0.3s] [✅ OK   ] FILTER — Filtered 11 low-quality files
[HH:MM:SS +0.6s] [✅ OK   ] PROCESS — Processing 273 files
[HH:MM:SS +0.7s] [✅ OK   ] GRAPH — Knowledge graph updated
[HH:MM:SS +0.7s] [✅ OK   ] SAVE_INDEX — Wiki index saved
[HH:MM:SS +0.7s] [✅ OK   ] SAVE_LOG — Wiki log saved
```

### Issue: Not Completed by Monday Morning
If ingestion didn't run:
- [ ] Check Render logs for errors
- [ ] Verify cron job exists in render.yaml
- [ ] Check if OpenAI API was down
- [ ] Look for retry attempts in logs (5-10 min intervals)
- [ ] If retrying: wait another 10 minutes, check again
- [ ] If failed: document error, prepare for Week 2

### Issue: Ingestion Failed
If running log shows errors:
- [ ] Find the ❌ ERROR step
- [ ] Note exact error message
- [ ] Check if it's client-related (auto-retry will handle)
- [ ] Check if it's filesystem-related (permissions, disk space)
- [ ] Document for troubleshooting
- [ ] Week 2 should still auto-run (don't manually trigger)

### Result: WEEK 1 ✅
Print/note summary:
```
Week 1 Summary (2026-06-15):
- Ingestion: ✅ SUCCESS
- Running log: ✅ CREATED (ingestion-2026-06-15-HHMMSS.log)
- Processed: 273 files
- Trashed: 11 files
- Failed: 0
- Time elapsed: ~Xs
- No manual intervention needed
```

---

## Week 2 Checklist

**Date:** Saturday 2026-06-21 23:00 UTC / Sunday 2026-06-22 07:00 UTC+8:00

Repeat all checks from Week 1:

- [ ] Render logs show successful start
- [ ] Running log created: `ingestion-2026-06-22-*.log`
- [ ] Report created: `ingestion-2026-06-22.md`
- [ ] Processed: 273, Trashed: 11, Failed: 0
- [ ] archive/ contains trashed files
- [ ] wiki/ directory updated

### Additional: Consistency Check
- [ ] Week 2 results match Week 1 (same counts)
- [ ] Running log format identical to Week 1
- [ ] Report format identical to Week 1
- [ ] No unusual delays or retry messages
- [ ] Same steps in same order

### Result: WEEK 2 ✅
```
Week 2 Summary (2026-06-22):
- Ingestion: ✅ SUCCESS
- Consistency: ✅ MATCHES WEEK 1
- Processed: 273 files
- Trashed: 11 files
- Failed: 0
- Status quo maintained
```

---

## Week 3 Checklist

**Date:** Saturday 2026-06-28 23:00 UTC / Sunday 2026-06-29 07:00 UTC+8:00

Repeat Week 2 checks:

- [ ] Render logs show successful start
- [ ] Running log created: `ingestion-2026-06-29-*.log`
- [ ] Report created: `ingestion-2026-06-29.md`
- [ ] Processed: 273, Trashed: 11, Failed: 0
- [ ] Consistency maintained from Weeks 1-2

### Final Validation
- [ ] 3 running logs exist (W1, W2, W3)
- [ ] 3 reports exist (W1, W2, W3)
- [ ] All show identical counts
- [ ] All show ✅ status
- [ ] No error patterns detected

### Historical Review
```bash
ls -la outputs/ingestion-logs/ingestion-2026-06-*.log
ls -la outputs/ingestion-reports/ingestion-2026-06-*.md
```

Should show 3 files each (or more if new files captured during week)

### Result: WEEK 3 ✅ — PHASE 4 COMPLETE
```
Phase 4 Completion Summary (2026-06-29):
- Week 1: ✅ SUCCESS
- Week 2: ✅ SUCCESS (consistent with Week 1)
- Week 3: ✅ SUCCESS (consistent with Weeks 1-2)
- Pattern: STABLE & PREDICTABLE
- Status: PRODUCTION READY
- Next: Phase 5 (optional) or maintenance mode
```

---

## If Issues Arise

### Issue: Client Unavailable (Retries Triggered)

**What to see in logs:**
```
📡 Checking OpenAI client connectivity (attempt 1/11)
⚠️ Client not available, retrying in 5 minutes...
[wait 5 minutes]
📡 Checking OpenAI client connectivity (attempt 2/11)
✅ OpenAI client is available
✅ Client available, starting ingestion...
```

**Action:** This is expected behavior. Ingestion will proceed after client recovers. No action needed.

### Issue: Running Log Not Created

**Possible causes:**
- Ingestion job didn't run (cron failed)
- Job ran but crashed before logging initialized
- Filesystem permissions issue

**Troubleshooting:**
1. Check Render logs for errors
2. Verify render.yaml has cron service
3. Manually test: `VAULT_PATH=... OPENAI_API_KEY=... python scripts/ingestion_job.py`
4. Check disk space: `df -h`
5. Check permissions: `ls -la outputs/`

### Issue: Running Log Shows ❌ ERROR

**Action:** Note which step failed, check error message

**Common errors:**
- "raw/ folder not found" → check bucket paths
- "OpenAI API error" → client will auto-retry
- "Permission denied" → check file permissions
- "Disk full" → cleanup archive/

### Issue: Counts Don't Match (e.g., 270 instead of 273)

**Investigation:**
- New content added mid-week → processed count changes
- Some files might have been manually removed
- Check git log for recent changes to raw/

**Action:** Document the difference, note expected vs actual

### Decision Tree

```
Ingestion ran?
  ├─ YES → Did it complete successfully?
  │   ├─ YES → ✅ PASS (check log for any warnings)
  │   └─ NO → Did it auto-retry?
  │       ├─ YES → Retries working, check if recovered
  │       └─ NO → Check error, document issue
  └─ NO → Did cron trigger?
      ├─ YES → Check Render logs for errors
      └─ NO → Verify render.yaml cron service exists
```

---

## Success Criteria (Phase 4 Complete)

All 3 weeks must pass these criteria:

1. ✅ **Automation:** Ingestion ran without manual trigger
2. ✅ **Consistency:** Same results each week (273/11/0)
3. ✅ **Logging:** Running logs created and formatted correctly
4. ✅ **Resilience:** If API down, auto-retry worked
5. ✅ **Data:** No data loss, all trashed files archived
6. ✅ **Audit:** wiki/log.md and running logs match
7. ✅ **Reports:** Summary reports generated correctly
8. ✅ **Zero intervention:** No manual actions needed

---

## After Phase 4 Complete (2026-07-07)

### Decision: Proceed to Phase 5?

If all 3 weeks ✅ passed:
- [ ] Phase 5 (optional): knowledge_decay.py integration
- [ ] Automated quality checks on ingested content
- [ ] Detection of knowledge gaps

If any issues found:
- [ ] Document root cause
- [ ] Implement fix
- [ ] Re-run Week 1-3 monitoring after fix
- [ ] Approve Phase 5 after stability confirmed

### Maintenance Mode (If Phase 5 skipped)

Ingestion continues automatically every Sunday:
- [ ] Weekly check: Running log created ✅
- [ ] Weekly check: Report generated ✅
- [ ] Weekly check: Counts reasonable (273 ± buffer)
- [ ] Monthly: Archive cleanup (move old files)
- [ ] Quarterly: Review logs for patterns

---

## Summary

**Phase 4 is** real-time monitoring of 3 automatic ingestion runs to validate:
- Cron scheduling works
- Quality filtering works
- Running logs capture all steps
- Auto-retry handles API issues
- Reports generate correctly
- Zero data loss

**Timeline:** 3 weeks (2026-06-15 to 2026-06-29)  
**After:** Phase 5 optional or maintenance mode  
**Effort:** ~5-10 minutes per week to verify checklist

✅ Ready to begin Week 1 ingestion!
