# PersonalKM — 知識管理系統設計文檔

> 最後更新：2026-07-04 — LLM 呼叫已改由 `personalkm.llm.router` 統一路由（詳見 CHANGELOG.md 2026-07-04 與 MIGRATION.md Step 3），本文件的流程圖對外行為不變。

---

## 系統架構總覽

```
┌──────────────────────────────────────────────────────────────┐
│                        RENDER (Web Service)                   │
│                     LINE Bot + FastAPI Webhook                │
│                                                              │
│  LINE message ──► /webhook/line ──► save raw file ──► GitHub│
│                                    (commit + push)           │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ vault/ raw/ on GitHub
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                         MAC MINI (本地)                        │
│                   launchd 每小時 cron job                     │
│                                                              │
│  Phase A (ingest_wiki.py) ──► ingest_raw_to_wiki            │
│         │                            │                       │
│         │                     wiki/entities/                 │
│         │                     wiki/concepts/                 │
│         ▼                            │                       │
│  _commit_and_push_wiki() ─────────────┘                       │
│         │                                                      │
│         └──► GitHub (vault repo)                              │
│                                                              │
│  Phase B (post_link_ollama.py) ──► OllamaWikilinkAnalyzer    │
│         │                            (qwen3:8b)               │
│         │                     wiki/ wikilinks + backlinks     │
│         ▼                            │                       │
│  git push ──────────────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

---

## Phase A：LINE → Raw → Wiki Entities

**職責：** 將 LINE 收到的訊息轉換為結識的原始檔案，並由 LLM 自動分類到 `wiki/entities/` 或 `wiki/concepts/`。

### 觸發流程

| 觸發方式 | 負責者 | 位置 |
|---|---|---|
| LINE 訊息抵達 | Render FastAPI | `bot/app.py` |
| 轉換為原始檔並 push | `save_note()` | `bot/notes.py` |
| 自動擷取為 wiki entities | Mac Mini cron | `scripts/ingest_wiki.py` |

### 為何從 Render 移到 Mac Mini

Phase A 最初在 Render 的 webhook 背景任務中執行，但遭遇三層失敗：

1. **背景任務被部署砍掉**：Render 在收到 LINE 200 OK 回應後仍持續部署新版本，舊 instance 的背景任務被終止
2. **Fresh clone vault**：`ingest_raw_to_wiki` 寫入的 wiki 檔案從未推送（缺少 `_commit_and_push_wiki`）
3. **缺少 git pull**：Render 每次啟動都 clone 新的 vault，沒有先拉取 Render cron 寫入的 raw 檔案

### Phase A 重構後的穩定設計

```
Render webhook (同步)
  └─ save_note() → raw/ → commit + push
                          │
Mac Mini (每小時 launchd)  │
  └─ ingest_wiki.py        │
       ├─ git pull (取得所有新 raw)
       ├─ ingest_raw_to_wiki (處理並寫入 wiki/)
       └─ _commit_and_push_wiki() → wiki/ → push
```

### 檔案說明

| 檔案 | 用途 |
|---|---|
| `bot/app.py` | LINE webhook，僅負責：接收 LINE → 寫入 raw → push |
| `scripts/ingest_wiki.py` | Phase A 主要邏輯，Mac Mini 每小時執行 |
| `bot/ingestion_v2.py` | `ingest_raw_to_wiki()` 核心，LlmClient fallback 邏輯 |
| `bot/git_store.py` | Git 操作（`commit_and_push`）|
| `run_mac_mini_phase_a.sh` | Phase A runner script（lock 機制）|
| `com.dannytsao.personalkm.phase-a-ingest.plist` | launchd plist，StartInterval=3600，RunAtLoad=true |

### 輸出

- `wiki/entities/<date>-<topic>.md` — 主題性內容（AI、DevOps、工具等）
- `wiki/concepts/<date>-<topic>.md` — 概念性、日常記錄
- Frontmatter 包含：`created`, `source`, `summary`, `tags`, `topic`, `contested`

---

## Phase B：Wiki Link 後連結

**職責：** 為所有 wiki 頁面建立雙向連結（正向 + 反向），使用 Ollama qwen3:8b 在本地處理。

### 觸發流程

| 觸發方式 | 負責者 |
|---|---|
| 每小時 launchd | `com.dannytsao.personalkm.phase-b-wikilink.plist` |

### 為何使用 Tag/Regex 而非結構化 JSON

qwen3:8b 無法穩定輸出結構化 JSON（即使 system prompt 明確要求）。採用 XML tag + Regex 解析：

```xml
<wikilinks>
  <link target="obsidian" context="..." />
  <link target="ai-agent" context="..." />
