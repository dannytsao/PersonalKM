# Personal KM - AI-Powered Second Brain

**Status:** ✅ Phase 1+4 Live (Karpathy Framework Implementation + LINE reliability upgrades + canonical raw notes)

LINE 群組連結整理到 Obsidian 的個人知識管理系統。LINE Bot 自動抓取 URL、生成 AI 摘要、提取重點、檢測知識衰退，每週日自動組織筆記，月度報告追踪過時的技術知識。

## 2026-06-09 今日更新

- 修正 capture 時間基準為 Asia/Taipei，讓 raw note 檔名、YAML 日期與 `log_id` 日期一致，避免 Render UTC 造成「今天筆記」落在前一天。
- `threads.com` 與 `www.threads.com` 已納入社群平台路由，未來 Threads 連結會以 `platform: threads`、`content_type: social_post` 產生 canonical Markdown。
- 確認測試 Threads URL 已成功由 LINE bot 寫入 GitHub，並同步回本機 Obsidian repo。
- canonical raw notes 已部署到 live：URL、社群貼文、LINE pasted text 會盡量轉成統一 Markdown 結構，維持低成本、不新增昂貴爬蟲或 headless browser 依賴。
- `call it a day` 作為固定收尾流程：同步遠端、本機 README 補日誌、檢查、commit、push，並確認 Render `/health`。

## 2026-06-08 今日更新

- Render web service 已改為 Starter plan，避免 Free plan idle spin down 造成 LINE webhook cold start 遺失。
- 新增 repo 工作規則：完成變更後需測試、commit、push `main`，並確認 Render `/health`。
- Google AI Mode share link 不再硬抓 `share.google/aimode/...`，避免 HTTP 429；若同一則 LINE 訊息包含 AI Mode 回答文字，系統會用貼上的文字整理摘要。
- LINE 長貼文現在會先保存完整貼文 note，再逐一處理內含 URL，避免原始文字下落不明。
- 支援分段長文合併，例如 `[文章 1/3]`、`[文章 2/3]`、`[文章 3/3]`；收齊後合併為一篇完整 note。
- 每則 LINE capture 會產生 `log_id`，格式為 `YYYYMMDDHHMM_00001`；同一則訊息產出的完整貼文 note 與所有 URL notes 共用同一個 `log_id`。
- 成功寫入 repo 後，LINE bot 會呼叫 LINE mark-as-read API，讓對話中顯示已讀取。
- 新增低成本 canonical Markdown normalizer：不使用昂貴爬蟲，優先使用已抓到/已貼上的內容，統一輸出 YAML `content_type` 與「摘要、重點、原始內容、內含連結、媒體、擷取狀態、原文連結」章節。

## 🎯 核心功能

### 📝 自動捕獲 (Real-time)
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

### 📅 週日自動整理 (Every Sunday 9 AM)
- `raw/` → `wiki/` 自動組織
- AI 分析內容，按 entities/concepts 分類
- 自動生成 `knowledge-graph.md`
- Git 自動提交

### 📊 月度衰退檢測 (Monthly Report)
- 自動掃描 DevOps、AI 相關筆記
- 標記 90+ 天未更新的內容
- 生成 CRITICAL/HIGH/MEDIUM 衰退等級
- 建議更新或歸檔

### 📚 知識組織 (Three-Tier)
```
raw/              ← 未組織的大腦傾倒
  ↓ (每週日)
wiki/
├── entities/     ← Docker, Kubernetes, Claude 等
├── concepts/     ← 知識概念、框架
├── sources/      ← 參考資源
└── knowledge-graph.md

outputs/          ← 自動生成的報告
├── decay-reports/
└── ingestion-reports/

archive/          ← 已歸檔的舊筆記
```

---

## 📦 Vault 結構

```text
raw/                    新捕獲的內容（未分類）
│
wiki/                   自動組織的知識庫
├── entities/           具體工具/框架/人物
├── concepts/           知識概念
├── sources/            參考資源
└── knowledge-graph.md  自動索引

outputs/                自動生成的報告
├── decay-reports/      月度衰退檢測報告
└── ingestion-reports/  週度整理報告

archive/                歷史筆記
├── inbox-history-before-2026-06-07/  (舊 Inbox 遷移)
├── Food/               (Obsidian 備份)
├── Tech/               (Obsidian 備份)
└── stale/              (衰退檢測標記的筆記)

Trash/                  已刪除的項目
Attachments/            圖片等附件
Templates/              筆記模板
```

---

## 🚀 工作流

### 用戶視角
```
1️⃣ 你在 LINE 傳送 URL、貼文，或分段長文
   ↓
2️⃣ Bot 自動保存完整貼文、抓取 URL 並生成摘要
   ↓
3️⃣ 筆記存到 raw/，加上 log_id，並自動富集
   ↓
4️⃣ 成功寫入 repo 後，LINE 對話顯示已讀取
   ↓
5️⃣ 每週日 9 AM 自動組織到 wiki/
   ↓
6️⃣ Obsidian 自動同步，每月收到衰退檢測報告
```

