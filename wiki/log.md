# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-06-13] init | LLM Wiki integration + schema

- Integrated Karpathy/LLM-Wiki pattern with existing PersonalKM structure
- Created SCHEMA.md with domain (multi-domain KM: Tech, Food, Photography, General)
- Created index.md with navigation
- Created log.md (this file)
- Preserved existing raw/ (285 files across 4 categories), wiki/entities/ (1 test file), wiki/concepts/, wiki/sources/
- Established tag taxonomy covering domain, topic, quality, and processing tags
- Decay management integrated: pages >90 days flagged automatically
- Configured cross-domain linking rules (Tech ↔ Productivity, Tech ↔ Food, Photography ↔ Travel)
- Set WIKI_PATH env var to: /Users/dannytsao/Documents/PersonalKM/wiki

---

**Orientation for new sessions:**
1. Read SCHEMA.md for domain + conventions + tag taxonomy
2. Read index.md to see all pages organized by type
3. Scan recent log.md entries (last 20-30 lines) to understand recent activity
4. search_files for specific topics before creating new pages
