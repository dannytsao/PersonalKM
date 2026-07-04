# Migration Plan: PersonalKM → split repos + LLM router + agent isolation

Execute in this order. Each step is independently shippable; the pipeline
keeps working between steps.

## Step 1 — Vault split (privacy first, do this before anything else)

1. `brew install git-filter-repo`
2. Run `scripts/migrate_vault_split.sh` on your Mac. It:
   - creates `personalkm-vault` (private) containing only `raw/ wiki/ Attachments/ Trash/`, with history
   - strips those paths from the code repo's history (force push, review first)
3. On the Mac Mini: clone the vault to `~/.personalkm/personalkm-vault`,
   update launchd scripts to pull/push the **vault** repo for content.
4. Render webhook: point its git push target at the vault repo.
5. Obsidian: open the vault repo; disable Obsidian-Git auto-push (or >= 30 min).
6. Verify one full cycle (LINE message → raw appears in vault → hourly run
   → wiki page), then delete stale clones of the old mixed repo.

## Step 2 — Adopt this scaffold into the code repo

1. Copy this scaffold's files into the code repo root.
2. Move existing code into the new layout:
   - `bot/` webhook code      → `src/personalkm/capture/`
   - `scripts/ingest_wiki.py` → split into `src/personalkm/ingest/` (+ `scripts/` thin entrypoints)
   - propagation logic        → `src/personalkm/propagate/`
   - query engine             → `src/personalkm/query/`
3. `pip install -e ".[dev,llm]"` and get `pytest tests/contracts -q` green.
4. Move `CANONICAL_ENTITIES` from Python into
   `vault/wiki/_registry/entities.yaml`; load it via `settings.yaml`.

## Step 3 — LLM router (runtime isolation + automatic budget management)

1. Replace every direct Anthropic / Ollama call in ingest/propagate/query with
   `route("<stage>", prompt, ...)` from `personalkm.llm.router`.
2. Tune `config/models.yaml`:
   - set real daily budgets matching your plan quotas
   - decide per-stage primaries (expensive synthesis vs cheap extraction)
3. Delete any `skip_llm` / silent-fallback code paths — `LLMError` must
   propagate so the raw note stays pending and gets retried next hour.
4. Add to the hourly runner: on `LLMError` or any exception, push a LINE
   alert to yourself; also `python -m personalkm.llm.usage report` daily.

## Step 4 — Dev isolation (multi-agent)

1. Commit `AGENTS.md` + the `CLAUDE.md`/`GEMINI.md` symlinks + `.gitignore`.
2. Tell each agent: read the repo root instructions; scratch in `.agent/<name>/`;
   contracts must pass before commit; one branch per agent
   (`git worktree add ../pkm-<task> -b <task>` for parallel work).
3. Optional: pre-commit hook running `pytest tests/contracts -q` so no agent
   can commit red.

## Step 5 — Resolver layer (from earlier design discussion)

1. Implement adapters in `src/personalkm/resolve/adapters/`
   (youtube via yt-dlp, github via raw README, generic via readability).
2. Wire `resolve_sources()` as the first stage of the hourly run, before
   ingest; only `fetch_status: fetched` notes proceed to LLM synthesis.
3. Extend `sanity_check` to flag stub pages and `failed_final` notes.