### 自動化時間表
| 時間 | 操作 |
|------|------|
| **即時** | LINE 連結/貼文 → raw/ (log_id + AI 富集 + 已讀標記) |
| **每週日 9 AM** | raw/ → wiki/ (自動組織) |
| **每月** | 生成衰退檢測報告 |
| **持續** | Git 自動提交 |

---

## 💻 本機啟動

### 環境設定

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

編輯 `.env` 填入必要變數（見下方環境變數段落）

### 本機測試

```bash
uvicorn bot.app:app --reload --port 8000
```

健康檢查：
```bash
curl http://127.0.0.1:8000/health
```

### 手動執行自動化任務

**測試週日整理邏輯：**
```bash
python ~/.hermes/scripts/second-brain-ingest.py
```

**手動觸發衰退檢測：**
```bash
python scripts/check_knowledge_decay.py
```

---

## 🌐 Render 部署

此 repo 包含 `render.yaml`。在 Render Dashboard 選擇 **New +** → **Blueprint**，連接 `dannytsao/PersonalKM`，Render 自動帶入配置：

```yaml
Build Command: pip install -r requirements.txt
Start Command: uvicorn bot.app:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Auto Deploy: true  # 已啟用 - 每次 push 自動部署
Plan: starter      # 避免 Free plan 閒置休眠
```

**Cron Jobs:**
```yaml
- Service: second-brain-ingest
  Schedule: 0 9 * * 0   # 每週日 UTC 9:00
  Command: python ~/.hermes/scripts/second-brain-ingest.py

- Service: knowledge-decay-monthly
  Schedule: 0 9 1 * *   # 每月 1 號 UTC 9:00
  Command: python ~/.hermes/scripts/knowledge-decay-monthly.py
```

---

## 🔑 環境變數

### 必填

| 變數 | 用途 | 例子 |
|------|------|------|
| `LINE_CHANNEL_SECRET` | LINE webhook 驗證 | `abc123xyz...` |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE 消息 API | `Channel access token` |
| `OPENAI_API_KEY` | AI 摘要與分類 | `sk-...` |
| `OPENAI_MODEL` | OpenAI 模型 | `gpt-4o-mini` |
| `VAULT_REPO_URL` | Vault 儲存庫 | `https://token@github.com/user/PersonalKM.git` |

### 可選

| 變數 | 默認 | 說明 |
|------|------|------|
| `VAULT_PATH` | `/tmp/personal-km-vault` | 本地克隆路徑 |
| `PYTHON_VERSION` | `3.11.9` | Python 版本 |
| `REQUEST_TIMEOUT_SECONDS` | `10` | HTTP 請求超時 |
| `MAX_PAGE_CHARS` | `5000` | 網頁內容最大字符 |

**Render 環境變數設定：**
- 在 Render Dashboard 為 `personal-km-line-bot` service 設定上表變數
- 建議使用 Environment Group 共用 `VAULT_REPO_URL`

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
   - 儲存到 `raw/`
   - 推送 Git commit
   - 成功寫入後標示 LINE 訊息已讀取

### 長文與分段貼文

若 LINE 單則訊息過長，建議手動分段並在每段開頭加上序號：

```text
[文章 1/3]
第一段內容...
```

```text
[文章 2/3]
第二段內容...
```

```text
[文章 3/3]
第三段內容...
```

系統會先暫存未收齊的段落，等所有段落到齊後合併成一篇完整 `line-message` note，再處理內含 URL。合併後產出的完整貼文 note 與 URL notes 會共用同一個 `log_id`。

### Google AI Mode share links

`https://share.google/aimode/...` 通常會對伺服器端擷取回傳 HTTP 429，因此系統不直接抓取該分享頁。若要整理 AI Mode 的回答，請在同一則 LINE 訊息中貼上連結與回答文字：

```text
https://share.google/aimode/...

AI Mode 回答：
這裡貼上 Google AI Mode 產生的完整回答...
```

系統會使用貼上的回答文字產生摘要；若只貼 share link，note 會標記為 blocked 並保留原始連結。

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

### 重要提醒

衰退檢測只讀 GitHub 上的狀態。若只在本機 Obsidian 修改筆記但未 commit/push，Render 的自動化看不到這些更新。

---

## 🎯 YouTube 摘要格式

### 自動檢測
- 系統自動偵測 YouTube/youtu.be 連結
- 自動抓取逐字稿與 AI 分析

### 摘要格式
```markdown
---
tags: 標籤1, 標籤2
summary: "**重點摘要：**
- 具體重點 1 (包含工具名稱/版本)
- 具體重點 2 (包含具體步驟)
- 具體重點 3 (包含具體結果)
- 具體重點 4 (包含具體工具)
- 具體重點 5 (包含具體優勢)"
---

[原始逐字稿...]
```

### 設計原則
- ✅ 避免籠統描述 (「工具整合」→ 列出具體工具)
- ✅ 避免模糊詞語 (「實作步驟」→ 具體步驟序列)
- ✅ 包含具體名稱、版本、數字

---

## 📊 衰退檢測配置

