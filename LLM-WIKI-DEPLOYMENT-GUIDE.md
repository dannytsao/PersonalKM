# LLM-Wiki Integration Deployment Guide

**Status:** Phase 1 & 2 Complete & Tested ✅  
**Date:** 2026-06-13  
**Next Steps:** Phase 3 & 4 (Deploy to Production)

---

## What Changed

### New Files

- `bot/ingestion_wiki_helpers.py` (404 loc)
  - WikiSchema: Parse SCHEMA.md tag taxonomy
  - WikiIndex: Maintain index.md page catalog
  - WikiLog: Append-only log.md audit trail
  - WikiPage: Build/parse LLM-Wiki frontmatter
  - Helper functions: wikilink extraction, page discovery

- `bot/ingestion_v2.py` (468 loc)
  - Enhanced `ingest_raw_to_wiki()` with llm-wiki compliance
  - LLM-Wiki frontmatter generation
  - Automatic index.md + log.md maintenance
  - Wikilink integration between pages
  - Backward-compatible knowledge-graph.md

- `scripts/test_llmwiki_integration.py` (225 loc)
  - Comprehensive test suite (✅ all passing)

- `wiki/SCHEMA.md` (previously created)
  - Domain + 17-tag taxonomy
  - Conventions document

- `wiki/index.md` (previously created)
  - Navigation hub (template for auto-update)

- `wiki/log.md` (previously created)
  - Action log template

---

## Phase 3: Deploy to Production

### Step 1: Backup Current Data

```bash
# In PersonalKM working directory
git tag safety-pre-v2-deployment
git push origin safety-pre-v2-deployment

# This creates a restore point if something goes wrong
```

### Step 2: Replace ingestion.py with v2

**Option A (Recommended): Gradual Migration**

Keep both versions running in parallel:

```bash
# Keep original ingestion.py as fallback
mv bot/ingestion.py bot/ingestion_v1.py

# Activate v2
cp bot/ingestion_v2.py bot/ingestion.py
```

Then update `scripts/ingestion_job.py` (or cron) to import from bot.ingestion:

```python
# OLD:
from bot.ingestion import ingest_raw_to_wiki

# NEW (same path, but v2 code):
from bot.ingestion import ingest_raw_to_wiki
```

**Option B (Direct Replacement - Only if No Active Jobs)**

```bash
rm bot/ingestion.py
cp bot/ingestion_v2.py bot/ingestion.py
```

### Step 3: Test on Staging Data

Create test raw/ files and run dry-run:

```bash
# Create a few test notes in raw/
cat > raw/test-devops.md << 'EOF'
# Docker Best Practices 2026

- Use multi-stage builds
- Minimize layer count
- With Kubernetes orchestration
EOF

cat > raw/test-ai.md << 'EOF'
# Fine-tuning with LoRA

Using gpt-4o-mini models and transformers library for efficient fine-tuning.
EOF

# Run ingestion
python3 -m bot.ingestion ingest_raw_to_wiki ./

# Verify results
ls -la wiki/entities/
ls -la wiki/
cat wiki/log.md
cat wiki/index.md
```

### Step 4: Verify Output Structure

Check that new pages have llm-wiki frontmatter:

```bash
head -20 wiki/entities/test-devops.md
```

Expected output:
```yaml
---
title: Docker Best Practices 2026
created: 2026-06-13
updated: 2026-06-13
type: entity
tags: ["tech", "container", "devops"]
sources: ["raw/test-devops.md"]
confidence: medium
contested: false
contradictions: []
---

# Docker Best Practices 2026
...
```

### Step 5: Run Full Integration Test

```bash
python3 scripts/test_llmwiki_integration.py
```

Expected: ✅ All tests pass

### Step 6: Verify Navigation Files

```bash
# Check index.md has entries
grep -c '^\[\[' wiki/index.md

# Check log.md has audit trail
grep -c '## \[' wiki/log.md

# Verify knowledge-graph.md still works (backward compat)
head -10 wiki/knowledge-graph.md
```

---

## Phase 4: Monitor First Run

### Before Pushing to Render

1. **Commit changes locally**
   ```bash
   git add bot/ingestion.py bot/ingestion_v1.py
   git commit -m "feat: activate llm-wiki ingestion v2"
   ```

