# Wiki Schema — PersonalKM

## Domain

Personal knowledge management for AI/development tools, productivity workflows, and lifestyle content. Captures insights from LINE-shared articles and web content, distilled into scannable, interlinked notes.

**Core areas:**
- AI agents, LLMs, and development tools
- Automation workflows and agent orchestration
- Productivity systems and PKM methodology
- Travel, food, and lifestyle discoveries

## Conventions

- **File names:** lowercase, hyphens, no spaces (e.g., `claude-code.md`, `hermes-agent.md`)
- **Every wiki page starts with YAML frontmatter** (see below)
- **Use `[[wikilinks]]`** to link between pages (minimum 2 outbound links per page)
- **When updating a page, always bump the `updated` date**
- **Every new page must be added to `index.md`** under the correct section
- **Every action must be appended to `log.md`**
- **Provenance markers:** On pages that synthesize 3+ sources, append `^[raw/<category>/source-file.md]`
  at the end of paragraphs whose claims come from a specific source.
- **raw/ files are immutable** — corrections go in wiki pages, never edit raw captures

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [[raw/Tech/source-name]]
# Optional quality signals:
confidence: high | medium | low
contested: true
contradictions: [other-page-slug]
---
```

`sources` uses Obsidian wikilinks (`[[raw/Tech/filename]]`) pointing to the
original capture file in `raw/`. These are clickable in Obsidian — open the
source content directly. Raw files are preserved on disk so links stay alive.

**Legacy:** Old pages may have `sources` as file paths or `[]` — the normalize
script handles both.

## Tag Taxonomy

**AI & Tools:**
- `ai-agent` — autonomous agent frameworks, orchestration
- `llm` — language models, model providers
- `dev-tool` — development tools, editors, CLIs
- `cloud-platform` — cloud services (Cloudflare, AWS, Render, etc.)

**Workflows & Methods:**
- `automation` — workflow automation, triggers, pipelines
- `pkm` — personal knowledge management methodology
- `productivity` — productivity tips, workflows

**Topics:**
- `travel` — travel destinations, itineraries
- `food` — restaurants, dishes, cooking
- `lifestyle` — general lifestyle content

**Meta:**
- `comparison` — side-by-side comparisons
- `timeline` — chronological events, releases
- `opinion` — subjective takes, controversial claims

**Rule:** every tag on a page must appear in this taxonomy. Add new tags here BEFORE using them.

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
- Relationships to other entities (`[[wikilinks]]`)
- Source references

**Examples:** `claude-code.md`, `hermes-agent.md`, `cloudflare.md`, `render.md`

## Concept Pages

One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts (`[[wikilinks]]`)

**Examples:** `multi-agent-workflow.md`, `knowledge-distillation.md`, `wikilinks.md`

## Comparison Pages

Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

**Examples:** `claude-code-vs-hermes-agent.md`, `render-vs-vercel.md`

## raw/ Frontmatter

Raw sources get a small frontmatter block for drift detection:

```yaml
---
source_url: https://example.com/article
ingested: YYYY-MM-DD
sha256: <hex digest of body content>
---
```

## Update Policy

When new information conflicts with existing content:

1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report

## Directory Structure

```
wiki/
├── SCHEMA.md              # This file
├── index.md               # Content catalog
├── log.md                 # Action log (append-only)
├── raw/                   # Layer 1: immutable source captures (symlink to ../raw)
│   ├── Tech/
│   ├── Food/
│   └── General/
├── entities/              # Layer 2: people, products, organizations
├── concepts/              # Layer 2: topics, methods, techniques
├── comparisons/           # Layer 2: side-by-side analyses
├── queries/               # Layer 2: filed query results
└── _archive/             # Archived/superseded pages
```
