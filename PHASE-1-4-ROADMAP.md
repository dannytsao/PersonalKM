# 🎯 PersonalKM Enhancement Roadmap - APPROVED

**Status:** ✅ APPROVED & IN PROGRESS  
**Date Approved:** 2026-06-07  
**Phase:** 1+4 (Quick Wins)  
**Total Duration:** 4 hours  
**Review Date:** 2026-07-07 (one month)

---

## 📋 Executive Summary

**Goal:** Organize PersonalKM vault with Karpathy's three-tier structure + automated weekly ingestion

**What You Get:**
- ✅ Structured vault (raw → wiki → outputs)
- ✅ Weekly auto-organization
- ✅ All current features continue working
- ✅ Foundation for Phase 2+3 later

**Cost:** +$0.20-0.40/month  
**Time:** 4 hours  
**Risk:** Very low

---

## 🎬 Phase 1: RESTRUCTURE (2 hours)

### What This Does
Reorganize vault from flat structure to three-tier Karpathy framework.

### Current Structure
```
PersonalKM/
├── Inbox/
│   ├── Tech/
│   ├── General/
│   └── Photography/
├── Archive/
└── Trash/
```

### New Structure
```
PersonalKM/
├── raw/                    ← Brain dump (new captures)
│   └── [LINE bot saves here]
├── wiki/                   ← Organized knowledge
│   ├── concepts/
│   ├── entities/
│   ├── sources/
│   └── knowledge-graph.md
├── outputs/                ← Reports & results
│   ├── decay-reports/
│   └── query-results/
├── archive/                ← Old notes (renamed from Archive)
├── trash/                  ← Deleted notes
└── [config files]
```

### Implementation Steps

**Step 1: Create directories** (15 min)
```bash
mkdir -p raw/ wiki/concepts wiki/entities wiki/sources outputs/decay-reports outputs/query-results
```

**Step 2: Migrate existing notes** (30 min)
```bash
# Move current Inbox contents to archive (they're already organized in categories)
mv Inbox/* archive/
rmdir Inbox/

# Keep Archive folder as reference but rename
mv Archive archive-old

# Move old notes to archive
```

**Step 3: Modify bot/app.py** (45 min)
- Change: Save new captures to `raw/` instead of `Inbox/`
- Change: Enrichment still happens same way
- Change: Decay check still happens same way
- No changes needed for enrichment or decay systems

**Code change:**
```python
# OLD:
note_path = write_note(vault_path, settings.inbox_dir, note)

# NEW:
note_path = write_note(vault_path, "raw", note)  # Save to raw/
```

**Step 4: Test & commit** (30 min)
- Test capturing a note via LINE
- Verify it appears in `raw/`
- Run decay check
- Commit to Git
- Deploy to Render

### Success Criteria
- ✅ New captures go to raw/
- ✅ Enrichment works on raw/ files
- ✅ Decay detection works on raw/ files
- ✅ Git commits succeed
- ✅ Render deployment succeeds

---

## 🔄 Phase 4: AUTO-INGESTION (2 hours)

### What This Does
Weekly automation to organize raw/ → wiki/ with entity extraction

### The Process

Every week (Sunday 9 AM):
```
1. Scan raw/ for new files
2. For each file:
   - Extract key entities (frameworks, versions, concepts)
   - Identify DevOps/AI relevance
   - Generate summary (if not already enriched)
   - Create wiki/ entry
   - Build relationships
3. Update wiki/knowledge-graph.md
4. Commit changes to Git
5. Push to GitHub
```

### Implementation Steps

**Step 1: Create bot/ingestion.py** (45 min)
```python
def ingest_raw_to_wiki(vault_path):
    """
    1. List all files in raw/
    2. For each new file:
       - Extract entities
       - Move to wiki/ organized structure
       - Create relationships
    3. Update knowledge-graph.md
    4. Return ingestion report
    """
```

**Step 2: Create cron job script** (30 min)
```
~/.hermes/scripts/second-brain-ingest.py
- Weekly trigger (Sunday 9 AM, or you pick day/time)
- Runs ingestion
- Generates report
- Commits to Git
- Auto-deploys on Render
```

**Step 3: Configure cron job** (30 min)
```bash
hermes cronjob create \
  --name "second-brain-weekly-ingest" \
  --schedule "0 9 * * 0" \
  --prompt "Run weekly vault ingestion"
```

**Step 4: Test & verify** (15 min)
- Run ingestion manually
- Verify wiki/ structure populates
- Check knowledge-graph.md created
- Verify commit succeeds

### Success Criteria
- ✅ raw/ files are processed weekly
- ✅ Entities extracted correctly
- ✅ Files moved to wiki/ properly organized
- ✅ knowledge-graph.md generates
- ✅ Git commits automatically
- ✅ Cron job runs reliably

---

## 📅 Implementation Timeline

### Week 1 (This Week): IMPLEMENTATION

**Monday-Tuesday (2 hours):**
- Phase 1: Restructure directories
- Migrate existing notes
- Modify bot/app.py
- Test & verify
- First commit

**Wednesday-Thursday (2 hours):**
- Phase 4: Create ingestion system
- Setup cron job
- Test weekly automation
- Verify all systems
- Second commit

**Friday:**
- Full system test
- Deploy to Render
- Verify both phases working
- Final commit with "Ready for production" message

### Week 2-4: USAGE & MONITORING

**Your actions:**
- Continue using LINE bot normally
- Captures now go to raw/
- Watch weekly ingestion (Sundays 9 AM)
- Weekly ingestion organizes vault automatically

