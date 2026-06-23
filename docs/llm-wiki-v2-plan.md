# LLM Wiki v2 — Enhanced Ingestion Pipeline

> Plan for adding AI Summarization (MiniMax), Entity Deduplication, and Bidirectional Wikilinks to the PersonalKM ingestion pipeline.
> Status: **PLANNED** — Not started

## Overview

| Feature | What It Does | Impact |
|---------|-------------|--------|
| AI Summarization (MiniMax) | Distill raw captures → 30-50 line summaries | Wiki pages readable in 30 seconds |
| Entity Deduplication | One page per entity, updated on new captures | No more 50 "Claude Code" files |
| Bidirectional Wikilinks | Pages link to each other | Knowledge graph instead of file pile |

---

## Phase 1: MiniMax Client Wrapper

**Goal:** Create a reusable LLM client that uses MiniMax by default, falls back to OpenAI.

**Files:**
- `bot/llm_clients.py` (NEW)

**What it does:**
- `MiniMaxClient` — OpenAI-compatible, uses `base_url="https://api.minimax.io/v1"` + `MINIMAX_API_KEY`
- `OpenAIClient` — Fallback using `OPENAI_API_KEY`
- `get_default_client()` — Auto-detect best available (MiniMax → OpenAI → None)

**Exit Condition:**
```bash
cd ~/Documents/PersonalKM
python -c "
from bot.llm_clients import get_default_client
c = get_default_client()
print('Provider:', c.provider)
print('Models:', c.list_models()[:3])
"
# Must print provider name and list 3+ model names without errors
```

**Exit Criteria:**
- [ ] `bot/llm_clients.py` imports without error
- [ ] `get_default_client()` returns a client (MiniMax if key available)
- [ ] `client.chat_completions.create()` succeeds with a test prompt
- [ ] Falls back gracefully when no API key available (returns None, no crash)

---

## Phase 2: AI Summarization

**Goal:** Distill raw captures into concise wiki summaries using MiniMax.

**Files:**
- `bot/llm_summarizer.py` (NEW)

**What it does:**
- `summarize_content(content, page_type)` → `{summary, key_facts, linked_entities, confidence}`
- `distill_to_markdown(summarization_result)` → formatted wiki body
- Prompt designed to output: 30-50 line distillation, key facts as bullet list, entity mentions normalized

**Prompt strategy:**
```
You are a knowledge curator. Distill this content into a wiki page:

CONTENT:
{raw_content}

OUTPUT (in markdown):
## Summary
{3-5 sentence summary}

## Key Facts
- {fact 1}
- {fact 2}
- {fact 3}

## Entities Mentioned
- {entity 1}
- {entity 2}

## Related Concepts
- {concept 1}

## Source
^[raw/path/file.md]
```

**Exit Condition:**
```bash
cd ~/Documents/PersonalKM
python -c "
from bot.llm_summarizer import summarize_content

raw = open('raw/Tech/sample.md').read() if Path('raw/Tech').exists() else '# Test\nTest content about Claude Code and AI agents.'
result = summarize_content(raw, 'entity')

print('Summary length:', len(result['summary']))
print('Key facts:', len(result['key_facts']))
print('Entities:', result['linked_entities'])
"
# Summary must be <200 words (distilled vs raw)
# Key facts must be 3-10 bullets
# Entities must be non-empty list
```

**Exit Criteria:**
- [ ] `bot/llm_summarizer.py` imports without error
- [ ] `summarize_content()` returns dict with `summary`, `key_facts`, `linked_entities`
- [ ] Summary is meaningfully shorter than input (distillation works)
- [ ] Entity names normalized (English slug format)
- [ ] No crashes on empty/short content (graceful degradation)

---

## Phase 3: Entity Deduplication

**Goal:** One wiki page per entity, updated on new captures (not a new file each time).

**Files:**
- `bot/entity_dedup.py` (NEW)

**What it does:**
- `EntityRegistry` — In-memory index built at ingestion start
  - Scans `wiki/entities/` and `wiki/concepts/` for existing pages
  - Maps normalized names → file paths
- `find_entity_match(name)` → path or None
- `update_or_create(entity_name, new_content, source_path)` → path
  - If match found: append new content + provenance to existing page
  - If not found: create new page

**Name normalization rules:**
- Lowercase, hyphens, no spaces
- Chinese → Pinyin or English equivalent if possible
- Remove timestamps from filenames: `2026-06-14-claude-code.md` → `claude-code`
- Remove platform suffixes: `...-on-youtube`, `...-on-instagram`

**Exit Condition:**
```bash
cd ~/Documents/PersonalKM
# Create 2 test files about same entity (e.g., "Claude Code")
# Run: python -c "
from bot.entity_dedup import EntityRegistry
from pathlib import Path

registry = EntityRegistry(Path('wiki'))
print('Indexed entities:', registry.count())

# Check if duplicate detection works
match = registry.find_entity_match('claude-code')
print('Match for claude-code:', match)
"
# After running on 2 files about same entity:
# Only 1 file should exist in wiki/entities/ (not 2)
```