### 監控範圍
- **DevOps 主題:** Docker, Kubernetes, Terraform, CI/CD 等
- **AI 主題:** GPT, Claude, LLM, PyTorch 等

### 衰退等級
| 等級 | 天數 | 顏色 |
|------|------|------|
| EVERGREEN | 0-90 | 🟢 |
| MEDIUM | 90-120 | 🟡 |
| HIGH | 120-180 | 🟠 |
| CRITICAL | 180+ | 🔴 |

### 月度報告
```markdown
## 2026-06-07 知識衰退檢測報告

### 🟢 EVERGREEN (最新，無需更新)
- Claude 最新用法 (0 days)

### 🟡 MEDIUM (3-4 個月，建議複習)
- Docker 多階段構建 (95 days)

### 🔴 CRITICAL (6+ 個月，強烈建議更新)
- Kubernetes 1.25 配置 (210 days)
  → 當前版本已是 1.31
```

---

## 🔄 Inbox 遷移記錄

**2026-06-07:** 完成遷移
- 4 個舊筆記從 `Inbox/` 移至 `archive/inbox-history-before-2026-06-07/`
- `Inbox/` 文件夾已刪除
- 新系統完全啟用 (raw → wiki)

詳見 [INBOX-MIGRATION-LOG.md](./INBOX-MIGRATION-LOG.md)

---

## 📅 Phase 進度

### ✅ Phase 1+4: 完成 (2026-06-07)
- [x] 三層架構 (raw/wiki/outputs)
- [x] 週日自動整理
- [x] AI 富集 (標籤、摘要、概念)
- [x] YouTube 5 點摘要
- [x] 衰退檢測系統

### ⏰ Phase 2+3: 評估中 (2026-09-07 決定)
- [ ] 知識圖譜 (entity relationships)
- [ ] 查詢界面 (search/filter/timeline)
- [ ] 決策點：運行 1 個月後決定

詳見 [ENHANCEMENT-DECISION.md](./ENHANCEMENT-DECISION.md)

---

## 🛠️ 自定義與擴展

### 調整 YouTube 摘要
編輯 `bot/hermes_enrich.py`：
```python
# 修改重點數量
"key_points": [...]

# 修改分析溫度 (0.5=保守, 0.7=創意)
temperature=0.5

# 修改最大 token
max_tokens=600
```

### 調整衰退檢測
編輯 `bot/knowledge_decay.py`：
```python
# 修改監控主題
DEVOPS_KEYWORDS = [...]
AI_KEYWORDS = [...]

# 修改衰退天數閾值
FRESHNESS_LEVELS = {
    "CRITICAL": 180,
    "HIGH": 120,
    ...
}
```

### 添加新的自動化任務
1. 在 `~/.hermes/scripts/` 創建新 Python 腳本
2. 在 `render.yaml` 添加 Cron Job
3. 推送並自動部署

---

## 📚 文檔導覽

| 文檔 | 內容 |
|------|------|
| [PHASE-1-4-ROADMAP.md](./PHASE-1-4-ROADMAP.md) | Phase 1+4 詳細計畫 |
| [YOUTUBE-SUMMARY-ENHANCEMENT.md](./YOUTUBE-SUMMARY-ENHANCEMENT.md) | YouTube 摘要改進說明 |
| [ARCHIVE-STRATEGY.md](./ARCHIVE-STRATEGY.md) | Archive 文件夾策略 |
| [WHY-RAW-NOT-INBOX.md](./WHY-RAW-NOT-INBOX.md) | 為什麼需要 raw/ 文件夾 |
| [INBOX-MIGRATION-LOG.md](./INBOX-MIGRATION-LOG.md) | Inbox 遷移記錄 |
| [IMPLEMENTATION-DELIVERY.md](./IMPLEMENTATION-DELIVERY.md) | 交付文檔 |

---

## 🎊 核心工作流快速參考

### 日常使用
```bash
# 1. 在 LINE 傳送 URL、貼文，或 [文章 1/3] 分段長文
#    ↓ (即時)
# 2. 筆記自動進入 raw/，包含 log_id 與富集摘要
#    ↓ (每週日 9 AM)
# 3. 自動組織到 wiki/
#    ↓ (自動同步)
# 4. Obsidian 顯示更新
#    ↓ (每月自動)
# 5. 收到衰退檢測報告
```

### 月度維護
```bash
# 1. 檢查衰退報告
# 2. 更新過時筆記或標記歸檔
# 3. 查看 wiki/ 的新組織
# 4. 決定是否升級到 Phase 2+3
```

---

## 📞 支援與貢獻

- **議題追蹤:** [GitHub Issues](https://github.com/dannytsao/PersonalKM/issues)
- **文件:** 詳見各個 `.md` 文檔
- **反饋:** 通過 LINE 或 GitHub

---

## 📜 許可證

個人項目

---

**上次更新:** 2026-06-09
**系統狀態:** ✅ 完全運行 (Phase 1+4 + LINE reliability upgrades + canonical raw notes)
**下次評審:** 2026-07-07
