# PersonalKM — 功能規格文件

> 最後更新：2026-07-04
> 狀態：此文件記錄「已設計但尚未實作」的功能規格，以及系統整體的 capture flow。
> 已實作的架構請見 `DESIGN.md`。

---

## 一、Data Capture Flow（完整流程）

### 設計哲學

**我存，AI 整理，我問** — 三個角色嚴格分工，每個工具只做一件事。
---

### 第一層：Capture（我存）

**執行者：Render webhook（`bot/app.py`）**

- 接收 LINE 訊息（URL、文字、混合）
- 唯一工作：寫 raw note → commit → push vault repo
- 黃金原則：**零失敗、零處理**，幾百毫秒完成，不做任何 fetch 或 LLM 呼叫

Raw note 初始 frontmatter：
```yaml
created: 2026-07-04T10:00:00+08:00
source: line
url: https://...
fetch_status: pending
retry_count: 0
```

---

### 第二層：Resolve（確定內容）

**執行者：Mac Mini hourly cron，Phase A 第一步**
**程式：`src/personalkm/resolve/`（純程式，無 LLM）**

URL Resolver 依來源分流：

| 來源 | 處理方式 | 結果狀態 |
|------|---------|---------|
| YouTube | yt-dlp 抓 transcript + title | `fetched` |
| GitHub | raw README fetch（免 auth） | `fetched` |
| News / 一般網頁 | readability 正文抽取 | `fetched` |
| IG / Threads（需登入）| 建 stub，LINE 通知補內容 | `auth_required` |
| 404 / 已消失 | 建 stub，保留 URL + 註記 | `dead` |
| 抓取失敗 | 等下一小時 retry，最多 3 次 | `failed` → `failed_final` |

**只有 `fetch_status: fetched` 的 note 才進 LLM 合成。**

抓回來的全文存在 raw note 旁（`raw/<date>-<slug>/content.md`），wiki note 只放蒸餾後的內容，未來重跑不需要重新抓網路。

---

### 第三層：Ingest（AI 整理）

**執行者：Mac Mini hourly cron，Phase A 後段**
**LLM：`route("ingest_synthesis")` → MiniMax M3 → OpenAI → Ollama qwen3:8b**

輸入：raw note + content.md（已抓到的全文）
輸出：

```yaml
created: ...
source: line
summary: AI 產的摘要（讀過全文後）
tags: [...]
topic: 主題分類
entities: [hermes-agent, claude-code, ...]
confidence: high
stub: false
```

Entity extraction（便宜任務）：
- `route("entity_extraction")` → Ollama qwen3:8b（本地，零 token 成本）
- 比對 `wiki/_registry/entities.yaml`（34 個 canonical entities）
- 新 entity 候選寫入 `proposed:`，等人工或信心門檻晉升

---

### 第四層：Propagate（知識連結）

**執行者：Mac Mini hourly cron，Phase B**
**LLM：`route("propagation_distill")` → Ollama qwen3:8b → MiniMax M2.7**

每份新 wiki note 的 entities 被 append 到對應的 entity 頁面 `## Captures` 區。
當累積到觸發條件，執行 **Distillation Loop**（見第二節）。

---

### 第五層：Query（我問）

**執行者：LINE Bot 問句觸發**
**LLM：`route("query_answer")` → MiniMax M2.7-highspeed → Ollama qwen3:8b**

- Hybrid search：keyword（title > frontmatter > body）+ entity graph
- LLM synthesis + `[[wikilink]]` citations
- 回答直接推回 LINE

---

### LLM 自動管理

整條 pipeline 的模型切換完全自動（`config/models.yaml`）：
任何 `LLMError`（非靜默 fallback）→ 推 LINE 告警。

---

## 二、Entity Distillation Loop 規格

### 背景

目前 entity page 的 `## Captures` 區是無限 append，累積多了會變成流水帳——這違反 Karpathy LLM Wiki「知識越存越濃縮」的精神。Distillation Loop 是讓知識真正深化的機制。

### 觸發條件

```yaml
distill_trigger:
  captures_threshold: 5
  decay_score_threshold: 0.4
  max_age_days: 30
```

三個條件任一成立即觸發，優先序：captures 數量 > decay > age。

### LLM 任務
JSON parse 失敗 → `LLMError`，該 entity 跳過本輪，下次 hourly retry。

### 執行流程
### Frontmatter 新增欄位（entity page）

```yaml
last_distilled: 2026-07-04T12:00:00+08:00
distill_count: 1
captures_count: 12
active_captures: 3
```

### 失敗處理

- JSON parse 失敗 → `LLMError`，跳過，不影響同輪其他 entity
- 歸檔前先備份到 `wiki/_archive/<slug>/`
- 失敗推 LINE 告警

---

## 三、近期待實作項目（優先序）

| 優先 | 功能 | 對應規格 |
|------|------|---------|
| P0 | Resolve layer（URL fetcher + adapters） | 第一節第二層 |
| P0 | LLM router 接入現有 ingest/propagate | MIGRATION.md Step 3 |
| P1 | Entity Distillation Loop | 第二節 |
| P1 | Vault 拆成 private repo | MIGRATION.md Step 1 |
| P2 | 失敗告警推 LINE | 第一節 LLM 自動管理 |
| P2 | entities.yaml 取代 code 內硬編碼 | MIGRATION.md Step 2.4 |