**Exit Criteria:**
- [ ] `bot/entity_dedup.py` imports without error
- [ ] `EntityRegistry` builds index from existing wiki in <5 seconds
- [ ] `find_entity_match('claude-code')` finds `claude-code.md` (case-insensitive)
- [ ] Processing 2 captures about same entity → only 1 wiki page
- [ ] Original file deleted after successful deduplicated ingest

---

## Phase 4: Bidirectional Wikilinks

**Goal:** When a new page mentions existing entities, add links BOTH ways.

**Files:**
- `bot/ingestion_wiki_helpers.py` (ENHANCE)

**What it does:**
- `add_bidirectional_links(new_page_path, mentioned_entities)`
  - New page links to existing entity pages
  - Existing entity pages get a "See also: [[new-page]]" backlink
- `find_backlink_candidates(new_page)` → list of pages that should link to this new page

**Exit Condition:**
```bash
cd ~/Documents/PersonalKM
# After ingesting a new file:
grep -c '\[\[' wiki/entities/some-existing-page.md
# Should be > 0 (has wikilinks)

# Check new page has outbound links
grep '\[\[' wiki/entities/new-page.md | head -3
# Should show [[entity-name]] links

# Check existing pages got backlinked
grep 'new-page' wiki/entities/*.md | wc -l
# Should be > 0
```

**Exit Criteria:**
- [ ] Every new wiki page has ≥2 outbound `[[wikilinks]]`
- [ ] Existing pages that mention the new entity get a backlink
- [ ] No broken wikilinks (every `[[link]]` points to existing page)
- [ ] Wikilinks work across entities/ and concepts/ directories

---

## Phase 5: Full Integration Test

**Goal:** All 3 features working together on real data.

**Files:**
- `bot/ingestion.py` (ENHANCE) — wires Phase 1-4 together
- `bot/config.py` (ENHANCE) — adds `MINIMAX_API_KEY`, `MINIMAX_MODEL`

**What it does:**
- On ingestion run: load EntityRegistry, get MiniMax client, run full pipeline
- Process 10-20 real raw files
- Verify: deduplication, summarization, wikilinks all work together

**Exit Condition:**
```bash
cd ~/Documents/PersonalKM
# Run on 10 raw files
python -c "
from bot.ingestion import ingest_raw_to_wiki
from pathlib import Path
result = ingest_raw_to_wiki(Path('.'))
print('Status:', result['status'])
print('Processed:', result['processed'])
print('Created pages:', len(result.get('created_pages', [])))
"

# Verify:
# 1. Created pages are summarized (not raw dump)
# 2. No duplicate entity pages for same entity
# 3. All pages have wikilinks
# 4. No errors in ingestion log
```

**Exit Criteria:**
- [ ] Ingestion runs on 10+ files without errors
- [ ] Pages are distilled (readable in <1 min per page)
- [ ] Entity deduplication: no duplicate entity pages
- [ ] Wikilinks: every page has ≥2 links (in or out)
- [ ] Health check passes after ingestion
- [ ] Git commit with all changes

---

## Configuration

Add to Render environment variables (or `.env` locally):

```bash
MINIMAX_API_KEY=your_m...key
MINIMAX_MODEL=MiniMax-M3        # or MiniMax-M2.7
OPENAI_API_KEY=                 # optional fallback, can be empty
```

---

## Rollback Plan

If any phase fails or degrades quality:

```bash
cd ~/Documents/PersonalKM
git log --oneline -5
# Find last good commit
git checkout <last-good-commit-hash> -- bot/
git checkout <last-good-commit-hash> -- outputs/
# Restart from failed phase
```

**Last good commit:** `500d017` (pre-v2, basic ingestion working)

---

## Phase Execution Order

```
[X] Phase 1: MiniMax Client      ✅ COMPLETE (commit 33dec1a)
[X] Phase 2: AI Summarization    ✅ COMPLETE (commit c51e705)
[X] Phase 3: Entity Deduplication ✅ COMPLETE (commit 5b5c739)
[ ] Phase 4: Bidirectional Wikilinks
[ ] Phase 5: Full Integration
```

Each phase must pass its exit condition before proceeding to the next.

---

## Cost Tracking

| Phase | MiniMax Usage | Est. Cost |
|-------|--------------|-----------|
| Phase 1 | 0 (no API calls yet) | $0 |
| Phase 2 | ~1K tokens/test × 1 test | ~$0.001 |
| Phase 3 | 0 (filesystem only) | $0 |
| Phase 4 | 0 (no API calls) | $0 |
| Phase 5 | ~1K tokens/file × 10 files | ~$0.01 |

**Total estimated cost:** ~$0.01-0.02 for full test

---

## Backward Compatibility

- Existing wiki pages stay as-is (no forced migration)
- Old `bot/ingestion_v1.py` and `bot/ingestion_v2.py` remain as fallbacks
- If `MINIMAX_API_KEY` is not set, pipeline degrades gracefully (skip summarization)
- Cron job continues working with existing logic until Phase 5 complete
