# PersonalKM — AI-Powered Second Brain

**Status:** ✅ Phase A+B Stable (Phase A on Mac Mini, wikilinks on Mac Mini, Render = webhook only)
**Last Updated:** 2026-06-27

LINE 群組連結整理到 Obsidian 的個人知識管理系統。LINE Bot 自動抓取 URL、生成 AI 摘要、提取重點、檢測知識衰退，每月報告追踪過時的技術知識。

---

## 📂 文件入口

| 文件 | 用途 |
|------|------|
| `DESIGN.md` | **[NEW 2026-06-26]** 系統架構、Phase A/B 流程、Lessons Learned、故障排除 |
| `LLMWIKI-INTEGRATION-CHANGENOTE.md` | LLM Wiki (Karpathy pattern) 整合說明、檔案清單、變更紀錄 |
| `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md` | 系統需求、架構與目前狀態 |
| `IMPROVEMENT-BACKLOG.md` | 後續改善事項與優先順序 |
| `CHANGELOG.md` | 已完成事項與已移除文件摘要 |
| `DOCS-INVENTORY.md` | 文件清單、狀態與更新節奏 |
| `PROJECT-DOCUMENTATION-PROCESS.md` | 專案文件管理流程 |
| `AGENTS.md` | Codex/agent 工作規則 |
| `KNOWLEDGE-DECAY-GUIDE.md` | 知識衰退檢測操作說明 |

---

## 🏗️ 系統架構

```
┌──────────────────────────────────────────────────────────────┐
│  RENDER (Webhook — Stateless)                                 │
│  LINE message → raw file → GitHub push (commit + push)       │
│  僅負責即時擷取，不做任何 AI 處理                             │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ vault/raw/ on GitHub
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  MAC MINI (Cron — 每小時)                                     │
│                                                              │
│  Phase A: scripts/ingest_wiki.py                             │
│    └─ git pull → ingest_raw_to_wiki → _commit_and_push_wiki  │
│    └─ wiki/entities/ + wiki/concepts/ → GitHub              │
│                                                              │
│  Phase B: scripts/post_link_ollama.py                        │
│    └─ OllamaWikilinkAnalyzer (qwen3:8b)                     │
│    └─ wikilinks + backlinks → GitHub                         │
└──────────────────────────────────────────────────────────────┘
```

**為何 Phase A/B 放在 Mac Mini 而非 Render？**

Render 的滾動部署會在任何時刻砍掉正在執行的背景任務。Phase A/B 在 webhook 的背景任務中執行了約三個月，從未成功完成。三層失敗原因：

1. **背景任務被部署砍掉** — Render 在 webhook 返回 200 OK 後仍持續部署，舊 instance 被終止
2. **Fresh clone vault** — Render 每次啟動 clone 新 vault，`ingest_raw_to_wiki` 寫入的 wiki 檔案從未推送
3. **缺少 git pull** — Phase A 看不到其他來源寫入的 raw 檔案

**重構後的穩定設計：** 所有 Phase A/B 從 webhook 完全移除，Mac Mini 每小時 launchd cron job 統一處理，不受 Render 生命週期影響。

---

## 🎯 核心功能

### 📝 即時捕獲 (Real-time)
- LINE 群組中任何 URL 都會被自動抓取
- 支援 YouTube、網頁、Instagram、TikTok、X 等
- 自動提取標題、內容、逐字稿
- 支援完整 LINE 貼文保存、長文分段合併與每次 capture 的 `log_id` 追蹤
- 以低成本 canonical Markdown schema 統一 YouTube、Web、社群連結、AI Mode 與 LINE pasted text

### 🤖 AI 智能富集 (Per Capture)
- 自動生成結構化摘要與標籤
- **YouTube 優化:** 5 點具體重點（非籠統描述）
- 自動概念提取與分類
- YAML frontmatter 存儲元數據

### 🔗 雙向 Wikilinks (Mac Mini 每小時)
- 新頁面自動連結到相關 entities
- 相關 entity 頁面自動加入 backlink
- Ollama qwen3:8b 在本機處理（不上雲）

### 📊 月度衰退檢測 (Monthly Report)
- 自動掃描 DevOps、AI 相關筆記
- 標記 90+ 天未更新的內容
- 生成 CRITICAL/HIGH/MEDIUM 衰退等級
- 建議更新或歸檔

---

## 📦 Vault 結構

```
raw/                    新捕獲的內容（未分類）
  ↓ (每小時 Phase A)
wiki/
├── entities/           具體工具/框架/人物
├── concepts/           知識概念
├── sources/            參考資源
├── _backlinks/         反向連結索引
└── knowledge-graph.md  自動索引

outputs/
├── decay-reports/      月度衰退檢測報告
└── ingestion-reports/  整理報告

archive/                已歸檔的舊筆記
Trash/                  已刪除的項目
Attachments/            圖片等附件
Templates/              筆記模板
```

