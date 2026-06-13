# LLM-Wiki Integration Plan for PersonalKM Bot

**Date:** 2026-06-13  
**Goal:** Modify bot.ingestion.py to follow llm-wiki conventions  
**Status:** Planning

## Current State

**bot/ingestion.py:**
- ✅ Processes raw/ → wiki/ (entities/, concepts/)
- ✅ Uses AI (OpenAI) to extract entities
- ✅ Adds YAML frontmatter (captured_date, categories, entities, wiki_path)
- ✅ Generates knowledge-graph.md
- ❌ Does NOT maintain index.md (no page catalog)
- ❌ Does NOT maintain log.md (no audit trail)
- ❌ Does NOT add wikilinks between pages
- ❌ Does NOT add quality signals (confidence, contested, contradictions)
- ❌ Does NOT follow llm-wiki tag taxonomy

**bot/knowledge_decay.py:**
- ✅ Detects stale content (>90 days, time-sensitive)
- ✅ Generates decay reports
- ✅ Works independently

## Changes Required

### 1. Enhanced Frontmatter (ingestion.py)

**Current:**
```yaml
---
captured_date: ISO timestamp
categories: ["devops", "ai"]
entities: [list]
wiki_path: "entities/docker"
---
```

**Enhanced (llm-wiki compliant):**
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept
tags: [from_schema_taxonomy]  # e.g., [tech, container, docker, devops]
sources: [raw/Tech/source.md]
confidence: high | medium | low
contested: false
contradictions: []
---
```

### 2. Wikilinks Between Pages (NEW)

When organizing note_a that mentions "Docker" and "Kubernetes":
- If docker.md exists → add `[[entities/docker]]` to note_a
- If kubernetes.md exists → add `[[entities/kubernetes]]` to note_a
- Add reciprocal links: docker.md links back to note_a

### 3. Maintain index.md (NEW)

After each ingest:
- Read index.md
- For each new page created, add entry: `[[path/slug]] — one-line summary`
- Update "Total pages" counter
- Update "Last updated" timestamp

### 4. Maintain log.md (NEW)

Append to log.md for each operation:
```
## [2026-06-13] ingest | Weekly batch (5 sources)
- Created: entities/docker.md, entities/kubernetes.md
- Updated: concepts/container-networking.md
- Total pages now: 42
- Status: 5 processed, 0 failed
```

### 5. Decay Detection Integration

- Mark pages >90 days old with `decay-flagged` tag
- Update log.md with decay findings
- Generate decay reports to outputs/decay-reports/

## Files to Modify

1. **bot/ingestion.py** (main changes)
   - Enhance frontmatter generation
   - Add wikilink extraction + linking logic
   - Add index.md update function
   - Add log.md update function
   - Integrate tag taxonomy from wiki/SCHEMA.md

2. **bot/ingestion_wiki_helpers.py** (NEW, helper module)
   - Parse wiki/SCHEMA.md to get tag taxonomy
   - Find wikilink candidates
   - Extract one-line summaries from pages
   - Update index.md safely (preserve order, format)
   - Append to log.md

3. **bot/knowledge_decay.py** (minor changes)
   - Add decay-flagged tag to flagged pages
   - Log decay operations to log.md

4. **scripts/ingestion_job.py** (if exists, verify integration)
   - Ensure it calls updated ingestion.py
   - Verify cron scheduling still works

## Implementation Steps

### Phase 1: Helper Module (Low Risk)
- Create bot/ingestion_wiki_helpers.py
- Functions: read_schema(), find_wikilink_candidates(), extract_summary(), update_index(), append_log()
- Tests: Verify no side effects, dry-run on existing data

### Phase 2: Enhanced Frontmatter (Medium Risk)
- Modify bot/ingestion.py → organize_note_to_wiki()
- Generate llm-wiki compliant frontmatter
- Keep backward compatibility (detect old frontmatter, migrate)

### Phase 3: Wikilinks (Medium Risk)
- After page creation, search for related pages
- Add [[wikilinks]] to body
- Update related pages' backlinks

### Phase 4: Navigation (Low Risk)
- Call update_index() after each page create/update
- Call append_log() for every operation

### Phase 5: Decay Integration (Low Risk)
- Pass existing pages to decay detection
- Tag with decay-flagged before ingest
- Log findings

## Backward Compatibility

✅ All changes are additive:
- Old frontmatter pages can be migrated on next ingest
- knowledge-graph.md can coexist with index.md
- No breaking changes to raw/ structure
- Decay reports unchanged

## Timeline

Phase 1: 30 min (helper module + tests)
Phase 2: 20 min (frontmatter enhancement)
Phase 3: 30 min (wikilink logic)
Phase 4: 15 min (navigation maintenance)
Phase 5: 15 min (decay integration)

**Total: ~2 hours**

## Risk Mitigation

✓ Commit each phase separately
✓ Dry-run on existing data before deploy
✓ Test with 1-2 sample notes first
✓ Keep knowledge-graph.md generation (fallback)
✓ Maintain git history for rollback

## Success Criteria

- ✅ index.md auto-maintained (accurate page count)
- ✅ log.md auto-maintained (audit trail)
- ✅ All pages have llm-wiki frontmatter
- ✅ Wikilinks between related pages work
- ✅ Decay-flagged tags applied correctly
- ✅ Next ingest run succeeds with proper structure
- ✅ All tests pass

---

Ready to implement?
