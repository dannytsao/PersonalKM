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

> Hard rule 6 overrides steps 2-3 below: commit and push to your **current working branch**, never directly to `main`. Merging into `main` (step 4) is a separate, deliberate action, not something that happens on every commit.

After completing code or configuration changes in this repository:

1. Run the relevant tests or checks for the changed area.
2. Commit the finished changes on your current working branch.
3. Push to `origin <current-branch>`.
4. When ready to ship, merge the branch into `main` — if it's a clean fast-forward (no divergence), `git push origin <branch>:main` does this as a single server-side ref update without needing to check out `main` locally. Otherwise do a real merge on `main` and push that.
5. Confirm the Render service is live by checking:

   `https://personal-km-line-bot.onrender.com/health`

The Render web service is configured with `autoDeploy: true`, so pushing to `main` triggers deployment automatically — this happens at step 4, not at every branch commit.

If step 4's push to `main` is rejected because remote `main` contains new bot-generated note commits, re-fetch, re-verify the fast-forward is still clean (or merge), rerun relevant tests, then push again.

## End-of-Day Trigger

When the user says `call it a day` (or similar), run the end-of-day wrap-up workflow **before closing**. **Updating all project-related documents is a mandatory part of day-end closing — do not skip it.**

> Hard rule 6 overrides the branch target below: end-of-day docs get committed and pushed to your **current working branch**, never directly to `main`. Merging that branch into `main` (see Deployment step 4) is a separate, deliberate action — not a routine part of closing out a day.

1. **Sync the current branch**, and the vault worker separately (it tracks `main`, not your feature branch):
   ```bash
   cd ~/Documents/PersonalKM && git pull --rebase origin <current-branch>
   cd ~/.personalkm/personalkm-vault && git pull --rebase origin main
   ```
2. **Update all project docs** that changed during the session (mandatory):
   - `CHANGELOG.md` — add `## YYYY-MM-DD` entry with all meaningful changes (features, fixes, bugs, architecture)
   - `README.md` — update `Last Updated:` date; add brief note if a major feature or bug fix landed
   - `DESIGN.md` — update `最後更新:` date if architecture or flow changed
   - Any other doc that is now inaccurate or stale (`DOCS-INVENTORY.md` was archived to `docs/archive/` on 2026-07-04 and is no longer actively maintained — do not resurrect it)
3. **Run `git diff --check`** to catch trailing whitespace or merge conflicts.
4. **Commit** with message: `docs: end-of-day wrap-up YYYY-MM-DD`
5. **Push** to `origin <current-branch>`.
6. **Sync vault** — the worker repo only picks up these changes once your branch is merged into `main`; it does not need to run every day.
7. **Confirm** local `HEAD` matches `origin/<current-branch>`. The Render health endpoint reflects `main` only, so it won't change until the branch is merged and deployed.

> All docs live in the same GitHub repo as the vault. A single push to `main` (once merged) updates both the source code repo and the knowledge vault simultaneously.
