# LLM Wiki Integration — Change Note
**Date:** 2026-06-13  
**Status:** ✅ Complete

## Summary

Integrated Karpathy's LLM Wiki pattern (knowledge compilation, cross-referencing, decay detection) with your existing PersonalKM structure. **No breaking changes.** All existing content preserved.

## What Changed

### Created (New Files)

1. **`wiki/SCHEMA.md`**
   - Domain definition: Multi-domain knowledge system (Tech, Food, Photography, General)
   - Conventions: wikilinks, frontmatter standards, cross-domain linking
   - Tag taxonomy: 17 core tags covering domain (tech, food, photography, general), topic (hermes-agent, ai-llm, container, etc.), quality (decay-flagged, needs-verification, wip), and processing (from-line, from-youtube, ai-summarized)
   - Update policy for handling contradictions
   - Entity/Concept/Comparison/Query page guidance
   - Page thresholds (when to create vs. add vs. archive)

2. **`wiki/index.md`**
   - Navigation hub listing all pages by type (Entities, Concepts, Comparisons, Queries)
   - Current count: 1 entity (test-docker-note)
   - Entry format: `[[wikilink]] — one-line summary`
   - Updated as new pages are ingested

3. **`wiki/log.md`**
   - Append-only action log
   - Tracks every operation: ingest, update, query, lint, create, archive, delete
   - Orientation instructions for new sessions
   - Rotation threshold: 500 entries → rename to log-YYYY.md

### Preserved (Existing Structure)

- **`raw/`** — 285 files across 4 categories (Tech 215, General 49, Food 22, Photography 6)
  - Immutable source layer. Frontmatter will be added on re-ingests to track sha256
- **`wiki/entities/`** — test-docker-note.md (1 existing entity)
- **`wiki/concepts/`** — empty, ready for concepts
- **`wiki/sources/`** — empty, available for source tracking
- **`outputs/`** — decay-reports, ingestion-reports, query-results remain untouched
- **`archive/`** — existing archived items stay in place
- **`.obsidian/`** — vault config unchanged

## Integration Points

### Raw → Wiki Flow

```
raw/Tech/        ──→ entities/ai-models/, concepts/devops/, entities/tools/
raw/Food/        ──→ entities/restaurants/, concepts/cuisines/
raw/Photography/ ──→ concepts/composition/, entities/locations/
raw/General/     ──→ concepts/essays/, entities/people/
```

All page creates/updates are logged to `log.md` and added to `index.md`.

### Decay Detection

Pages are auto-flagged `decay-flagged` when:
- Last `updated` date >90 days old
- Content has time-sensitive info (versions, prices, availability)

Reports: `outputs/decay-reports/` (existing location unchanged)

### Tag Taxonomy

Tags must come from SCHEMA.md before use. Prevents tag sprawl and enables consistent searching.

```yaml
Domain: tech, food, photography, general
Topic:  hermes-agent, ai-llm, container, web-dev, travel, productivity, learning
Quality: decay-flagged, needs-verification, wip, controversial, evergreen
Processing: from-line, from-youtube, from-article, ai-summarized, auto-tagged, manual-curated
```

## Environment Configuration

```bash
# Set in ~/.hermes/.env or manually in shell
export WIKI_PATH="/Users/dannytsao/Documents/PersonalKM/wiki"
```

Hermes agent will now use this path for all wiki operations (ingest, lint, query).

## Operating the Wiki

### Session Startup (Do This First)

```bash
cd /Users/dannytsao/Documents/PersonalKM/wiki
read wiki/SCHEMA.md       # Understand domain + conventions
read wiki/index.md        # See what pages exist
tail -30 wiki/log.md      # Recent activity
```

### Common Operations

**Search for a topic:**
```bash
search_files "docker" path="$WIKI_PATH" file_glob="*.md"
```

**Find orphan pages (broken links):**
```bash
# Usage: skill_view(name='llm-wiki') → run lint operation
# Returns: orphan pages, broken wikilinks, stale content, contradictions
```

**Ingest a new source:**
```bash
# 1. Capture raw source → raw/Tech/source-name.md
# 2. Agent reads it, identifies entities/concepts
# 3. Creates/updates wiki pages, adds to index.md, logs action
# 4. User discusses takeaways
```

**Update a page:**
- Bump `updated: YYYY-MM-DD` in frontmatter
- Update wikilinks if related concepts changed
- Log the action

### Obsidian Integration

The wiki directory is already an Obsidian vault at `/Users/dannytsao/Documents/PersonalKM/`.

- **Wikilinks render:** `[[page-name]]` works as clickable links
- **Graph View:** Visualizes knowledge network (Entities → Concepts → Queries)
- **Dataview:** Use queries like `TABLE tags FROM "wiki/entities"` to filter by tag
- **Search:** Find across all pages with Obs search

No additional setup needed — just open the vault in Obsidian.

## Next Steps (Optional, Not Urgent)

1. **Add wikilinks to existing pages** — test-docker-note.md should link to at least 2 other pages (future concepts)
2. **Bulk ingest raw/ into wiki** — when 285 raw files are mature enough, categorize into entities/concepts
3. **Set up Obsidian Sync** — if you want phone/multi-device access via Obsidian Sync
4. **Automate decay checks** — cron job to weekly flag stale pages (already exists in PersonalKM)

## Troubleshooting

**Q: How do I add a new tag?**  
A: Add it to SCHEMA.md tag taxonomy first, then use it in page frontmatter. Prevents tag sprawl.

**Q: Can I edit raw/ files?**  
A: No — raw/ is immutable. Create/update wiki pages instead. Corrections exist only in the wiki layer.

**Q: What if a wiki page contradicts another?**  
A: Mark both with `contradictions: [other-page]` in frontmatter. Set `contested: true`. Lint reports these for human review.

**Q: How often should I lint?**  
A: Weekly minimum, or after bulk ingest. Catches orphans, broken links, stale content, contradictions.

---

**Files Modified:**
- ✅ `wiki/SCHEMA.md` — created
- ✅ `wiki/index.md` — created
- ✅ `wiki/log.md` — created
- ✅ Existing files preserved (raw/, entities/, concepts/, etc.)

**Backward Compatibility:** ✅ 100% — all existing structure and content untouched. LLM Wiki pattern layered on top.

**Next Hermes Run:** WIKI_PATH will be recognized. You can now ingest sources into the wiki using `llm-wiki` skill operations.