</wikilinks>
```

### 檔案說明

| 檔案 | 用途 |
|---|---|
| `scripts/post_link_ollama.py` | Phase B 主邏輯 |
| `bot/ollama_wikilink.py` | `OllamaWikilinkAnalyzer` — XML tag 解析 |
| `run_mac_mini_phase_b.sh` | Phase B runner script |
| `com.dannytsao.personalkm.phase-b-wikilink.plist` | launchd plist |

### 輸出

- 每個 wiki 頁面的 `wikilinks:` 欄位（正向連結）
- `wiki/_backlinks/<topic>.md`（反向連結 index）
- `Wiki/log.md` 記錄處理結果

---

## Phase 6：Canonical Entity 架構（2026-06-28）

**職責：** 建立 canonical entity pages（無日期前綴），作為實體知識的中心節點。一份 capture 觸發多個 entity 頁面更新，實現 Karpathy LLM-wiki 模式。

### 架構

```
raw/ capture
  │
  ├─► ingest_file_v2()  ──► 主頁面 (entities/ 或 concepts/)
  │
  └─► _propagate_to_entity_pages()  ──► entities/<slug>.md (10-15 頁)
       │     每篇 capture 的摘要 append 到所提及的所有 canonical entity
       │     頁面的 ## Captures 區塊
       │
       └─► _add_canonical_body_links()  ──► body 中的 entity 名稱自動補 [[wikilink]]