**System actions:**
- Weekly: auto-ingestion runs
- Real-time: enrichment + decay detection still running
- Monthly: decay reports still generating
- All: commits to GitHub

### Week 5 (One Month): REVIEW

**Review meeting (2026-07-07):**
- Assess: Is organization working?
- Verify: Is weekly ingestion reliable?
- Decide: Ready for Phase 2+3?
- Feedback: What would help most?

---

## 🎯 What Stays The Same

These systems continue working without changes:

✅ **LINE Bot Capture**
- Still captures URLs immediately
- Still works the same way

✅ **AI Enrichment**
- Still auto-tags notes
- Still generates summaries
- Still adds YAML frontmatter
- Now works on raw/ files

✅ **Decay Detection**
- Still analyzes DevOps/AI notes
- Still flags outdated content
- Still adds deprecation notices
- Now works on raw/ files (and later wiki/)

✅ **Monthly Reports**
- Still generates .decay-report-monthly.md
- Still prioritizes updates
- Works on entire vault

---

## 🎁 What Changes

✅ **Note Location**
- New captures: `raw/` (was `Inbox/`)
- Organized: `wiki/` (new)

✅ **Weekly Automation**
- New: `second-brain-ingest` cron job
- Every Sunday 9 AM (configurable)
- Auto-organizes vault

✅ **Vault Structure**
- New: Three-tier organization
- Clear: raw → wiki → outputs

---

## 📊 Success Metrics (for 1-month review)

On 2026-07-07, we'll assess:

### Organizational Metrics
- [ ] How many captures in raw/ weekly?
- [ ] How many files moved to wiki/ by ingestion?
- [ ] Is wiki/ structure organized as expected?
- [ ] knowledge-graph.md generating correctly?

### Reliability Metrics
- [ ] Weekly ingestion runs reliably?
- [ ] Git commits succeed 100% of time?
- [ ] Render deployment stable?
- [ ] Any errors in logs?

### User Experience Metrics
- [ ] Easier to find captured notes?
- [ ] Happy with new structure?
- [ ] Decay detection still working?
- [ ] Monthly reports still useful?

### Next Steps Decision
- [ ] Ready for Phase 2 (entity extraction + relationships)?
- [ ] Ready for Phase 3 (query interface)?
- [ ] Want to make adjustments to Phase 1+4 first?
- [ ] Any feedback on implementation?

---

## 🔧 Configuration Details

### Directory Permissions
```
raw/        755  (everyone can read/write)
wiki/       755  (everyone can read/write)
outputs/    755  (everyone can read/write)
archive/    755  (read-only backup)
```

### Cron Job Settings
- **Schedule:** Sunday 9 AM (0 9 * * 0)
- **Frequency:** Weekly
- **Timeout:** 5 minutes
- **Notification:** Will set reminder for review

### Git Commit Messages
- Phase 1 commit: "🏗️ Phase 1: Restructure vault (raw→wiki→outputs)"
- Phase 4 commit: "🔄 Phase 4: Add weekly auto-ingestion"
- Weekly ingestion: "📚 Weekly vault ingestion: N new notes organized"

---

## 📝 Documentation Updates Needed

After implementation, we'll update:
- ✅ README.md (mention raw/wiki/outputs structure)
- ✅ SYSTEM-SUMMARY.md (add Phase 1+4 info)
- ✅ This file (mark sections COMPLETE)
- ✅ GitHub repo docs

---

## ⚠️ Risk Mitigation

**What could go wrong:**

1. **Migration fails**
   - ✓ Backup: Git history preserved
   - ✓ Recovery: All files still in branch history

2. **New captures miss enrichment/decay**
   - ✓ Won't happen: Code paths unchanged
   - ✓ Both systems still run on raw/ files

3. **Weekly ingestion breaks**
   - ✓ Manual fallback: Can run ingestion manually
   - ✓ Won't break captures: raw/ still works

4. **Render deployment fails**
   - ✓ Easy rollback: Previous version in git
   - ✓ Can restart service manually

**Overall risk level: VERY LOW** ✅

---

## 🎊 Expected Outcome After 1 Month

### What You'll See
- ✅ Vault organized in clear structure
- ✅ New captures automatically organized weekly
- ✅ Everything else working exactly as before
- ✅ Foundation set for future enhancements
- ✅ No manual maintenance required

### What You Won't See (yet)
- ❌ Query interface (Phase 3)
- ❌ Knowledge graph visualization (Phase 2)
- ❌ Entity relationship mapping (Phase 2)

### Decision at 1-Month Review
- Do you want Phase 2+3? (query + graph)
- Or keep Phase 1+4 as-is?
- Any adjustments needed?

---

## 📞 One-Month Review Reminder

**Set for:** 2026-07-07 (exactly one month from now)  
**Type:** Automated reminder + summary report  
**What to assess:**
1. Is organization working as expected?
2. Is weekly automation reliable?
3. Do you want Phase 2+3?
4. Any issues to fix?

---

## ✅ Sign-Off

**Developer (Me):** Ready to implement ✅  
**User (You):** Approved Phase 1+4 ✅  
**Start Date:** 2026-06-07  
**Expected Completion:** 2026-06-11 (Friday)  
**Review Date:** 2026-07-07 (one month)  

---

## 🚀 Next Action

Ready to start implementation!

**What I'll do now:**
1. Create the implementation plan details
2. Build Phase 1 (2 hours)
3. Build Phase 4 (2 hours)
4. Test everything
5. Deploy to Render
6. Set one-month review reminder
7. Commit everything with detailed messages

**Estimated completion:** This Friday 2026-06-11

Ready? Let's go! 🚀
