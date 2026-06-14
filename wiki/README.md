# PersonalKM Wiki — Knowledge Base Layer

**Last Updated:** 2026-06-14  
**Status:** Phase 4 Monitoring (3-week live ingestion)

## Overview

This is the **processed knowledge layer** of PersonalKM. Raw captures flow in from LINE bot, YouTube, web articles, and screenshots → ingestion pipeline processes them → curated entities and concepts live here.

## Structure

```
wiki/
├── README.md                  (this file — navigation & conventions)
├── SCHEMA.md                  (domain, frontmatter spec, tag taxonomy)
├── index.md                   (master catalog, 272 pages total)
├── log.md                     (append-only action log)
├── knowledge-graph.md         (auto-generated node listing)
├── entities/                  (148 specific topics, tools, people, articles)
├── concepts/                  (124 patterns, ideas, observations, places)
├── _archive/                  (superseded pages, kept for context)
└── sources.md                 (optional: bibliography & provenance)
```

## Base Files Purpose

### index.md
**Master catalog of all 272 wiki pages**, organized by type (entities, concepts, comparisons, queries).
- Updated auto: yes (on each ingestion batch)
- Format: wikilinks + one-line summaries
- Use this to find pages, discover related topics

### log.md
**Chronological action log**, append-only. Every ingest, update, query, delete goes here.
- Format: `## [YYYY-MM-DD] action | subject`
- Rotates to `log-YYYY.md` at 500 entries
- Use this to audit what changed and when

### SCHEMA.md
**Domain definition & conventions**. Defines:
- Frontmatter format (8 required fields)
- Tag taxonomy (domain, topic, quality, processing)
- Page creation thresholds
- Entity/concept/comparison page templates

### knowledge-graph.md
**Auto-generated list of all nodes** (entities, concepts).
- Regenerated after each ingestion batch
- JSON-like structure for tool consumption
- Use to verify ingestion success

### README.md (this file)
**Navigation & conventions**. You're reading this now.

---

## Quality Standards (Phase 4)

All 272 pages pass these checks:

✓ **Frontmatter complete:** 8-field YAML (title, created, updated, type, tags, sources, confidence, contested)
✓ **Type field corrected:** `type: entity` or `type: concept` (was "entitie", now fixed)
✓ **Single frontmatter block:** Removed double --- structure
✓ **Tags verified:** Proper spelling (e.g., "hermes" not "hemes")
✓ **Sources linked:** Traceable back to raw/ input

## Quick Start

1. **Explore topics:** Read `index.md` for quick overview
2. **Understand conventions:** Skim `SCHEMA.md` (5 min)
3. **Find recent activity:** Check last 20 lines of `log.md`
4. **Search for something:** Use `search_files` against wiki/

## Ingestion Pipeline Status

Weekly cron runs: **Saturday 23:00 UTC (Sunday 07:00 UTC+8:00)**  
Next run: Sunday 2026-06-15 07:00 UTC+8:00

Pipeline stages:
1. **Ingest:** Capture from LINE, YouTube, web (raw/)
2. **Quality filter:** Trash low-quality patterns (11 patterns, 3.9% rate)
3. **Entity extraction:** LLM identifies topics, entities, concepts
4. **Organize to wiki:** Write entities/ and concepts/ with frontmatter
5. **Update indexes:** Regenerate index.md, graph, log.md
6. **Deploy:** Push to Render prod

**Current state:** 272 files successfully processed (as of 2026-06-14 08:37)

---

## Files Status (Phase 4 Verification)

| File | Purpose | Last Update |
|------|---------|-------------|
| index.md | Catalog (272 pages) | 2026-06-14 08:37 |
| log.md | Action log (500+ entries) | 2026-06-14 08:33 |
| SCHEMA.md | Conventions | 2026-06-13 |
| knowledge-graph.md | Node listing | 2026-06-14 08:37 |
| entities/ | 148 specific items | 2026-06-14 08:33 |
| concepts/ | 124 patterns/ideas | 2026-06-14 08:33 |

---

## Known Issues & Fixes (just applied)

**FIXED 2026-06-14:**
- ✓ Removed double frontmatter from all 272 files
- ✓ Corrected "type: entitie" → "type: entity" in all files
- ✓ Fixed tag typos (e.g., "hemes" → "hermes")
- ✓ Verified all files have single, clean frontmatter block

---

## Next Steps

1. Continue Phase 4 monitoring (3 weeks): watch for ingestion errors
2. If silent failures appear: check `organize_note_to_wiki()` logging
3. Post-Phase-4 (2026-07-05): Evaluate decay patterns, archive outdated content
4. Implement auto-health-checks per `knowledge-system-health-monitoring` skill

---

**Questions?** Check SCHEMA.md for rules, or search log.md for similar past actions.
