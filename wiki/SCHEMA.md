# Wiki Schema

## Domain

PersonalKM: A multi-domain knowledge management system integrating LINE messaging, Obsidian vault, and AI-powered enrichment. Captures content across Technology, Food Culture, Photography, and General Observations; processes raw captures through entity extraction, decay analysis, and knowledge synthesis.

## Conventions

- File names: lowercase, hyphens, no spaces (e.g., `transformer-architecture.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date in frontmatter
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** On pages that synthesize 3+ sources, append `^[raw/articles/source-file.md]` or `^[raw/Tech/source.md]` at the end of paragraphs whose claims come from a specific source
- **Raw sources immutable:** Files in `raw/` directory are never edited after initial capture. Corrections exist only in wiki pages.
- **Category hierarchy:** Main categories are Tech, Food, Photography, General. Subcategories organized by entity/concept within the wiki layer

## Frontmatter

All wiki pages (entities/, concepts/, comparisons/, queries/) must have:

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/Tech/source-name.md]
# Optional quality signals:
confidence: high | medium | low        # how well-supported the claims are
contested: false                       # set when the page has unresolved contradictions
contradictions: []                     # pages this one conflicts with
---
```

`confidence` and `contested` are optional but recommended for opinion-heavy or fast-moving topics.

## raw/ Frontmatter

Raw sources also get a frontmatter block so re-ingests can detect drift:

```yaml
---
source_url: https://example.com/article   # original URL, if applicable
ingested: YYYY-MM-DD
sha256: <hex digest of the raw content below the frontmatter>
---
```

The `sha256:` lets future re-ingest of the same URL skip processing when content is unchanged, and flag drift when it has changed.

## Tag Taxonomy

Tags that mark domain, quality, and processing stage. Add new tags here BEFORE using them.

### Domain Tags
- `tech`: Software, DevOps, architecture, AI/ML, tools
- `food`: Restaurants, recipes, culinary techniques, regional cuisines
- `photography`: Visual composition, camera techniques, locations, editing
- `general`: Personal observations, essays, lifestyle reflections

### Topic Tags
- `hermes-agent`: Hermes configuration, usage, agents
- `ai-llm`: LLM models, RAG, inference, alignment, fine-tuning
- `container`: Docker, Kubernetes, container orchestration
- `web-dev`: Frontend, backend, web frameworks, databases
- `travel`: Locations, tourism, local recommendations
- `productivity`: Tools for organization, automation, workflow
- `learning`: Educational content, tutorials, how-tos

### Quality Tags
- `decay-flagged`: Content older than 90 days, needs review
- `needs-verification`: Claims need corroboration or contradicts existing content
- `wip`: Work in progress, incomplete
- `controversial`: Multiple valid interpretations or unresolved debate
- `evergreen`: Timeless content, remains relevant indefinitely

### Processing Tags
- `from-line`: Captured via LINE bot ingestion
- `from-youtube`: Extracted from YouTube transcript
- `from-article`: Sourced from web articles or blogs
- `ai-summarized`: Processed through OpenAI summarization
- `auto-tagged`: Tags added by entity extraction
- `manual-curated`: Manually reviewed and organized

## Page Thresholds

- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside the domain
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages

One page per notable entity. Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities ([[wikilinks]])
- Source references

Examples: Companies (Anthropic, OpenAI), Products (Claude, GPT-4), Tools (Hermes Agent, Docker), Restaurants (named establishments)

## Concept Pages

One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts ([[wikilinks]])

Examples: Transform architectures, container networking, food pairing principles, photography composition

## Comparison Pages

Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

Examples: Docker vs Podman, iPhone vs Android, espresso machines

## Update Policy

When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report

## Cross-Domain Integration

- **Tech ↔ Productivity:** Tech tools (Claude, Hermes) link to workflow improvements
- **Tech ↔ Food:** Food tech (recipe apps, restaurant discovery tools) link to technology concepts
- **Photography ↔ Travel:** Photo locations and techniques link to travel destinations
- **All → General:** Reflections and syntheses link back to foundational concepts

## Decay Management

Pages are automatically flagged with `decay-flagged` tag when:
- Last updated >90 days ago AND
- Contains time-sensitive content (software versions, prices, availability)

Decay reports run weekly; flagged pages appear in `outputs/decay-reports/` for human review.

## Integration with raw/

The `raw/` directory is organized by category (Tech, Food, Photography, General). Each file has immutable frontmatter. The wiki layer synthesizes across raw sources:

```
raw/Tech/        → entities/ai-models/, entities/tools/, concepts/devops/
raw/Food/        → entities/restaurants/, concepts/cuisines/
raw/Photography/ → concepts/composition/, entities/locations/
raw/General/     → concepts/essays/, entities/people/
```