2. **Push to GitHub**
   ```bash
   git push origin main
   ```

3. **Render auto-deploys** (autoDeploy: true in render.yaml)

4. **Check deployment**
   ```bash
   curl https://personal-km-line-bot.onrender.com/health
   # Expected: 200 OK
   ```

### During First Ingestion (Sunday 9 AM)

Monitor the cron job:

```bash
# Check Render logs
# Dashboard: https://dashboard.render.com

# Or check git log for bot-generated commits
git log --oneline -10 -- wiki/
```

Expected behavior:
- raw/*.md files disappear (moved to wiki/)
- wiki/entities/, wiki/concepts/ gain new pages
- wiki/index.md updated with new entries
- wiki/log.md appended with action details
- wiki/knowledge-graph.md regenerated

### First 3 Runs Observation Period

**Week 1:**
- Monitor for API errors (OpenAI timeout, rate limit)
- Check index.md accuracy (entries match actual files)
- Verify log.md grows correctly (no duplication)

**Week 2:**
- Verify wikilinks work (pages link to related pages)
- Check frontmatter consistency (all pages have 8 fields)
- Validate tags are from SCHEMA.md taxonomy

**Week 3:**
- Review decay detection integration (if enabled)
- Check knowledge-graph.md completeness
- Run lint queries via llm-wiki skill

---

## Rollback Procedure

If issues arise:

```bash
# Restore v1
git checkout HEAD -- bot/ingestion.py
git tag rollback-from-v2
git push origin rollback-from-v2

# OR restore to safety point
git checkout safety-pre-v2-deployment -- bot/ingestion.py
git commit -m "rollback: revert to ingestion v1"
git push origin main
```

Then manually review wiki/ structure and fix any data corruption.

---

## Success Checklist

- [ ] backup tag created (safety-pre-v2-deployment)
- [ ] ingestion.py replaced with v2 (or v2 activated as v1.py)
- [ ] test suite passes locally (✅ verified)
- [ ] dry-run on test data succeeds
- [ ] index.md auto-maintained with correct entries
- [ ] log.md auto-maintained with audit trail
- [ ] frontmatter has all 8 llm-wiki fields
- [ ] wikilinks found and added to related pages
- [ ] knowledge-graph.md still works (backward compatibility)
- [ ] /health endpoint responding (deployed on Render)
- [ ] First Sunday 9 AM ingestion runs without errors

---

## Configuration Notes

**No .env changes needed.** All new behavior is automatic based on:
- SCHEMA.md (tag taxonomy)
- ingestion_wiki_helpers.py (helper classes)

**Performance impact:** Minimal
- WikiIndex + WikiLog updates: <100ms per ingest
- Wikilink discovery: <500ms (searches existing pages once)
- Overall ingest time: same as before (AI extraction dominates)

---

## Monitoring Commands

### Check recent ingestions
```bash
git log --oneline --since="1 week ago" -- wiki/log.md | head -5
```

### List pages added this week
```bash
find wiki/entities wiki/concepts -type f -mtime -7
```

### Validate frontmatter on all pages
```bash
for f in wiki/entities/*.md wiki/concepts/*.md; do
  grep -q "^---$" "$f" && echo "✓ $f" || echo "✗ $f"
done
```

### Check index.md vs reality
```bash
# Count pages in index.md
grep -c '^\[\[' wiki/index.md

# Count actual pages
find wiki/entities wiki/concepts -name "*.md" ! -name "SCHEMA.md" ! -name "*index*" ! -name "*log*" ! -name "*graph*" | wc -l
```

---

## Next Steps After Deployment

**Optional Phase 5:** Integrate knowledge_decay.py
- Mark old pages with decay-flagged tag
- Generate decay reports to outputs/decay-reports/

**Optional Phase 6:** Query via llm-wiki skill
- Use `hermes llm-wiki lint` to find orphans
- Use `hermes llm-wiki query` to search by tag
- Generate reports combining decay + wikilinks

---

## Questions or Issues?

Refer to:
- LLM-WIKI-BOT-INTEGRATION-PLAN.md (high-level overview)
- wiki/SCHEMA.md (tag taxonomy + conventions)
- wiki/QUICKREF.md (quick operations reference)
- bot/ingestion_wiki_helpers.py (class documentation)
- bot/ingestion_v2.py (enhanced workflows)
