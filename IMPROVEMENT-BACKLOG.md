# PersonalKM Improvement Backlog

更新日期：2026-07-15

這份文件整理目前 LINE Bot + Obsidian 個人知識系統的後續改善事項，按執行優先順序排列。

已完成的 LLM-Wiki v2 已移至 `docs/llm-wiki-v2-plan.md`。

## 優先順序總覽

| 順位 | 項目 | 層級 | 效益/工時 | 狀態 |
|------|------|------|-----------|------|
| 1 | P0#1 健康監控 | 🔴 P0 | 高/低 | ✅ 已完成 |
| 2 | P1#4 Layer 2 內容清理 | 🟡 P1 | 高/中 | ✅ 已完成 |
| 3 | P3#9 Phase 6 Canonical Entity | 🔵 P3 | 高/高 | ✅ 已完成 |
| 4 | P1#5 美食結構化 | 🟡 P1 | 中/中 | ⏳ 待做 |
| 5 | P2#7 IG/Threads/X 補強 | 🟠 P2 | 中/高 | ⏳ 待做 |
| 6 | P4#11 Query 搜尋 | 🟣 P4 | 中/中 | ⏳ 待做 |
| 7 | P2#6 YouTube 深化 | 🟠 P2 | 中/中 | ⏳ 待做 |
| 8 | P3#10 Housekeeping | 🔵 P3 | 低/低 | ⏳ 待做 |
| 9 | P0#2 Token 輪換 | 🔴 P0 | 低/低 | ⏳ 待做 |
| 10 | P0#3 LLMError 告警 + 用量報告 | 🔴 P0 | 中/低 | ⏳ 待做（MIGRATION.md 未完成項） |

---

## P0 — Reliability / 不漏收

### 1. Render 與 LINE webhook 健康監控 🥇

**優先：第 1 順位**

目標：更早發現 Render service 停止、重啟、webhook 失敗或 GitHub push 失敗。

建議做法：
- 增加每日 health check report，寫入 `outputs/health-checks/`。
- 記錄最近一次 LINE webhook capture 的 `log_id`、時間、成功/失敗狀態。
- 若連續失敗，產生 failed report 或通知。
- 可選：透過 Hermes cronjob 定期檢查並通知（Telegram/Discord）。

### 2. GitHub token rotation reminder / 安全維護 🥉

**優先：第 9 順位**

目標：避免曾經顯示過的 GitHub token 長期有效。

建議做法：
- 定期提醒 rotate token。
- 確認 `VAULT_REPO_URL` 已同步更新到 Render web service 與 housekeeping cron。
- 未來改用更小權限的 token 或 GitHub deploy key。

### 3. LLMError LINE 告警 + 用量報告 🥉

**優先：第 10 順位（MIGRATION.md 未完成項）**

目標：當 LLM 呼叫失敗時自動通知，並每日檢視用量。

目前狀態：
- `python -m personalkm.llm.usage report` 指令已存在，可顯示今日 token 用量
- 但 LLMError 發生時沒有自動通知（LINE/Telegram）

建議做法：
- LLMError 發生時透過 LINE Notify 或 Telegram bot 發送告警
- 每日定時執行 usage report，異常時通知
- 可整合到現有的健康監控 cron job 中

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

目標：即使主 URL 是正確的，也要在「擷取到的頁面正文」進入 note body 前，移除和主旨無關的廣告、推薦文、導購區塊、頁尾導覽、分享按鈕、無關外部連結。

問題範例：
- 網頁正文混入「延伸閱讀」、「熱門文章」、「你可能也喜歡」。
- 社群貼文 metadata 混入平台導覽、登入提示、廣告文字。
- raw note 的「原始內容」比真正主文多很多雜訊，導致 summary 被稀釋。

建議做法：
- 在 `fetch_page()` 或 canonical Markdown normalizer 後加入 `clean_page_text()`。
- 使用規則先移除常見區塊標題與後續段落，例如「延伸閱讀」、「相關文章」、「熱門推薦」、「ADVERTISEMENT」。
- 清除重複 URL 清單、nav/footer/social/share 文字。
- 保留一份 `raw_source_excerpt` 或 `cleaning_notes`，方便追查清理是否過度。
- 加測試案例：文章主文 + 廣告區塊 + 延伸閱讀，確認只保留主文與必要來源連結。

### 5. Food note structured extraction 🥈

**優先：第 4 順位**

目標：美食類 note 穩定抽出店名、縣市、地址、Google Maps 連結；多店家貼文要支援多筆店家資訊。

已知需求：
- summary 與「店家資訊」不得互相矛盾。
- 若地址含縣市，縣市要獨立欄位化。
- 一篇多店家 Instagram/Threads 貼文，應列出多間店與多個地址。

建議做法：
- 將 Food extraction 改為結構化 JSON schema。
- 對單店與多店使用同一個 `places[]` 結構。
- 產生 note 前做一致性檢查，summary 與 places 不一致時以 `places[]` 為準或標記 `needs_review: true`。

