# PersonalKM Improvement Backlog

更新日期：2026-07-16

這份文件整理目前 LINE Bot + Obsidian 個人知識系統的後續改善事項，按執行優先順序排列。2026-07-16 優先序 1-10 已完成並測試。

已完成的 LLM-Wiki v2 已移至 `docs/llm-wiki-v2-plan.md`。

## 優先順序總覽

| 順位 | 項目 | 層級 | 效益/工時 | 狀態 |
|------|------|------|-----------|------|
| 1 | P0#1 健康監控 | 🔴 P0 | 高/低 | ✅ 已完成 |
| 2 | P1#4 Layer 2 內容清理 | 🟡 P1 | 高/中 | ✅ 已完成 |
| 3 | P3#9 Phase 6 Canonical Entity | 🔵 P3 | 高/高 | ✅ 已完成 |
| 4 | P1#5 美食結構化 | 🟡 P1 | 中/中 | ✅ 已完成 |
| 5 | P2#7 IG/Threads/X 補強 | 🟠 P2 | 中/高 | ✅ 已完成 |
| 6 | P4#11 Query 搜尋 | 🟣 P4 | 中/中 | ✅ 已完成 |
| 7 | P2#6 YouTube 深化 | 🟠 P2 | 中/中 | ✅ 已完成 |
| 8 | P3#10 Housekeeping | 🔵 P3 | 低/低 | ✅ 已完成 |
| 9 | P0#2 Token 輪換 | 🔴 P0 | 低/低 | ✅ 已完成 |
| 10 | P0#3 LLMError 告警 + 用量報告 | 🔴 P0 | 中/低 | ✅ 已完成 |

## 剩下待做（照順序）

目前沒有此序列中的待做項；下一輪 backlog 需重新排定。

---

## P0 — Reliability / 不漏收

### 1. Render 與 LINE webhook 健康監控 🥇

**優先：第 1 順位**

狀態：✅ 已完成並測試，2026-07-15。

目標：更早發現 Render service 停止、重啟、webhook 失敗或 GitHub push 失敗。

目前行為：
- Hermes cron `personalkm-health-check` 每 4 小時執行。
- 檢查 Render `/health`、vault last capture、vault local/remote sync、pipeline status、stale raw files、Phase A logs。
- 有異常時產生報告並指出修復步驟。

### 2. GitHub token rotation reminder / 安全維護 🥉

**優先：第 9 順位**

狀態：✅ 已完成並測試，2026-07-16。

目標：避免曾經顯示過的 GitHub token 長期有效。

目前行為：
- `python -m personalkm.security.token_rotation` 會檢查 `VAULT_REPO_URL` 是否含 embedded credentials。
- 支援 `VAULT_TOKEN_ROTATED_AT=YYYY-MM-DD` 與 `VAULT_TOKEN_MAX_AGE_DAYS`，超過門檻會回報 `rotate`。
- 報告不輸出 token 值，只輸出狀態、年齡與修復提示。

### 3. LLMError LINE 告警 + 用量報告 🥉

**優先：第 10 順位（MIGRATION.md 未完成項）**

狀態：✅ 已完成並測試，2026-07-16。

目標：當 LLM 呼叫失敗時自動通知，並每日檢視用量。

目前行為：
- `router.route()` 在所有 candidate model exhausted、即將 raise `LLMError` 時，會觸發 best-effort alert。
- alert 走既有 notification channels（LINE/Discord/email/file），但不吞掉原始 `LLMError`。
- `python -m personalkm.llm.usage report --notify` 可輸出並通知每日用量報告。

## P1 — Raw Quality / 進 raw 前與 raw 內清理

### 3. Layer 1 URL hygiene — 已完成 ✅

狀態：已完成，2026-06-11。

目前行為：
- 在 LINE 訊息進入 processing 前，先移除明顯廣告、追蹤、分享跳轉 URL。
- 移除常見 tracking query，例如 `utm_*`、`fbclid`、`igsh`、`gclid`。
- 保留正常主文連結，例如 Facebook group permalink。

後續可調整：
- 若仍有無關 URL 進入 raw，收集實例後加入 blocklist 或 allowlist 規則。

### 4. Layer 2 content cleaning 🥇

**優先：第 2 順位**

狀態：✅ 已完成並測試，2026-07-15。

目標：即使主 URL 是正確的，也要在「擷取到的頁面正文」進入 note body 前，移除和主旨無關的廣告、推薦文、導購區塊、頁尾導覽、分享按鈕、無關外部連結。

目前行為：
- `fetch_page()` 先移除 HTML noise elements（nav/footer/header/ads/cookie/share/related/comment 等）。
- 擷取後再跑 `clean_page_text()`，移除「延伸閱讀」、「相關文章」、「熱門推薦」、`ADVERTISEMENT`、copyright、社群分享、導覽項目等 boilerplate。
- 測試涵蓋內容清理行為，避免正文被廣告與推薦區塊稀釋。