---

## ⚙️ 自動化時間表

| 時間 | 操作 | 負責 |
|------|------|------|
| **即時** | LINE → raw/ → GitHub push | Render webhook |
| **每小時** | raw/ → wiki/entities/ + wiki/concepts/ | Mac Mini Phase A (`ingest_wiki.py`) |
| **每小時** | wikilinks + backlinks 建立 | Mac Mini Phase B (`post_link_ollama.py`) |
| **每月 1 日** | 衰退檢測報告 | Render cron |
| **每週六 23:00 UTC** | 週整理報告 | Render cron |

### Mac Mini Cron Jobs

```bash
# 確認正在運行
launchctl list | grep phase

# 查看 Phase A logs
cat ~/Library/Logs/PersonalKM/phase-a.out.log
cat ~/Library/Logs/PersonalKM/phase-a.err.log

# 重新 load Phase A
launchctl unload ~/Library/LaunchAgents/com.dannytsao.personalkm.phase-a-ingest.plist
launchctl load ~/Library/LaunchAgents/com.dannytsao.personalkm.phase-a-ingest.plist
```

---

## 🚀 工作流

### 用戶視角

```
1️⃣ 你在 LINE 傳送 URL、貼文，或分段長文
   ↓
2️⃣ Bot 自動保存完整貼文、抓取 URL 並生成摘要
   ↓
3️⃣ 筆記存到 raw/ 並 push，LINE 對話顯示已讀取
   ↓
4️⃣ Mac Mini 每小時自動組織到 wiki/ (Phase A)
   ↓
5️⃣ Mac Mini 每小時自動建立 wikilinks (Phase B)
   ↓
6️⃣ Obsidian 自動同步，每月收到衰退檢測報告
```

---

## 💻 本機啟動 (Mac Mini)

### 環境設定

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 本機測試 Render Webhook

```bash
uvicorn bot.app:app --reload --port 8000
```

健康檢查：
```bash
curl http://127.0.0.1:8000/health
```

### 手動觸發 Phase A

```bash
cd ~/Documents/PersonalKM
python3 scripts/ingest_wiki.py --vault ~/.personalkm/PersonalKM-worker
```

### 手動觸發 Phase B

```bash
cd ~/Documents/PersonalKM
python3 scripts/post_link_ollama.py --vault ~/.personalkm/PersonalKM-worker
```

### 手動觸發衰退檢測

```bash
python scripts/check_knowledge_decay.py
```

---

## 🌐 Render 部署

此 repo 包含 `render.yaml`。在 Render Dashboard 選擇 **New +** → **Blueprint**，連接 `dannytsao/PersonalKM`，Render 自動帶入配置。

```yaml
Build Command: pip install -r requirements.txt
Start Command: uvicorn bot.app:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Auto Deploy: true
Plan: starter
```

**Render Cron Jobs:**

```yaml
- Service: second-brain-ingest
  Schedule: 0 23 * * 6   # 每週六 UTC 23:00 (週日 07:00 UTC+8)

- Service: knowledge-decay-monthly
  Schedule: 0 9 1 * *   # 每月 1 號 UTC 9:00
```

> **注意：** Phase A (`raw/ → wiki/`) 已從 Render 移至 Mac Mini 每小時 cron job。Render webhook 僅負責即時 raw file 捕獲。

---

## 🔑 環境變數

### 必填

| 變數 | 用途 |
|------|------|
| `LINE_CHANNEL_SECRET` | LINE webhook 驗證 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE 消息 API |
| `OPENAI_API_KEY` | AI 摘要與分類 |
| `OPENAI_MODEL` | OpenAI 模型 |
| `VAULT_REPO_URL` | Vault 儲存庫 |

### 可選

| 變數 | 默認 | 說明 |
|------|------|------|
| `VAULT_PATH` | `/tmp/personal-km-vault` | 本地克隆路徑 |
| `PYTHON_VERSION` | `3.11.9` | Python 版本 |
| `REQUEST_TIMEOUT_SECONDS` | `10` | HTTP 請求超時 |
| `MAX_PAGE_CHARS` | `5000` | 網頁內容最大字符 |

---

## 📱 LINE Webhook 設定

1. 在 LINE Developers 後台設定 webhook URL：
   ```
   https://你的-render-domain.onrender.com/webhook/line
   ```

2. 啟用 webhook，將 Bot 加入 LINE 群組

