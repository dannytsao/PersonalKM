# LLM Wiki Quick Reference

**Wiki Location:** `/Users/dannytsao/Documents/PersonalKM/wiki`

## First Steps (Do This Each Session)

```bash
# Navigate to wiki
cd /Users/dannytsao/Documents/PersonalKM/wiki

# Orient yourself (read these in order):
cat SCHEMA.md      # Domain, conventions, tag taxonomy, page thresholds
cat index.md       # All pages organized by type
tail -30 log.md    # Recent activity
```

## Core Operations

### 1. Ingest a Source (New File from raw/)

```bash
# Example: You have raw/Tech/new-article.md

# Check what entities/concepts to create:
search_files "docker\|kubernetes" path="wiki"

# Agent will:
# 1. Read raw/Tech/new-article.md
# 2. Find mentions of docker, kubernetes, etc.
# 3. Create/update wiki/entities/ or wiki/concepts/ pages
# 4. Add to index.md
# 5. Log action to log.md
```

### 2. Query the Wiki

**Example:** "What do I know about Docker?"

```bash
# Agent will:
# 1. Read index.md to find relevant pages
# 2. Read wiki/entities/ + wiki/concepts/ for Docker
# 3. Synthesize an answer from compiled knowledge
# 4. Cite pages used: "Based on [[entities/docker]] and [[concepts/container-networking]]..."
# 5. Optionally file answer to wiki/queries/ if substantial
```

### 3. Lint the Wiki

**Find issues:**
- Orphan pages (no inbound links)
- Broken wikilinks
- Index completeness
- Invalid frontmatter
- Stale content (>90 days old without updates)
- Contradictions (marked in frontmatter)
- Pages with low confidence

## Tag Taxonomy

Use ONLY tags from SCHEMA.md. Add new tags there first, then use them.

**Domain Tags:** `tech`, `food`, `photography`, `general`
**Topic Tags:** `hermes-agent`, `ai-llm`, `container`, `web-dev`, `travel`, `productivity`, `learning`
**Quality Tags:** `decay-flagged`, `needs-verification`, `wip`, `controversial`, `evergreen`
**Processing:** `from-line`, `from-youtube`, `from-article`, `ai-summarized`, `auto-tagged`, `manual-curated`

## Page Structure

### Frontmatter (Required)

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from_taxonomy_here]
sources: [raw/Tech/filename.md, raw/Food/another.md]
confidence: high | medium | low
contested: false
contradictions: []
---
```

### Entity Pages

*Example: [[entities/docker]]*

- Overview: What it is
- Key facts + dates
- Links to related concepts ([[wikilinks]])
- Source references

### Concept Pages

*Example: [[concepts/container-networking]]*

- Definition
- State of knowledge
- Open questions
- Related concepts

### Comparison Pages

*Example: [[comparisons/docker-vs-podman]]*

- What's being compared + why
- Side-by-side table
- Verdict
- Sources

### Query Pages

*Example: [[queries/docker-best-practices-2026]]*

- Question or thesis
- Synthesized answer from multiple wiki pages
- References to source pages
- Date filed

## Page Thresholds

- **Create a page** if entity/concept appears in 2+ sources OR central to one source
- **Add to existing** if already covered by another page
- **DON'T create** for passing mentions
- **Split** when page exceeds ~200 lines
- **Archive** when superseded (move to `_archive/`, remove from index)

## Wikilinks

Every page must link to at least 2 other pages. Use markdown wikilink syntax:

```markdown
See also: [[entities/kubernetes]] and [[concepts/orchestration]]
```

## Handling Contradictions

When sources conflict:

1. Check dates — newer generally wins
2. Note both positions with dates + sources
3. Mark in frontmatter: `contradictions: [other-page-slug]`
4. Set `contested: true`
5. Flag for user review

## Raw Files Are Immutable

- Never edit `raw/` files after capture
- Corrections go only in wiki pages
- Raw files get sha256 hash for drift detection

## Cross-Domain Linking

Good links to create:
- **Tech ↔ Productivity:** Claude, Hermes → workflow improvements
- **Tech ↔ Food:** Recipe apps, restaurant discovery → tech tools
- **Photography ↔ Travel:** Photo techniques, locations → travel destinations
- **All → General:** Reflections link back to foundational concepts

## Useful Commands

```bash
# Search for content
search_files "transformer" path="$WIKI_PATH" file_glob="*.md"

# Search by tag
search_files "tags:.*ai-llm" path="$WIKI_PATH" file_glob="*.md"

# Find recently updated
find $WIKI_PATH -name "*.md" -mtime -7

# Count pages
find $WIKI_PATH -type f -name "*.md" | wc -l

# Check for orphans (manual)
find $WIKI_PATH -type f -name "*.md" | while read f; do
  links=$(grep -o '\[\[[^]]*\]\]' "$f" | wc -l)
  [ "$links" -lt 2 ] && echo "Orphan: $f ($links links)"
done
```

## Environment Setup

Add to `~/.hermes/.env`:

```bash
WIKI_PATH=/Users/dannytsao/Documents/PersonalKM/wiki
```

Then Hermes llm-wiki skill will use this path for all operations.

## Integration with Obsidian

The wiki is already an Obsidian vault. Open in Obsidian app:

- Wikilinks render as clickable links
- Graph View shows knowledge network
- Dataview queries let you filter by tag
- Search finds across all pages
- Attachments go to `Attachments/` folder

## When to Run Lint

- Weekly minimum
- After bulk ingest (10+ new/updated pages)
- When you suspect broken links or stale content
- Before archiving old pages

Lint returns: orphans, broken links, stale pages (>90 days), contradictions, low-confidence pages, oversized pages

## FAQ

**Q: Can I use any tag?**  
A: No. Only tags in SCHEMA.md. Add new tags there first.

**Q: Should index.md be updated manually?**  
A: No. Agent updates it automatically on ingest/create/delete.

**Q: How long should a page be?**  
A: Aim for 50-150 lines. Split if it exceeds 200.

**Q: What if I disagree with an auto-generated page?**  
A: Edit it directly. It's your wiki — maintain what matters.

**Q: When does decay-flagged trigger?**  
A: Pages >90 days old with time-sensitive content (versions, prices, availability).

**Q: Can I delete a page?**  
A: Yes. Move to `_archive/`, remove from index.md, update any pages that linked to it, log the action.

---

**Last Updated:** 2026-06-13  
**For full details:** Read `SCHEMA.md`, `LLMWIKI-INTEGRATION-CHANGENOTE.md`, and the `llm-wiki` skill