```

### 檔案說明

| 檔案 | 用途 |
|---|---|
| `bot/entity_dedup.py` | `CANONICAL_ENTITIES` 定義 (34 slugs)、`canonical_slug_from_name()`、merge 邏輯 |
| `bot/ingestion_v2.py` | `_propagate_to_entity_pages()`、`_add_canonical_body_links()`、`_auto_promote_entities()` |
| `bot/knowledge_graph.py` | Mermaid knowledge graph generator（被 ingest pipeline 和 backfill 共享）|
| `bot/query_engine.py` | Hybrid search engine + LLM synthesis |
| `scripts/query_wiki.py` | CLI 查詢介面 |
| `scripts/sanity_check.py` | Repair-first vault health checker |
| `scripts/phase6_backfill.py` | One-time migration script |

### Query Interface

- CLI: `python3 scripts/query_wiki.py -i` (interactive REPL) 或 `--json`
- Web: `GET /query?q=hermes+agent&top_k=10`
- Hybrid search: title (score 3) > frontmatter > body mentions > entity registry
- LLM synthesis with `[[wikilink]]` citations (可用 `--no-llm` 關閉)

### Sanity Check & Repair

`scripts/sanity_check.py` 是 repair-first 工具，修復 frontmatter issues 但永不刪除檔案：
- 補 `---` 分隔線 + flatten nested bracket tags + 清空 sources + 移除非 schema 欄位
- Warning-only：type mismatch、auto-promoted stubs
- Idempotent：第二次執行顯示 0 fixes
- 可整合在 batch ingest 結尾自動執行

---

## 教訓總結（Lessons Learned）

### 1. Webhook 觸發的任務必須同步

FastAPI 的 `BackgroundTasks` 在 webhook 返回 200 OK 後仍由 Render 管理，但 Render 的滾動部署會在任何時候砍掉舊 instance。**永遠不要**在 webhook 中依賴背景任務執行重要邏輯。

**解法**：將 Phase A 完全移出 webhook，由 Mac Mini cron job 接手。

### 2. Fresh Clone Vault Pattern

Render 每次啟動都會 clone 一個新的 vault。`ingest_raw_to_wiki` 如果寫入本地磁碟但從不 git push，那些檔案就會在下次啟動時消失。

**解法**：所有寫入都有明確的 commit + push。Phase A 從 git pull 開始，確保看到所有新的 raw 檔案。

### 3. 三層 Fix Pattern

這個管線連續失敗了三個月，每次只修復了當時看到的錯誤，卻沒解決根本原因：

| 層次 | 問題 | 修復 |
|---|---|---|
| 1 | wiki/ 從未推送 | `_commit_and_push_wiki()` |
| 2 | fresh clone vault 看不到 raw | `git pull` |
| 3 | 背景任務被 deploy 砍掉 | 同步 Phase A → 移到 Mac Mini |

**解法**：三層修復同時存在才能工作。Architecture 要從系統層面思考，不要只修看到的錯誤。

### 4. launchd 環境隔離

launchd 會清除幾乎所有環境變數（包括 `TMPDIR`）。Lock 目錄必須使用絕對路徑：

```bash
LOCK_DIR="${TMPDIR:-/tmp}/personalkm-phase-a.lock"
mkdir "$LOCK_DIR" 2>/dev/null || exit 0
trap 'rmdir "$LOCK_DIR"' EXIT
```

### 5. 兩個獨立的 Git Repo

`~/Documents/GitHub/DannyTsao/PersonalKM`（開發/文件）和 `~/.personalkm/personalkm-vault`（vault）是不同的 repo。後者為 private repo `github.com/dannytsao/Personalkm-vault`。Phase A/B script 讀寫 vault repo，Render 和 Mac Mini 之間通過 GitHub 同步。

### 6. 未知 `3b1e74e` Vault Backup

在 18:15 出現一個 `vault backup: 2026-06-26 18:15:27` commit，不是來自 Mac Mini（Mac Mini crontab 已清除），也不清楚來源。可能是 Render 內部備份机制。如果看到未預期的 vault backup commit，無需緊張——vault 會持續同步。

---

## Cron Job 狀態

| Job | Label | Schedule | 負責 |
|---|---|---|---|
| Phase A | `com.dannytsao.personalkm.phase-a-ingest` | 每小時 + RunAtLoad | raw → wiki entities |
| Phase B | `com.dannytsao.personalkm.phase-b-wikilink` | 每小時 + RunAtLoad | wikilinks + backlinks |

確認：
```bash
launchctl list | grep phase
```

---

## 故障排除

### Phase A 沒產生 wiki entities commit

1. 檢查 `~/Library/Logs/PersonalKM/phase-a.out.log` 有無錯誤
2. 確認 `scripts/ingest_wiki.py` 在 `sys.path` 中（`repo_root` 解析）
3. 確認 vault 有未處理的 raw 檔案：`ls vault/raw/`
4. 手動執行：`python3 scripts/ingest_wiki.py --vault ~/.personalkm/personalkm-vault`

### Phase B wikilinks 沒更新

1. 檢查 `scripts/post_link_ollama.py` 的 `WIKILINK_PROCESSED` frontmatter 是否已設定
2. 確認 Ollama 正在運行：`curl http://localhost:11434/api/tags`
3. 確認 qwen3:8b 模型已下載：`ollama list`

### Render webhook 沒收到 LINE

1. 檢查 LINE Developer Console 的 Webhook URL 是否正確
2. 確認 LINE Bot Basic 方案已啟用（否則 message content 取不到）
3. 檢查 Render Logs 有無 `POST /webhook/line` 200 OK

---

## 開發/部署指令

```bash
# 手動觸發 Phase A
cd ~/Documents/GitHub/DannyTsao/PersonalKM
python3 scripts/ingest_wiki.py --vault ~/.personalkm/personalkm-vault

# 重新 load Phase A cron
launchctl unload ~/Library/LaunchAgents/com.dannytsao.personalkm.phase-a-ingest.plist
launchctl load ~/Library/LaunchAgents/com.dannytsao.personalkm.phase-a-ingest.plist

# 查看 Phase A logs
cat ~/Library/Logs/PersonalKM/phase-a.out.log
cat ~/Library/Logs/PersonalKM/phase-a.err.log

# GitHub 上的 vault 最新狀態
cd ~/.personalkm/personalkm-vault
git fetch origin && git log origin/main --oneline -5
```