3. 群組中任何人貼 URL，Bot 會自動：
   - 產生 `log_id`，格式為 `YYYYMMDDHHMM_00001`
   - 抓取內容
   - 生成 AI 摘要
   - 儲存到 `raw/` 並 push
   - 成功寫入後標示 LINE 訊息已讀取

### 長文與分段貼文

若 LINE 單則訊息過長，建議手動分段並在每段開頭加上序號：

```
[文章 1/3]
第一段內容...
```

```
[文章 2/3]
第二段內容...
```

```
[文章 3/3]
第三段內容...
```

系統會先暫存未收齊的段落，等所有段落到齊後合併成一篇完整 `line-message` note，再處理內含 URL。

### Google AI Mode Share Links

`https://share.google/aimode/...` 會對伺服器端擷取回傳 HTTP 429，請在同一則 LINE 訊息中貼上連結與回答文字：

```
https://share.google/aimode/...

AI Mode 回答：
這裡貼上 Google AI Mode 產生的完整回答...
```

---

## 🧠 Obsidian 同步設定

### 推薦設置

1. **Clone Vault**
   ```bash
   git clone https://github.com/dannytsao/PersonalKM.git ~/Documents/PersonalKM
   ```

2. **安裝插件**
   - Obsidian Git - 自動同步
   - Dataview - 查詢筆記
   - Tag Wrangler - 標籤管理
   - Templater - 模板系統

3. **Obsidian Git 設定**
   - Auto pull: 每 10 分鐘
   - Auto commit: 每 10 分鐘
   - Auto push: 每 10 分鐘 (pull first)

> 衰退檢測只看 GitHub 狀態。若只在本機 Obsidian 修改但未 commit/push，Render 自動化看不到。

---

## 📅 Phase 進度

### ✅ Phase A 重構：完成 (2026-06-26)
Phase A 從 Render webhook 移至 Mac Mini 每小時 launchd cron：
- `scripts/ingest_wiki.py` — Phase A 主邏輯
- `scripts/post_link_ollama.py` — Phase B 主邏輯
- `run_mac_mini_phase_a.sh` — Phase A runner（lock 機制）
- `run_mac_mini_phase_b.sh` — Phase B runner（lock 機制）
- `com.dannytsao.personalkm.phase-a-ingest.plist` — Phase A launchd
- `com.dannytsao.personalkm.phase-b-wikilink.plist` — Phase B launchd

### ✅ LLM-Wiki v2：完成 (2026-06-23)
- [x] Phase 1: MiniMax Client (`bot/llm_clients.py`)
- [x] Phase 2: AI Summarization (`bot/llm_summarizer.py`)
- [x] Phase 3: Entity Deduplication (`bot/entity_dedup.py`)
- [x] Phase 4: Bidirectional Wikilinks (`bot/wikilinks.py`)
- [x] Phase 5: Full Integration (`bot/ingestion_v2.py`)
- [x] Wiki vault health: 17 entities, 10 concepts, 0 broken wikilinks

### ⏰ Phase 6: Canonical Entity Architecture (規劃中)
- [ ] 建立 canonical entity pages（`docker.md`、`claude-code.md` 等）
- [ ] 重構 Phase 3 dedup：相同 topic → 合併到 canonical page
- [ ] 目標：≥80% wiki 頁面有 ≥1 個 incoming backlink

詳見 `IMPROVEMENT-BACKLOG.md`。

---

## 🛠️ 自定義與擴展

### 調整 YouTube 摘要
編輯 `bot/hermes_enrich.py`。

### 調整衰退檢測
編輯 `bot/knowledge_decay.py`。

### 添加新的自動化任務
1. 在 `~/.hermes/scripts/` 創建新 Python 腳本
2. 在 Render `render.yaml` 添加 Cron Job
3. 推送並自動部署

---

## 📚 文檔導覽

| 文檔 | 內容 |
|------|------|
| `DESIGN.md` | **[NEW]** 架構圖、Phase A/B 流程、Lessons Learned、故障排除 |
| `CHANGELOG.md` | 已完成事項與已移除文件摘要 |
| `DOCS-INVENTORY.md` | 目前文件清單、狀態與更新節奏 |
| `PROJECT-DOCUMENTATION-PROCESS.md` | 專案文件管理流程 |
| `IMPROVEMENT-BACKLOG.md` | 後續改善事項與優先順序 |
| `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md` | 系統需求、架構與目前狀態 |

---

## 📞 支援

- **議題追蹤:** [GitHub Issues](https://github.com/dannytsao/PersonalKM/issues)
- **反饋:** 通過 LINE 或 GitHub

---

**上次更新:** 2026-06-26
**系統狀態:** ✅ Phase A+B Stable — Render webhook (raw only) + Mac Mini cron (A+B)
**下次評審:** 2026-07-26
