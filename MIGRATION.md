# Migration Plan: PersonalKM — 分階段重構

> 最後更新：2026-07-05
> 執行順序修正：Steps 2-4 由並行改為嚴格串行，Step 2 (code movement) 移至最後。

每個步驟獨立可部署，管線在步驟之間持續運作。

---

## 步驟總覽

| 順序 | 步驟 | 內容 | 狀態 |
|------|------|------|------|
| 1 | Vault 拆分 private repo | 內容 (`raw/ wiki/ ...`) 移到 private repo | ✅ 已完成 |
| 2 | LLM Router | `route()` 取代直接 SDK 呼叫 | ✅ 已完成 |
| 3 | Agent 開發隔離 | AGENTS.md + contracts + branch isolation | ✅ 已完成 |
| 4 | Resolver Layer | URL fetch adapters (YouTube/新聞/GitHub) | ✅ 已完成 |
| 5 | Code movement | `bot/` → `src/personalkm/` (純整理，無功能變更) | ✅ 已完成 (2026-07-10) |

---

## Step 1 — Vault 拆分 private repo（已完成 2026-07-05）

**結果：** `raw/ wiki/ Attachments/ Trash/ .obsidian/` 移到 `github.com/dannytsao/Personalkm-vault`（private）。Code repo 歷史經 `git-filter-repo` 改寫（force push all branches）。所有路徑參考已更新。

**執行細節記錄於 `CHANGELOG.md 2026-07-05`。**

---

## Step 2 — ✅ LLM Router（已完成 2026-07-04）

`src/personalkm/llm/router.py` + 4 個 Provider 實作（Claude, Ollama, OpenAI-compat, Gemini）。

### 已完成的項目

1. `bot/ingestion_v2.py` — `_synthesize_wiki_note()` 改用 `route("ingest_synthesis")`
2. `scripts/ingestion_job.py` — Render cron 改用 `route("ingest_synthesis")`
3. `bot/query_engine.py` — 改用 `route("query_answer")`
4. 移除所有 `skip_llm` 靜默降級路徑（AGENTS.md rule 3）
5. `config/models.yaml` — 4 個 stages、3 個 providers
6. `tests/contracts/test_llm_router_contract.py` — 6 passed

### 尚未完成

- LLMError 推 LINE 告警 + `python -m personalkm.llm.usage report` 每日用量

---

## Step 3 — ✅ Agent 開發隔離（已完成 2026-07-04）

1. `AGENTS.md` + `CLAUDE.md`/`GEMINI.md` symlinks + `.gitignore` — 已提交
2. `tests/contracts/test_frontmatter_schema.py` + 測試用 fixtures — 已存在
3. Branch isolation: 開發在 feature branch，合併到 main 才部署 — 已文件化
4. `tests/contracts/` 套件 6 passed — 已確認

---

## Step 4 — Resolver Layer（from earlier design discussion）

Implementation order TBD with Danny.

1. Implement adapters in `src/personalkm/resolve/adapters/` (youtube via yt-dlp, github via raw README, generic via readability).
2. Wire `resolve_sources()` as the first stage of the hourly run, before ingest; only `fetch_status: fetched` notes proceed to LLM synthesis.
3. Extend `sanity_check` to flag stub pages and `failed_final` notes.

---

## Step 5 — Code movement（純整理，最後做）

**不改變任何功能。** 在 Steps 1-4 都完成後，有時間和心力再做。

1. `bot/` webhook code → `src/personalkm/capture/`. Preserve the `analyze_on_capture` hook that `bot/app.py::capture_urls()` calls into `bot/knowledge_decay.py` (see KNOWLEDGE-DECAY-GUIDE.md 架構) — it must still fire from wherever `capture_urls()` lands.
2. `scripts/ingest_wiki.py` → split into `src/personalkm/ingest/` (+ `scripts/` thin entrypoints)
3. Propagation logic → `src/personalkm/propagate/`
4. Query engine → `src/personalkm/query/`
5. `pip install -e ".[dev,llm]"` and get `pytest tests/contracts -q` green.
6. Move `CANONICAL_ENTITIES` from Python into `vault/wiki/_registry/entities.yaml`; load it via `settings.yaml`.