### 5. Food note structured extraction 🥈

**優先：第 4 順位**

狀態：✅ 已完成並測試，2026-07-16。

目標：美食類 note 穩定抽出店名、縣市、地址、Google Maps 連結；多店家貼文要支援多筆店家資訊。

目前行為：
- Food note 產生同一套 `places[]` 結構，每筆包含店名、縣市、地址、Google Maps 連結。
- 單店與多店貼文共用同一個 extraction path。
- note body 同時保留可讀的「店家資訊」與機器可解析的 JSON `places[]`。
- 店名/地址缺漏或 summary 與正文店址衝突時標記 `needs_review: true`。

## P2 — Enrichment / 補強平台內容

### 6. YouTube deep summary upgrade 🥉

**優先：第 7 順位**

狀態：✅ 已完成並測試，2026-07-16。

目標：YouTube 不只摘要一小段，而是輸出更可回顧的知識筆記。

目前行為：
- YouTube 成功取得 transcript 時會走 deep-note path。
- 無外部 LLM key 時也能 deterministic 產生一句話重點、核心摘要、5-10 條重點、時間戳重點、可行動項目、關鍵概念、概念節點與逐字稿摘錄。
- LLM prompt 要求保留 timestamp、輸出具體行動與概念節點。

### 7. Instagram / Threads / X local recovery 🥈

**優先：第 5 順位**

狀態：✅ 已完成並測試，2026-07-16。

目標：當 Render 只能抓到 partial metadata 時，由本機 worker 或未來 cloud-safe worker 補強。

目前行為：
- LINE 訊息若同時含 IG/Threads/X/TikTok URL 與使用者貼上的 caption/text，會優先整理貼上的文字，不先嘗試 auth-walled fetch。
- 無法擷取的社群貼文會在 markdown `## 擷取狀態` 區標記 `需要本機 worker：是`、`worker_status：pending`。
- Resolver 建立的 auth-wall social stub 會寫入 `needs_local_worker: true`、`worker_status: pending`。
- Omnichannel worker 可從純 markdown raw note 的狀態區推斷 pending social note，不需要 raw YAML frontmatter。

## P3 — Organization / Obsidian 可用性

### 8. Raw to wiki ingestion quality — 已大幅改善 ✅ (LLM-Wiki v2)

LLM-Wiki v2 (`bot/ingestion_v2.py`) 已完成：
- AI 濃縮摘要（80-85% body 壓縮）
- entity 去重合併
- 雙向 wikilink
- health check 驗證

### 9. Canonical Entity Pages + True Dedup — Phase 6 🥇

**優先：第 3 順位**

狀態：✅ 已完成並測試，2026-07-15。

目標：建立真正的 entity canonical pages（如 `docker.md`、`claude-code.md`），而非僅有長檔名的 entity-indexed 頁面。

目前行為：
- `CANONICAL_ENTITIES` 定義 canonical slug 與顯示名稱。
- `EntityRegistry` 會優先以 canonical entity 名稱 match/merge。
- 新 capture 若命中 canonical entity，寫入無日期前綴的 canonical page，而不是建立新的長檔名頁面。
- `scripts/phase6_backfill.py` 可建立/更新 canonical pages、重建 wikilinks、修復 frontmatter、更新 index/log/knowledge graph。
- 已執行 backfill：新增 canonical pages，重建 knowledge graph，並通過測試。

### 10. Housekeeping archive / trash consistency 🥉

**優先：第 8 順位**

狀態：✅ 已完成並測試，2026-07-16。

目標：維持 `status: done` 自動 archive，`status: X` 自動移到 Trash，且 GitHub/Obsidian 狀態一致。

目前行為：
- `scripts/archive_inbox.py` 產生 structured housekeeping report，列出 archive/trash moves 與 skipped reasons。
- `scripts/cloud_housekeeping.py` 每次執行會寫入 `outputs/housekeeping/housekeeping-*.md` 並與移動結果一起 commit/push。
- 支援 `status: done|archived` → `Archive/`，`status: x|X` → `Trash/*.trash`，並處理檔名衝突。

## P4 — Search / Retrieval

### 11. Query interface / personal knowledge search 🥈

**優先：第 6 順位**

狀態：✅ 已完成並測試，2026-07-16。

目標：能用問題查自己的 raw/wiki 知識庫，而不是只靠 Obsidian 手動搜尋。

目前行為：
- `query_wiki()` 會搜尋 `wiki/`、`raw/`、`resolved/`，並保留 `source_kind`。
- raw/resolved 搜尋結果會帶出來源 URL 與 `log_id`（若存在）。
- CLI / FastAPI `/query` 共用同一個 query engine；CLI 修正為傳入 vault root。
