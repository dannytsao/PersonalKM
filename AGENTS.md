# PersonalKM — Agent Instructions (Single Source of Truth)

> CLAUDE.md and GEMINI.md are symlinks to this file. Edit ONLY this file.
> All coding agents (Claude Code, Gemini CLI, Codex, ...) follow these rules.

## What this project is

A personal knowledge management pipeline: LINE Bot captures → raw notes →
resolver fetches/converts sources → LLM synthesizes wiki notes → propagation
updates entity pages. Philosophy: 我存，AI 整理，我問.

## Repo layout

- `src/personalkm/capture/`    LINE webhook (FastAPI, runs on Render). Must stay dumb: receive → write raw → push. NO fetching, NO LLM here.
- `src/personalkm/resolve/`    URL classification + per-source adapters (youtube/github/news/...). Deterministic code only, NO LLM here.
- `src/personalkm/ingest/`     Phase A: raw + fetched content → wiki note synthesis (LLM).
- `src/personalkm/propagate/`  Phase B: entity page updates.
- `src/personalkm/query/`      Query engine.
- `src/personalkm/llm/`        The ONLY place provider SDKs may be imported. Everything else calls `llm.router`.
- `config/models.yaml`         Per-stage model routing + budgets. The ONLY place model names may appear.
- `tests/contracts/`           Behavioral invariants. See "Definition of done".

## Hard rules (guardrails)

1. **Never touch the vault.** Knowledge content lives in a separate private
   repo (`personalkm-vault`), whose local path comes from
   `config/settings.yaml`. Agents must never create, edit, or delete files
   under the vault path. Tests use `tests/fixtures/` instead.
2. **No provider names outside `src/personalkm/llm/` and `config/models.yaml`.**
   Business logic imports `from personalkm.llm.router import route` — never
   `anthropic`, `openai`, `google.generativeai`, `ollama`, etc.
3. **No silent LLM fallbacks.** If a model call fails or returns unparseable
   JSON after retries, raise `LLMError`. Producing a page without real LLM
   synthesis (`skip_llm`) is a bug, not a feature.
4. **Frontmatter schema is a contract.** Do not add/rename wiki frontmatter
   fields without updating `tests/contracts/test_frontmatter_schema.py` in
   the same commit.
5. **Scratch space:** put your plans, TODOs, and temp files under
   `.agent/<your-name>/`. It is gitignored. Never commit files there,
   and never write scratch files anywhere else in the repo.
6. **One agent, one branch.** Work on a feature branch (or a git worktree if
   running in parallel with another agent). Never commit directly to `main`.

## Definition of done (every change, every agent)

```bash
pip install -e ".[dev]"        # once
pytest tests/contracts -q      # MUST be green before any commit
pytest -q                      # full suite before opening a PR/merge
```

If contracts fail, fix the code — do not edit the contract to make it pass,
unless the task explicitly says the contract itself is changing.

## Common commands

```bash
uvicorn personalkm.capture.app:app --reload   # run webhook locally
python -m personalkm.ingest.run               # run Phase A once (uses fixtures if vault not configured)
python -m personalkm.llm.usage report         # show today's token spend per provider
```

## Style

- Python 3.11+, type hints on public functions, `ruff` clean.
- Small modules; adapters must implement `resolve.adapters.base.Adapter`.
- Log with `logging`, never `print`, in library code.

---

# Operational Workflows (existing rules, kept)

## Deployment

After completing code or configuration changes in this repository:

1. Run the relevant tests or checks for the changed area.
2. Commit the finished changes on `main`.
3. Push to `origin main`.
4. Confirm the Render service is live by checking:

   `https://personal-km-line-bot.onrender.com/health`

The Render web service is configured with `autoDeploy: true`, so pushing to `main` triggers deployment automatically.

If the push is rejected because remote `main` contains new bot-generated note commits, run `git pull --rebase origin main`, rerun relevant tests, then push again.

## End-of-Day Trigger

When the user says `call it a day` (or similar), run the end-of-day wrap-up workflow **before closing**. **Updating all project-related documents is a mandatory part of day-end closing — do not skip it.**

1. **Sync both repos** with `origin/main`:
   ```bash
   cd ~/Documents/PersonalKM && git pull --rebase origin main
   cd ~/.personalkm/PersonalKM-worker && git pull --rebase origin main
   ```
2. **Update all project docs** that changed during the session (mandatory):
   - `CHANGELOG.md` — add `## YYYY-MM-DD` entry with all meaningful changes (features, fixes, bugs, architecture)
   - `README.md` — update `Last Updated:` date; add brief note if a major feature or bug fix landed
   - `DESIGN.md` — update `最後更新:` date if architecture or flow changed
   - `DOCS-INVENTORY.md` — update `更新日期:` if doc structure changed
   - Any other doc that is now inaccurate or stale
3. **Run `git diff --check`** to catch trailing whitespace or merge conflicts.
4. **Commit** with message: `docs: end-of-day wrap-up YYYY-MM-DD`
5. **Push** to `origin main`.
6. **Sync vault** (worker repo pulls the same commit).
7. **Confirm** local `HEAD` matches `origin/main` in both repos and Render health endpoint is live.

> All docs live in the same GitHub repo as the vault. A single push updates both the source code repo and the knowledge vault simultaneously.
