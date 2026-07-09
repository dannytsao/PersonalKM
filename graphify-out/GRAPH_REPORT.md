# Graph Report - .  (2026-07-09)

## Corpus Check
- 143 files · ~85,994 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1201 nodes · 2383 edges · 87 communities (58 shown, 29 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 104 edges (avg confidence: 0.75)
- Token cost: 405,674 input · 0 output

## Community Hubs (Navigation)
- Link Processor & Content Clipping
- Frontmatter Normalization Scripts
- Archived Status & Ingestion History
- LLM Provider Base Interface
- Ingestion V1 & App Integration
- Ollama Wikilink Analyzer
- Entity Dedup & Ingestion V2
- Entity Registry Core
- Entity Backfill & Frontmatter Parsing
- Wikilinks Manager Rationale
- Ingestion Health Check System
- Notification System
- Agent Hard Rules & Pipeline Stages
- Deployment Workflow & Changelog
- Legacy Ingestion Pipeline
- Bot App Core (LINE Capture)
- Query Engine
- LINE Webhook Capture
- Note Rendering & Slugify
- Sanity Check & Repair Script
- Config & Git Store
- LLM Client Providers
- Entity Name Extraction
- Knowledge Decay Detection
- Archive Inbox Script
- Wiki Index Rationale
- Related Pages & Wikilink Integration
- Resolver Adapter Base
- Ingest Health Check (src layout)
- Vault Separation Philosophy
- Canonical Entity Phase 6
- Knowledge Graph Builder (Mermaid)
- LLM Summarizer Core
- Wiki V2 Migration
- Content Quality Checker
- MiniMax LLM Client
- Model Routing Config
- Running Log / Retry Tracking
- Wiki Schema & Taxonomy
- SPEC Pipeline Layers
- Topic Tags Migration Script
- LLM Wiki Integration Tests
- Knowledge Decay Guide & Capture Goal
- OpenAI LLM Client
- Ingestion Status Checker Script
- Copilot Captured Entities
- LLM Usage & Budget Tracking
- Phase A Ingest Wiki Script
- Raw Frontmatter Migration Script
- Obsidian Copilot Advice Conversations
- Resolve Fetch Status Enum
- Frontmatter Schema Contract Test
- Fix Broken Wikilinks Script
- Mac Mini Phase A Runner
- Mac Mini Phase B Runner
- Mac Mini Worker Runner
- Test Ingestion Script
- Bot Package Init
- YouTube Transcript Clip & Dataview Query
- Mac Mini Phase A LaunchAgent Installer
- Mac Mini Phase B LaunchAgent Installer
- Mac Mini Worker LaunchAgent Installer
- Vault Split Migration Script
- Mac Mini Worker LaunchAgent Uninstaller
- Capture Package Init
- Ingest Package Init
- Propagate Package Init
- Query Package Init
- Contracts Tests Init
- Omnichannel Tools Init
- Emojify Prompt
- Explain Like I'm 5 Prompt
- Fix Grammar & Spelling Prompt
- Generate Glossary Prompt
- Generate Table of Contents Prompt
- Make Longer Prompt
- Make Shorter Prompt
- Remove URLs Prompt
- Rewrite as Tweet Prompt
- Rewrite as Tweet Thread Prompt
- Simplify Prompt
- Summarize Prompt
- Translate to Chinese Prompt
- PersonalKM Package Root
- Cloudflare Migration Plan (Stub)

## God Nodes (most connected - your core abstractions)
1. `ExtractedContent` - 29 edges
2. `process_url()` - 28 edges
3. `EntityRegistry` - 26 edges
4. `Settings` - 24 edges
5. `LinkNote` - 22 edges
6. `WikilinkManager` - 22 edges
7. `IngestionHealthCheck` - 20 edges
8. `to_note()` - 20 edges
9. `PersonalKM Agent Instructions (Single Source of Truth)` - 20 edges
10. `ingest_file_v2()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Phase A: LINE -> Raw -> Wiki Entities (Mac Mini)` --semantically_similar_to--> `Ingest stage / Phase A (src/personalkm/ingest/)`  [INFERRED] [semantically similar]
  DESIGN.md → AGENTS.md
- `Phase B: Wikilink post-linking (Ollama qwen3:8b)` --semantically_similar_to--> `Propagate stage / Phase B (src/personalkm/propagate/)`  [INFERRED] [semantically similar]
  DESIGN.md → AGENTS.md
- `Query interface (CLI + web GET /query, hybrid search)` --semantically_similar_to--> `Query stage (src/personalkm/query/)`  [INFERRED] [semantically similar]
  DESIGN.md → AGENTS.md
- `Food note structured extraction (places[] schema)` --semantically_similar_to--> `Wiki frontmatter schema contract v1`  [INFERRED] [semantically similar]
  IMPROVEMENT-BACKLOG.md → README.md
- `Copilot custom prompt: Clip Web Page` --semantically_similar_to--> `Wiki frontmatter schema contract v1`  [INFERRED] [semantically similar]
  copilot/copilot-custom-prompts/Clip Web Page.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Capture -> Resolve -> Ingest -> Propagate -> Query pipeline with LLM router** — agents_capture_stage, agents_resolve_stage, agents_ingest_stage, agents_propagate_stage, agents_query_stage, agents_llm_router [EXTRACTED 1.00]
- **AGENTS.md hard rules / guardrails set** — agents_hard_rule_never_touch_vault, agents_hard_rule_no_provider_names_outside_llm, agents_hard_rule_no_silent_llm_fallback, agents_hard_rule_frontmatter_schema_contract, agents_hard_rule_scratch_space, agents_hard_rule_one_agent_one_branch [EXTRACTED 1.00]
- **Canonical entity dedup pattern (EntityRegistry + Phase 6 architecture + backlog work item)** — changelog_entity_registry, design_phase_6_canonical_entity, ib_canonical_entity_pages_phase6 [INFERRED 0.85]
- **Copilot Custom Prompt Library** — copilot_copilot_custom_prompts_clip_youtube_transcript_prompt, copilot_copilot_custom_prompts_emojify_prompt, copilot_copilot_custom_prompts_explain_like_i_am_5_prompt, copilot_copilot_custom_prompts_fix_grammar_and_spelling_prompt, copilot_copilot_custom_prompts_generate_glossary_prompt, copilot_copilot_custom_prompts_generate_table_of_contents_prompt, copilot_copilot_custom_prompts_make_longer_prompt, copilot_copilot_custom_prompts_make_shorter_prompt, copilot_copilot_custom_prompts_remove_urls_prompt, copilot_copilot_custom_prompts_rewrite_as_tweet_thread_prompt, copilot_copilot_custom_prompts_rewrite_as_tweet_prompt, copilot_copilot_custom_prompts_simplify_prompt, copilot_copilot_custom_prompts_summarize_prompt, copilot_copilot_custom_prompts_translate_to_chinese_prompt [INFERRED 0.85]
- **Scheduled Vault Maintenance & Monitoring Jobs** — docs_health_check_system_health_check_system, docs_archive_decay_system_complete_knowledge_decay_system, docs_render_cron_troubleshooting_guide [INFERRED 0.75]
- **Bot Feature Rollout Pipeline (commit to GitHub, Render autoDeploy)** — docs_archive_deployment_complete_md_option_b_deployment, docs_archive_deployment_complete_txt_hermes_enrich_deployment, docs_archive_decay_system_complete_knowledge_decay_system [INFERRED 0.75]
- **Ingestion Pipeline Reliability & Observability System** — docs_archive_quality_filtering_content_quality_checker, docs_archive_running_logs_and_retry_running_log, docs_archive_running_logs_and_retry_auto_retry, docs_archive_ingestion_improvements_health_check_module [INFERRED 0.85]
- **LLM Wiki v2 Ingestion Pipeline (MiniMax + Summarization + Dedup + Wikilinks)** — docs_llm_wiki_v2_plan_minimax_client, docs_llm_wiki_v2_plan_ai_summarization, docs_llm_wiki_v2_plan_entity_dedup, docs_llm_wiki_v2_plan_bidirectional_wikilinks [EXTRACTED 1.00]
- **LINE Bot + Obsidian Architecture Pillars (Render + GitHub queue + Mac mini worker)** — docs_archive_line_bot_obsidian_render_web_service, docs_archive_line_bot_obsidian_github_durable_queue, docs_archive_line_bot_obsidian_mac_mini_worker [EXTRACTED 1.00]

## Communities (87 total, 29 thin omitted)

### Community 0 - "Link Processor & Content Clipping"
Cohesion: 0.06
Nodes (96): AsyncClient, BeautifulSoup, blocked_platform_content(), canonical_body_markdown(), clean_food_value(), clipped_markdown_text(), content_type_for_platform(), dedupe_food_places() (+88 more)

### Community 1 - "Frontmatter Normalization Scripts"
Cohesion: 0.06
Nodes (72): youtube_video_id(), _extract_tags_raw(), main(), _parse_fm_text(), Path, Rebuild a wiki file with normalised frontmatter.      1. Deduplicate keys     2., Minimal key:value parser returning {key: raw_value_string}., Extract the raw tag value(s) following a ``tags:`` key in frontmatter.      Hand (+64 more)

### Community 2 - "Archived Status & Ingestion History"
Cohesion: 0.05
Nodes (55): Documentation Inventory (DOCS-INVENTORY.md), Auto-Retry Deliverable, Weekly Cron Scheduling (Option A, Sunday 07:00 UTC+8), PersonalKM Ingestion System Production-Ready Status Report, Phase 1-5 Rollout Tracking, Quality Filtering Deliverable, Running Logs Deliverable, enrich_note() function (bot/hermes_enrich.py) (+47 more)

### Community 3 - "LLM Provider Base Interface"
Cohesion: 0.08
Nodes (31): Completion, LLMError, parse_json_strict(), Provider, ABC, Provider-agnostic LLM interface.  Pipeline code must ONLY depend on this module, Raised when a stage cannot get a valid completion from any model.      Callers m, One concrete backend (Anthropic API, local Ollama, ...). (+23 more)

### Community 4 - "Ingestion V1 & App Integration"
Cohesion: 0.05
Nodes (48): bot/app.py (modified to call analyze_on_capture on every note), bot/app.py (modified to call hermes_enrich after note creation, before commit), bot/hermes_enrich.py (AI enrichment: auto-tagging + summarization, non-blocking), build_knowledge_graph(), categorize_note(), extract_entities_ai(), generate_ingestion_report(), ingest_raw_to_wiki() (+40 more)

### Community 5 - "Ollama Wikilink Analyzer"
Cohesion: 0.07
Nodes (43): call_ollama(), _extract_tag(), _extract_wikilinks(), OllamaWikilinkAnalyzer, parse_wikilink_output(), Ollama Wikilink Analyzer — Phase B (Post-Link) =================================, Extract content between <TAG_NAME> and </TAG_NAME>., Extract wikilink slugs from a parsed section.      Input: "- [[claude-code]]\n- (+35 more)

### Community 6 - "Entity Dedup & Ingestion V2"
Cohesion: 0.11
Nodes (31): canonical_slug_from_name(), normalize_entity_name(), Normalize an entity name to a consistent slug.          Examples:         "Claud, Given a raw entity name, return the canonical slug if it matches.          Examp, _add_canonical_body_links(), _add_capture_to_entity(), _auto_promote_entities(), _classify_page_type() (+23 more)

### Community 7 - "Entity Registry Core"
Cohesion: 0.08
Nodes (19): EntityRegistry, Index of all existing entities in the wiki.          Phase 6: now supports canon, Return number of indexed entities., Return number of canonical entity pages., Find if an entity already exists in the wiki.                  Phase 6: checks i, Return all indexed entity names (normalized)., Return all canonical entity slugs., Return True if entity with this name exists. (+11 more)

### Community 8 - "Entity Backfill & Frontmatter Parsing"
Cohesion: 0.11
Nodes (31): is_canonical_slug(), parse_frontmatter(), Parse frontmatter from markdown content string.          Returns (fm_dict, body_, Check if a slug is a known canonical entity name., detect_entity_mentions(), Detect entity mentions in content using simple pattern matching.      Returns li, Remove ALL YAML frontmatter blocks from markdown content.          Handles:, _strip_frontmatter() (+23 more)

### Community 9 - "Wikilinks Manager Rationale"
Cohesion: 0.11
Nodes (17): Path, Normalize an entity name to a wikilink slug., Resolve a normalized entity slug to an existing wiki file path.         Checks b, Ensure the page has wikilinks to all mentioned entities.         Adds [[slug]] s, Find plain-text mentions of an entity in content and convert to wikilinks., Add backlinks from existing entity pages TO the new page.                  When, Append a backlink to a page's body.                  Looks for a "See also" sect, Extract all wikilink entities from a page's content.                  Returns li (+9 more)

### Community 10 - "Ingestion Health Check System"
Cohesion: 0.10
Nodes (14): IngestionHealthCheck, Path, Post-ingestion health check and validation system. Ensures data integrity and de, Validate frontmatter on 5 random wiki files., Comprehensive validation of ingestion results., Validate index.md structure and content., Validate log.md structure., Validate knowledge-graph.md (optional). (+6 more)

### Community 11 - "Notification System"
Cohesion: 0.13
Nodes (24): notify(), notify_ingestion_failure(), notify_ingestion_start(), notify_ingestion_success(), Send notification via all configured methods.      Args:         title: Notifica, Notify that ingestion has started., Notify that ingestion completed successfully., Notify that ingestion failed. (+16 more)

### Community 12 - "Agent Hard Rules & Pipeline Stages"
Cohesion: 0.17
Nodes (25): PersonalKM Agent Instructions (Single Source of Truth), Definition of done (pytest tests/contracts), Hard rule: frontmatter schema is a contract, Hard rule: no provider names outside llm/, Hard rule: no silent LLM fallbacks (raise LLMError), Hard rule: scratch space under .agent/<name>/, Ingest stage / Phase A (src/personalkm/ingest/), LLM router (src/personalkm/llm/, personalkm.llm.router) (+17 more)

### Community 13 - "Deployment Workflow & Changelog"
Cohesion: 0.11
Nodes (25): Deployment workflow (branch -> merge to main -> autoDeploy), End-of-Day Trigger workflow ('call it a day'), Hard rule: one agent, one branch, Changelog (consolidated implementation history), bot/ingestion_v2.py integrated pipeline, Mac mini omnichannel worker (2026-06-10), scripts/query_wiki.py CLI query interface, raw/wiki/outputs system (Phase 1+4, 2026-06-07) (+17 more)

### Community 14 - "Legacy Ingestion Pipeline"
Cohesion: 0.16
Nodes (23): build_knowledge_graph(), build_llmwiki_frontmatter(), categorize_note(), extract_entities_ai(), generate_ingestion_report(), generate_tags_llm(), ingest_raw_to_wiki(), organize_note_to_wiki() (+15 more)

### Community 15 - "Bot App Core (LINE Capture)"
Cohesion: 0.21
Nodes (19): collect_line_message_part(), _commit_and_push_wiki(), generate_line_log_id(), line_log_sequence_path(), line_parts_path(), load_line_log_sequence(), load_line_parts(), Path (+11 more)

### Community 16 - "Query Engine"
Cohesion: 0.16
Nodes (20): answer_with_llm(), build_llm_context(), display_cli(), _extract_wikilinks(), main(), _parse_frontmatter(), Path, query_wiki() (+12 more)

### Community 17 - "LINE Webhook Capture"
Cohesion: 0.20
Nodes (19): BackgroundTasks, capture_line_messages(), line_webhook(), mark_line_event_as_read(), canonicalize_url(), extract_urls(), is_noise_url(), LineTextEvent (+11 more)

### Community 18 - "Note Rendering & Slugify"
Cohesion: 0.23
Nodes (18): LinkNote, note_filename(), note_target_dir(), Path, Render a raw note as pure markdown body (no YAML frontmatter).      YAML was pre, render_note(), slugify(), write_note() (+10 more)

### Community 19 - "Sanity Check & Repair Script"
Cohesion: 0.14
Nodes (20): _add_frontmatter_delimiter(), check_and_repair(), _clean_extra_fields(), _clean_sources(), _ensure_date_fields(), _ensure_type(), _fix_source_path(), _flatten_nested_tags() (+12 more)

### Community 20 - "Config & Git Store"
Cohesion: 0.23
Nodes (16): BaseSettings, capture_urls(), query_vault(), Search the vault with natural language. Returns JSON with matched pages., save_note(), get_settings(), Settings, commit_and_push() (+8 more)

### Community 21 - "LLM Client Providers"
Cohesion: 0.16
Nodes (17): get_default_client(), get_llm_info(), get_minimax_client(), get_openai_client(), _is_local_base_url(), LLMClientInfo, NoOpClient, _probe_ollama() (+9 more)

### Community 22 - "Entity Name Extraction"
Cohesion: 0.14
Nodes (16): add_source_to_frontmatter(), append_to_body(), extract_entity_name_from_path(), extract_entity_name_from_title(), Path, Entity Deduplication for PersonalKM LLM-Wiki v2 (Phase 6)  Phase 6 adds canonica, Extract a meaningful entity name from a wiki file path.          Examples:, Extract entity name from the title: field in frontmatter. (+8 more)

### Community 23 - "Knowledge Decay Detection"
Cohesion: 0.17
Nodes (17): add_deprecation_notice(), analyze_with_ai(), calculate_freshness_level(), detect_version_references(), generate_report(), get_note_metadata(), openai_client(), Path (+9 more)

### Community 24 - "Archive Inbox Script"
Cohesion: 0.27
Nodes (17): archive(), collect_archive_moves(), collect_moves(), frontmatter_status(), inbox_notes(), main(), PlannedMove, Path (+9 more)

### Community 25 - "Wiki Index Rationale"
Cohesion: 0.13
Nodes (9): Maintain wiki/index.md., Parse index.md into sections., Add entry to index. Return True if added/updated, False if duplicate., Remove entry from index., Write index.md to disk., Append action to log., Rotate log when it exceeds max_entries., Build YAML frontmatter string. (+1 more)

### Community 26 - "Related Pages & Wikilink Integration"
Cohesion: 0.17
Nodes (11): find_related_pages(), integrate_wikilinks(), LLM-Wiki Integration Helpers Maintains index.md, log.md, and wiki navigation for, Represent a wiki page with frontmatter., Extract YAML frontmatter and body., Extract one-line summary from page body., Extract all [[wikilinks]] from content., Add a wikilink to content if not already present. (+3 more)

### Community 27 - "Resolver Adapter Base"
Cohesion: 0.15
Nodes (11): Always fails — use only for testing., Exception, Adapter, AuthWallError, FetchedContent, GoneError, ABC, Adapter interface + URL classification.  One adapter per source family. Determin (+3 more)

### Community 28 - "Ingest Health Check (src layout)"
Cohesion: 0.18
Nodes (13): _check_frontmatter(), _check_url_platform(), print_summary(), Any, Path, Pre-ingestion raw note quality check.  Scans raw/ notes before the weekly ingest, Check if the note's URL is from a blocked platform., Scan every .md file under *vault_path*/raw/ and return a quality report.      Re (+5 more)

### Community 29 - "Vault Separation Philosophy"
Cohesion: 0.16
Nodes (15): Hard rule: never touch the vault, Philosophy: 我存，AI 整理，我問, Vault split into private repo (2026-07-05), config/settings.yaml - non-secret runtime settings, vault.path setting (local clone of private content repo), Copilot custom prompt: Clip Web Page, Food note structured extraction (places[] schema), Step 1: Vault split into private repo (done) (+7 more)

### Community 30 - "Canonical Entity Phase 6"
Cohesion: 0.17
Nodes (15): Phase 6 canonical entity dedup (2026-06-28), bot/entity_dedup.py EntityRegistry, bot/llm_summarizer.py distill_to_markdown, Copilot conversation: No NotebookLM Obsidian Integration, Question: linking Obsidian with Google NotebookLM (unanswered - not in vault), Copilot conversation: Obsidian-NotebookLM Integration, Phase 6: Canonical Entity Architecture (2026-06-28), Phase 6: Canonical Entity Pages + True Dedup (work item) (+7 more)

### Community 31 - "Knowledge Graph Builder (Mermaid)"
Cohesion: 0.29
Nodes (12): _build_index(), build_knowledge_graph(), _build_mermaid(), _collect_edges(), _display_name(), _link_path(), Path, Knowledge Graph Generator for PersonalKM ======================================= (+4 more)

### Community 32 - "LLM Summarizer Core"
Cohesion: 0.23
Nodes (12): get_llm_client(), Get the default LLM client (singleton pattern).          Caches the client after, _fallback_summarize(), _is_frontmatter_line(), _parse_json_response(), Any, AI Summarizer for PersonalKM LLM-Wiki v2  Distills raw captures into concise, st, Check if a line looks like a YAML frontmatter key: value pair. (+4 more)

### Community 33 - "Wiki V2 Migration"
Cohesion: 0.21
Nodes (12): distill_to_markdown(), Convert summarization result into wiki markdown body.      Args:         result:, Convert text to a slug identifier., _slugify(), extract_frontmatter(), inject_body(), main(), migrate_file() (+4 more)

### Community 34 - "Content Quality Checker"
Cohesion: 0.23
Nodes (7): ContentQualityChecker, Path, Extract body content (excluding frontmatter)., Extract summary field from frontmatter., Check if file is low quality (stub/placeholder).         Returns: (is_low_qualit, Return path to log file., Check if raw content meets minimum quality thresholds.

### Community 35 - "MiniMax LLM Client"
Cohesion: 0.20
Nodes (7): MiniMaxClient, Any, Fallback using requests when OpenAI SDK unavailable., Return list of available models., Check if client can make API calls., MiniMax Chat Completions API client.          OpenAI-compatible — uses the same, Create a chat completion.                  Args:             model: Model ID (e.

### Community 36 - "Model Routing Config"
Cohesion: 0.41
Nodes (12): Daily token budgets per provider, config/models.yaml - per-stage LLM routing config, Provider: claude (anthropic), Provider: minimax (openai_compat), Provider: ollama (local), Provider: openai (openai_compat), Stage: entity_extraction (cheap structured extraction), Stage: ingest_synthesis (Phase A wiki note synthesis) (+4 more)

### Community 37 - "Running Log / Retry Tracking"
Cohesion: 0.33
Nodes (3): Real-time ingestion progress log., Log a processing step., RunningLog

### Community 38 - "Wiki Schema & Taxonomy"
Cohesion: 0.24
Nodes (6): Parse and manage wiki/SCHEMA.md tag taxonomy., Parse SCHEMA.md to extract tag taxonomy., Fallback taxonomy from SCHEMA.md defaults., Return flat list of all valid tags., Validate tags against taxonomy. Return (valid, invalid)., WikiSchema

### Community 39 - "SPEC Pipeline Layers"
Cohesion: 0.20
Nodes (11): _propagate_to_entity_pages() capture propagation, GET /query FastAPI web endpoint, Gate: all 29 checklist items -> Distillation Loop implementation, alerts config (line_notify_on_failure, heartbeat_max_silence_hours), G3 Knowledge Distillation goal (captures accumulate on canonical entity page), 第一層 Capture (我存) - Render webhook, Entity Distillation Loop spec (第二節), LLM 自動管理 (automatic model switching + LLMError alerts) (+3 more)

### Community 40 - "Topic Tags Migration Script"
Cohesion: 0.33
Nodes (10): extract_body(), has_topic_field(), main(), migrate_frontmatter(), migrate_page(), migrate_with_llm(), Path, Use LLM to determine topic + tags, then apply structural migration. (+2 more)

### Community 41 - "LLM Wiki Integration Tests"
Cohesion: 0.29
Nodes (9): main(), Test LLM-Wiki frontmatter generation., Test ingestion with fake data., Test WikiSchema, WikiIndex, WikiLog classes., Test note categorization., test_categorization(), test_fake_ingestion(), test_frontmatter_generation() (+1 more)

### Community 42 - "Knowledge Decay Guide & Capture Goal"
Cohesion: 0.25
Nodes (9): Captured URL - Yahoo News: Meihua Blossom Sea Scenic Spots, Capture stage (src/personalkm/capture/, LINE webhook), Knowledge decay detection concept + monthly report workflow, Decay detection architecture (capture -> enrich -> analyze -> commit; monthly scan), Automatic deprecation notices on outdated notes, Freshness scoring (CRITICAL/HIGH/MEDIUM/EVERGREEN), Monthly decay digest report (1st of month, 9AM), Knowledge Decay Detection System - Implementation Guide (+1 more)

### Community 43 - "OpenAI LLM Client"
Cohesion: 0.22
Nodes (5): OpenAIClient, OpenAI Chat Completions API client.          Used as fallback when MiniMax is un, Create a chat completion via OpenAI., Return list of available models., Check if client can make API calls.

### Community 44 - "Ingestion Status Checker Script"
Cohesion: 0.25
Nodes (8): check_health(), get_ingestion_status(), print_status_report(), Path, Independent status check tool for PersonalKM. Provides deep insight into ingesti, Pretty print status report., Run full health check using IngestionHealthCheck class., Get current ingestion status by inspecting actual state.

### Community 45 - "Copilot Captured Entities"
Cohesion: 0.29
Nodes (8): Wiki entity: Anges AI ([[anges-ai]]), Wiki entity: GLM-5.2 ([[glm-5-2]]), Copilot conversation: GLM-5.2 Explained, Wiki entity: 055 Lobster Seafood Restaurant, Wiki entity: New Taipei five-star hotel buffet, Wiki entity: OpenClaw ([[OpenClaw]]), Wiki entity: Ruilong Waterfall Park ([[ruilong-waterfall-park]]), hermes-agent.md canonical entity example

### Community 46 - "LLM Usage & Budget Tracking"
Cohesion: 0.43
Nodes (7): is_over_budget(), _load(), Daily token accounting per provider.  This is what makes LLM management *automat, record(), report(), _save(), today_total()

### Community 47 - "Phase A Ingest Wiki Script"
Cohesion: 0.52
Nodes (6): _commit_and_push_wiki(), Path, Commit and push any wiki/ changes created by ingest_raw_to_wiki()., Pull latest from GitHub, run ingest_raw_to_wiki, push wiki/ changes.      Args:, run_git(), run_phase_a()

### Community 48 - "Raw Frontmatter Migration Script"
Cohesion: 0.38
Nodes (6): main(), migrate_file(), Path, Remove YAML frontmatter block from markdown, return body only.      Handles:, Migrate a single raw/ file. Returns True if changed., strip_frontmatter()

### Community 49 - "Obsidian Copilot Advice Conversations"
Cohesion: 0.33
Nodes (6): Backlinks + Graph View (Obsidian core features), Copilot conversation: Obsidian Personal Wiki Advice, Dataview plugin (querying/displaying note data), Zettelkasten method (atomic notes, interlinking), Copilot conversation: Taipei Restaurants Status, Advice: vault note titling/tagging for @vault search

### Community 50 - "Resolve Fetch Status Enum"
Cohesion: 0.47
Nodes (5): Enum, FetchStatus, next_status(), fetch_status state machine for raw notes.  Lifecycle (stored in raw note frontma, str

### Community 51 - "Frontmatter Schema Contract Test"
Cohesion: 0.47
Nodes (5): _frontmatter(), Path, CONTRACT: wiki/raw note frontmatter schema.  Any agent changing the schema must, test_raw_fixtures_conform(), test_wiki_fixtures_conform()

### Community 52 - "Fix Broken Wikilinks Script"
Cohesion: 0.50
Nodes (4): fix_file(), main(), Path, Remove ## Related Entities section from a file body.

### Community 53 - "Mac Mini Phase A Runner"
Cohesion: 0.67
Nodes (3): log(), PATH, run_mac_mini_phase_a.sh script

### Community 54 - "Mac Mini Phase B Runner"
Cohesion: 0.67
Nodes (3): log(), PATH, run_mac_mini_phase_b.sh script

### Community 55 - "Mac Mini Worker Runner"
Cohesion: 0.67
Nodes (3): log(), PATH, run_mac_mini_worker.sh script

## Knowledge Gaps
- **71 isolated node(s):** `personalkm`, `install_mac_mini_phase_a_launchd.sh script`, `install_mac_mini_phase_b_launchd.sh script`, `install_mac_mini_worker_launchd.sh script`, `migrate_vault_split.sh script` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IngestionHealthCheck` connect `Ingestion Health Check System` to `Ingestion V1 & App Integration`, `Ingestion Status Checker Script`, `Legacy Ingestion Pipeline`, `Entity Dedup & Ingestion V2`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `WikilinkManager` connect `Wikilinks Manager Rationale` to `Entity Backfill & Frontmatter Parsing`, `Entity Dedup & Ingestion V2`, `Entity Registry Core`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `route()` connect `LLM Provider Base Interface` to `Query Engine`, `Entity Dedup & Ingestion V2`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ExtractedContent` (e.g. with `Settings` and `LinkNote`) actually correct?**
  _`ExtractedContent` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `Settings` (e.g. with `ExtractedContent` and `FoodPlace`) actually correct?**
  _`Settings` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `LINE Bot to Obsidian link capture package.`, `Search the vault with natural language. Returns JSON with matched pages.`, `Commit and push any wiki/ changes created by ingest_raw_to_wiki().     Runs afte` to the rest of the system?**
  _356 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Link Processor & Content Clipping` be split into smaller, more focused modules?**
  _Cohesion score 0.05891016200294551 - nodes in this community are weakly interconnected._