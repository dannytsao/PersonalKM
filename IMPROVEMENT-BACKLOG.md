# PersonalKM Improvement Backlog

更新日期：2026-06-23

這份文件整理目前 LINE Bot + Obsidian 個人知識系統的後續改善事項。優先順序以「降低漏收、提升 raw note 品質、讓 Obsidian 更可用」為主。

已完成的 LLM-Wiki v2 已移至 `docs/llm-wiki-v2-plan.md`。

## P0 - Reliability / 不漏收

### 1. Render 與 LINE webhook 健康監控

目標：更早發現 Render service 停止、重啟、webhook 失敗或 GitHub push 失敗。

建議做法：
- 增加每日 health check report，寫入 `outputs/health-checks/`。
- 記錄最近一次 LINE webhook capture 的 `log_id`、時間、成功/失敗狀態。
- 若連續失敗，產生 failed report 或通知。

### 2. GitHub token rotation reminder / 安全維護

目標：避免曾經顯示過的 GitHub token 長期有效。

建議做法：
- 定期提醒 rotate token。
- 確認 `VAULT_REPO_URL` 已同步更新到 Render web service 與 housekeeping cron。
- 未來改用更小權限的 token 或 GitHub deploy key。

## P1 - Raw Quality / 進 raw 前與 raw 內清理

### 3. Layer 1 URL hygiene — 已完成 ✅

狀態：已完成，2026-06-11。

目前行為：
- 在 LINE 訊息進入 processing 前，先移除明顯廣告、追蹤、分享跳轉 URL。
- 移除常見 tracking query，例如 `utm_*`、`fbclid`、`igsh`、`gclid`。
- 保留正常主文連結，例如 Facebook group permalink。

後續可調整：
- 若仍有無關 URL 進入 raw，收集實例後加入 blocklist 或 allowlist 規則。

### 4. Layer 2 content cleaning — 待做

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

### 5. Food note structured extraction — 待強化

目標：美食類 note 穩定抽出店名、縣市、地址、Google Maps 連結；多店家貼文要支援多筆店家資訊。

已知需求：
- summary 與「店家資訊」不得互相矛盾。
- 若地址含縣市，縣市要獨立欄位化。
- 一篇多店家 Instagram/Threads 貼文，應列出多間店與多個地址。

建議做法：
- 將 Food extraction 改為結構化 JSON schema。
- 對單店與多店使用同一個 `places[]` 結構。
- 產生 note 前做一致性檢查，summary 與 places 不一致時以 `places[]` 為準或標記 `needs_review: true`。

## P2 - Enrichment / 補強平台內容

### 6. YouTube deep summary upgrade — 評估中

目標：YouTube 不只摘要一小段，而是輸出更可回顧的知識筆記。

LLM-Wiki v2 的 `llm_summarizer.py` 已有基礎濃縮，Phase 6 可考慮深化輸出格式。

建議輸出：
- 影片一句話結論。
- 5-10 個詳細重點。
- 時間戳重點，如果 transcript 可取得。
- 可行動清單。
- 關鍵名詞與相關工具。
- 適合放入 wiki 的概念節點。

### 7. Instagram / Threads / X local recovery — 待做

目標：當 Render 只能抓到 partial metadata 時，由本機 worker 或未來 cloud-safe worker 補強。

建議做法：
- 優先整理使用者貼上的 caption text。
- 對 blocked/social login wall note 標記 `worker_status: pending`。
- 未來評估 local browser snapshot，但避免高成本與不穩定爬蟲。

## P3 - Organization / Obsidian 可用性

### 8. Raw to wiki ingestion quality — 已大幅改善 ✅ (LLM-Wiki v2)

LLM-Wiki v2 (`bot/ingestion_v2.py`) 已完成：
- AI 濃縮摘要（80-85% body 壓縮）
- entity 去重合併
- 雙向 wikilink
- health check 驗證

### 9. Housekeeping archive / trash consistency — 待做

目標：維持 `status: done` 自動 archive，`status: X` 自動移到 Trash，且 GitHub/Obsidian 狀態一致。

建議做法：
- 每日 cloud housekeeping report。
- 對未移動成功的 note 顯示原因，例如 YAML 解析失敗、路徑衝突、檔名重複。
- Trash note 不再被 ingestion 或 wiki 流程視為 active note。

## P4 - Search / Retrieval

### 10. Query interface / personal knowledge search — Phase 6 候選

目標：能用問題查自己的 raw/wiki 知識庫，而不是只靠 Obsidian 手動搜尋。

建議做法：
- 先做 CLI query：搜尋 wiki + raw metadata + summary。
- 再做 lightweight web/query interface。
- 回答時附來源 note link 與 `log_id`。

## 下一步建議

最值得優先做的是：

1. Layer 2 content cleaning，直接改善 raw note 品質。
2. Food structured extraction，因為你最近的實際使用痛點最多。
3. Housekeeping report，確保 archive/trash 自動化值得信任。