## P2 — Enrichment / 補強平台內容

### 6. YouTube deep summary upgrade 🥉

**優先：第 7 順位**

目標：YouTube 不只摘要一小段，而是輸出更可回顧的知識筆記。

LLM-Wiki v2 的 `llm_summarizer.py` 已有基礎濃縮，Phase 6 可考慮深化輸出格式。

建議輸出：
- 影片一句話結論。
- 5-10 個詳細重點。
- 時間戳重點，如果 transcript 可取得。
- 可行動清單。
- 關鍵名詞與相關工具。
- 適合放入 wiki 的概念節點。

### 7. Instagram / Threads / X local recovery 🥈

**優先：第 5 順位**

目標：當 Render 只能抓到 partial metadata 時，由本機 worker 或未來 cloud-safe worker 補強。

建議做法：
- 優先整理使用者貼上的 caption text。
- 對 blocked/social login wall note 標記 `worker_status: pending`。
- 未來評估 local browser snapshot，但避免高成本與不穩定爬蟲。

## P3 — Organization / Obsidian 可用性

### 8. Raw to wiki ingestion quality — 已大幅改善 ✅ (LLM-Wiki v2)

LLM-Wiki v2 (`bot/ingestion_v2.py`) 已完成：
- AI 濃縮摘要（80-85% body 壓縮）
- entity 去重合併
- 雙向 wikilink
- health check 驗證

### 9. Canonical Entity Pages + True Dedup — Phase 6 🥇

**優先：第 3 順位**

目標：建立真正的 entity canonical pages（如 `docker.md`、`claude-code.md`），而非僅有長檔名的 entity-indexed 頁面。

**現況問題（2026-07-15 評估）：**
- 現有 59 個 entity 頁面均為長檔名（如 `2026-07-15-openai-官方釋出-gpt-5.6-...md`）
- 零個乾淨的 canonical entity page（無 `docker.md`、`claude-code.md` 等）
- 大多數 wiki 頁面是孤兒（接近 0 incoming backlinks）
- 相同主題的 capture → 產生新長檔名頁面，而非合併到同一個 entity page
- Karpathy 原文：「A single new source might trigger writes to **10–15 wiki pages**」，未實現

**Phase 6 具體工作：**

1. **建立 canonical entity 列表**
   - 從現有 wiki 頁面內容中提取真正的實體名
   - 建立 `docker.md`、`claude-code.md`、`github-actions.md` 等 canonical 頁面
   - 預計建立 50-100 個 canonical entity page

2. **重構 EntityRegistry dedup 邏輯**
   - `EntityRegistry` 改為基於 entity 名稱（而非檔名）做 match/merge
   - 新 capture 進來時，查 registry → 已有 entity → 追加到 canonical page；無 entity → 建立新 canonical page
   - 不再創建 `2026-07-15-docker-tutorial-xxx.md` 這種長檔名

3. **重寫 backfill 腳本**
   - 識別 page 內容中的 entity mention → 連結到 canonical entity page
   - 目標：多數頁面都有 ≥1 個 incoming backlink

4. **可選：Query → Write-back pipeline**
   - `/query <問題>`：搜尋 wiki，回答，並問「要不要把這個結論寫進 wiki？」
   - 建立「好問題的答案沉澱到 wiki」的飛輪

**Exit Conditions：**
- `docker.md`、`claude-code.md`、`hermes-agent.md` 等 ≥20 個 canonical entity page 存在
- ≥80% wiki 頁面有 ≥1 個 incoming backlink（目前接近 0%）
- 相同主題的 2 個 capture → 合併進同一個 canonical page（非建立 2 個檔案）
- backfill 腳本可完整重建所有 wikilinks

**預估規模：** 中等 — 需要重新設計 EntityRegistry 的 dedup 策略，但不需要改 `llm_summarizer.py` 或 `wikilinks.py` 的核心邏輯。

### 10. Housekeeping archive / trash consistency 🥉

**優先：第 8 順位**

目標：維持 `status: done` 自動 archive，`status: X` 自動移到 Trash，且 GitHub/Obsidian 狀態一致。

建議做法：
- 每日 cloud housekeeping report。
- 對未移動成功的 note 顯示原因，例如 YAML 解析失敗、路徑衝突、檔名重複。
- Trash note 不再被 ingestion 或 wiki 流程視為 active note。

## P4 — Search / Retrieval

### 11. Query interface / personal knowledge search 🥈

**優先：第 6 順位**

目標：能用問題查自己的 raw/wiki 知識庫，而不是只靠 Obsidian 手動搜尋。

建議做法：
- 先做 CLI query：搜尋 wiki + raw metadata + summary。
- 再做 lightweight web/query interface。
- 回答時附來源 note link 與 `log_id`。
