# PersonalKM Improvement Backlog

更新日期：2026-07-20

這份文件整理目前 LINE Bot + Obsidian 個人知識系統的後續改善事項，按執行優先順序排列。2026-07-16 優先序 1-10 已完成並測試；2026-07-19 新增優先序 11-15（Karpathy LLM-Wiki 差距收斂第一輪 + Entity Distillation Loop dry-run）已完成並測試；2026-07-20 新增優先序 17-25（Karpathy LLM-Wiki 差距收斂第二輪，對照實際 vault 數據驗證後排定，並將先前散落在「剩下待做」的 5 個缺口依邏輯依賴關係一併排入，待處理）。

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
| 11 | P5#12 Entity dedup merge 修復 | 🔵 P5 | 中/低 | ✅ 已完成 |
| 12 | P5#13 Query 優先回 wiki | 🔵 P5 | 高/低 | ✅ 已完成 |
| 13 | P5#14 1 source → N pages | 🔵 P5 | 中/中 | ✅ 已完成（見範圍限定） |
| 14 | P5#15 Query → write-back | 🔵 P5 | 中/中 | ✅ 已完成（API/CLI 層，定案不接 LINE） |
| 15 | P5#16 Entity Distillation Loop dry-run | 🔵 P5 | 高/中 | ✅ dry-run 已完成（未寫回、未接 cron）|
| 16 | P6#17 detect_entity_mentions() 過度偵測根因修復 | 🔵 P6 | 高/中 | 🔲 待開始 |
| 17 | P6#18 Stub 頁面 sources: 污染清理（6 頁） | 🔵 P6 | 中/低 | 🔲 待開始 |
| 18 | P6#19 Propagation 回溯補跑 | 🔵 P6 | 高/低 | 🔲 待開始（前置：#16） |
| 19 | P6#20 entities.yaml 動態白名單取代硬編碼 | 🔵 P6 | 高/中 | 🔲 待開始 |
| 20 | P6#21 Entity 合併路由改用 LLM 偵測結果 | 🔵 P6 | 高/中 | 🔲 待開始 |
| 21 | P6#22 Phase B 遷移到 personalkm.llm.router | 🔵 P6 | 中/中 | 🔲 待開始 |
| 22 | P6#23 Distillation Loop decay_score_threshold 決定 | 🔵 P6 | 低/低 | 🔲 待開始 |
| 23 | P6#24 Entity Distillation Loop 接進 cron | 🔵 P6 | 中/低 | 🔲 待開始（前置：#16、#21、#22） |
| 24 | P6#25 wiki/stubs/ frontmatter 合約補齊 | 🔵 P6 | 低/低 | 🔲 待開始 |

## 剩下待做（照順序）

目前沒有此序列中的待做項；下一輪 backlog 需重新排定。過程中發現幾個未列入本輪、需要另外排優先序的缺口：

- **2026-07-20 定案：LINE 不做對話式問答，維持純 capture 角色，不再是待排入的工作項**。`src/personalkm/capture/app.py` 的 `/webhook/line` 只做 capture，沒有任何 `reply_message`/`push_message` 呼叫，這是刻意的，不是缺工。理由：(1) AGENTS.md hard rule 規定 LINE webhook「Must stay dumb... NO fetching, NO LLM here」，LINE 問句觸發查詢會直接違反這條規則；(2) 查詢回答的核心呈現方式是 `[[wikilink]]` 引用，這是 Obsidian 原生語法，離開 Obsidian 就是死掉的文字，點不了、跳不了。Query 功能正式定位為 CLI（`scripts/query_wiki.py`）與 Obsidian 端，`/query` HTTP endpoint 與 `query_wiki()` 函式層（含 P5#15 write-back）已經是正確且最終的交付範圍，不需要再往 LINE 擴充。同步更新 SPEC.md 第五層、CHECKLIST.md 第 24-26 項。
~~`wiki/stubs/` 頁面的 frontmatter 沒有被 `test_frontmatter_schema.py` 合約涵蓋~~ 📋 2026-07-20 已排入 P6#25（見下方，低優先，可獨立處理）。
~~Entity Distillation Loop 的 `decay_score_threshold` 仍未實作~~ 📋 2026-07-20 已排入 P6#23，作為 P6#24（接進 cron）的前置決策。

**2026-07-20：Entity Distillation Loop 寫回機制 + `ingest_synthesis` 雲端化比較工具**

### Entity Distillation Loop 寫回（P5#16 續）

狀態：✅ 寫回機制已完成並測試，**Cron 整合刻意不做**。

目標：把 dry-run 驗證過的折疊保留設計真正實作出來。

目前行為：
- `distill.py` 新增 `apply_distillation()`：把 AI 摘要 + 重點寫在頁面最上面，原始 body（含所有 `### capture (date)` 全文）完整保留、包進 `<details>` 摺疊區塊，**不刪除任何內容**。Frontmatter 補上 SPEC.md 定義的 `last_distilled`/`distill_count`/`captures_count`/`active_captures` 四個欄位，`distill_count` 會正確遞增。
- `_set_field()` 只用整行比對（`.*$`），刻意不用完整重新解析再重建 frontmatter——因為 `distill.py` 自己的 `_parse_frontmatter()` 是逐行解析，會漏掉 `sources:`/`tags:` 這種多行 YAML 清單，如果拿它重建整個 frontmatter 會把這些欄位悄悄刪掉（跟 `post_link_ollama.py` 那次 bug 是同一個教訓）。
- `scripts/distill_entities.py` 新增 `--apply`：每一頁寫回前都會印出提議內容並要求 y/n 個別確認，沒有任何頁面會被無聲寫入；`--apply` 不能跟 `--no-llm` 併用（沒有摘要就沒有東西可以寫）。
- **Cron 整合刻意沒做**：這次 session 連續在別的地方踩到好幾個「自動化跑了很久才被發現壞掉」的 bug（Kimi 誤路由、`wikilink_processed` 疊加、`sources:` 污染），基於這個真實經驗，建議先讓使用者用 `--apply` 手動跑過幾次、確認品質穩定後，才考慮排進 Mac Mini hourly cron，這個決定留給你。
- 已知簡化：同一頁被重複濃縮多次時，摺疊區塊會一層包一層，沒有處理巢狀問題——目前觸發頻率低（5 筆 capture 或 30 天），實務上要很多輪才會顯現，先不處理。
- 測試：`tests/test_distill.py` 新增 8 案例（未觸發/無摘要不寫入、原文逐字保留、frontmatter 正確遞增、重複執行 `distill_count` 累加、不動到 `sources:`/`tags:` 等既有欄位）。

### `ingest_synthesis` 雲端化比較工具（P5 決策準備）

狀態：✅ 比較工具已完成並測試，**還沒改變任何正式行為**。

目標：在不影響 Phase A 正式運作的前提下，讓你能用真實內容比較現行 Ollama 版本跟雲端版本的品質。

目前行為：
- `ingestion_v2._synthesize_wiki_note()` 新增 `synthesis_stage` 參數（預設 `"ingest_synthesis"`，不影響現有唯一呼叫點的行為），可以指定其他 stage 名稱重跑同一段內容。
- `config/models.yaml` 新增 `ingest_synthesis_trial` stage（DeepSeek 優先，跟 `entity_distillation` 同一套 fallback 鏈），**只給比較工具用，`ingestion_v2.py` 的正式呼叫路徑完全沒有接到它**。
- 新增 `scripts/compare_ingest_synthesis.py`：讀一個你指定的真實 raw/resolved 檔案，同一段內容分別跑過 `ingest_synthesis`（現行 Ollama）與 `ingest_synthesis_trial`（DeepSeek），印出兩邊的 topic/tags/confidence/summary 與耗時，方便並排比較。只讀你指定的檔案，不寫入任何東西。
- 測試：`tests/test_ingestion_synthesis.py`（monkeypatch 驗證預設 stage 名稱不變、自訂 stage 名稱正確傳遞）。

**2026-07-20：`ingest_synthesis` 正式換成雲端優先**

狀態：✅ 已完成，這是這輪唯一真正改動 Phase A 正式行為的決定。

用 `compare_ingest_synthesis.py` 對兩篇真實 resolved 內容（OpenAI ChatGPT Work 更新、Claude Hacks 影片）做並排比較後決定：

- 兩篇 DeepSeek 版本都明顯保留更多具體事實——第一篇多抓到「可在桌面存取本機檔案」「可在 `.chatgpt.site` 建站」「僅付費用戶開放」等 Ollama 版本完全沒提到的細節；第二篇 DeepSeek 正確抓出「六個技巧」「Perfect Prompt Formula」「Apex Mindset 示範專案」「Base 44」「Claude Opus 4.8」，Ollama 版本只給了一段籠統敘述、連「六個技巧」都沒提到。速度上 DeepSeek 也沒有明顯劣勢（其中一篇還更快）。
- 這個結果跟稍早 Distillation Loop 測試 `claude-code.md` 時觀察到的模式一致（DeepSeek 覆蓋更廣、細節更具體），不是單次巧合。
- `config/models.yaml` 的 `ingest_synthesis` stage 正式改成 `deepseek/deepseek-v4-flash` 優先，fallback 鏈 `minimax/MiniMax-M2.7-highspeed → ollama/qwen3:8b`；`max_output_tokens` 一併調到 4000（沿用 `entity_distillation` 那次學到的教訓：deepseek-v4-flash 的內部 reasoning 過程會佔用輸出額度）。比較用的 `ingest_synthesis_trial` stage 已移除（決策已定案，不再需要）。
- 過程中發現使用者環境變數 export 成小寫（`minimax_api_key` 而非 `MINIMAX_API_KEY`）導致兩把 key 一直讀不到——shell 環境變數大小寫敏感，這不是程式碼問題。過程中使用者不慎把兩把真實 API key 貼進對話紀錄，已提醒視為外洩、需要重新產生新 key。
- 182 個測試全過。

**尚未做，需要你決定：**
- Distillation Loop 要不要接進 Mac Mini cron，等你手動用 `--apply` 跑過幾次再說
- 如果之後想再測試其他候選模型（例如 Claude），`compare_ingest_synthesis.py` 這支工具還在，但需要在 `config/models.yaml` 重新加一個 trial stage 才能用（原本的 `ingest_synthesis_trial` 已經因為決策定案被移除）

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

## P5 — Karpathy LLM-Wiki 差距收斂（第一輪）

背景：對照 SPEC.md 五層 pipeline 與 CHECKLIST.md 29 項驗收，發現「查詢優先度」「entity 合併正確性」「1 source → N pages」「query 結果寫回 wiki」是四個具體、可執行的落差，逐項評估後排入本輪。

### 12. Entity dedup merge 修復 🥇

**優先：第 11 順位**

狀態：✅ 已完成並測試，2026-07-19。

目標：確保新 capture 合併到既有 entity/concept page 時，`updated:` 時間戳真的被更新。

目前行為：
- 根因：`entity_dedup.py`、`ingestion_v2.py` 三處合併邏輯原本都用 `re.sub(r'^updated: .+$', ...)` 直接取代——若頁面當下沒有 `updated:` 欄位（例如舊格式頁面），這行會靜默不做任何事，不報錯，時間戳從此卡住。
- 新增 `entity_dedup.set_updated_timestamp()`，找不到既有 `updated:` 時改插在 `created:` 之後，兩者都沒有時插在 frontmatter 開頭；三處呼叫點（`ingestion_v2.py` 兩處合併分支、`entity_dedup.py` 的 `_append_capture`、`_add_capture_to_entity`）已全部改用此函式。
- **範圍限定**：合併「要併到哪一頁」目前仍是用 capture 的**標題文字**去比對（`registry.find_entity_match(title)` / `canonical_slug_from_name(title)`），不是用 LLM 實際判斷的 entity 名稱去比對——這代表如果標題沒提到實體名稱，即使內文明顯在講該實體，也不會合併進該實體的主頁面（只會透過 #14 的次要 excerpt 機制帶到）。這是比時間戳更根本的路由精準度問題，本輪不動它，因為改動合併目標的判斷邏輯屬於行為變更，可能造成內容誤併，需要你先決定容錯門檻才能安全動手。
- 測試：`tests/test_entity_dedup.py`（三個案例涵蓋有欄位/缺 updated/兩者都缺）。

### 13. Query 優先回 wiki 🥇

**優先：第 12 順位**

狀態：✅ 已完成並測試，2026-07-19。

目標：查詢結果排序讓 wiki entities 優先於 raw 頁面，避免長 raw 文章靠關鍵字重複次數蓋過精簡的 wiki 頁面。

目前行為：
- `search_vault()` 在合併 wiki 與 raw/resolved 結果前，對 raw/resolved 分數乘上 `RAW_SOURCE_SCORE_DAMPENING = 0.6` 再排序——wiki 在同等相關度時會贏，但特別強的 raw 命中仍能在 wiki 完全沒有相關結果時浮現，不是整組排除。
- 測試：`tests/test_query_engine.py::test_search_vault_ranks_wiki_above_raw_on_comparable_relevance`。

### 14. 1 source → N pages 🥈

**優先：第 13 順位**

狀態：✅ 已完成並測試，2026-07-19（範圍限定版）。

目標：新 capture 進來時，除了合併進主要 entity page，也順便更新內文提到的其他 entity/concept page。

目前行為：
- `_propagate_to_entity_pages()` 原本只掃 `wiki/entities/` 且只認 34 個硬編碼 `CANONICAL_ENTITIES`；現在改成同時檢查 `entities/` 與 `concepts/`，任何 `detect_entity_mentions()` 偵測到、且該頁已存在的 slug 都會被 append 一段 300 字摘錄 + 來源連結，不再要求該 slug 在 canonical 清單裡。
- **範圍限定**：次要頁面拿到的仍是文字摘錄（excerpt），不是像主頁那樣經過 LLM 蒸餾過的內容；也不會為不存在的 slug 新建頁面（避免污染 wiki 結構）。若要做到「每個相關頁面都拿到蒸餾內容」，需要額外一輪 LLM 呼叫，工時會顯著增加，本輪先不做。
- 副作用需注意：這讓更多頁面會被無限 append（見下方「剩下待做」的 Distillation Loop 缺口）。
- 測試：`tests/test_ingestion_propagation.py`（涵蓋 concepts/ 更新與自我引用跳過）。

### 15. Query → write-back 🥈

**優先：第 14 順位**

狀態：✅ 已完成並測試，2026-07-19（API/CLI 層——2026-07-20 定案這就是最終交付範圍，不接 LINE）。

目標：好問題的答案可以選擇性寫回 wiki。

目前行為：
- 新增 `write_back_answer()`：只會寫回 LLM 答案**實際引用**（`[[wikilink]]`）且**已存在**的 entity/concept page，用 `## 問答記錄` 區塊 append 問答紀錄；找不到符合的既有頁面就回傳 `None`，**絕不會**因為一次查詢答案就新建一個 wiki 頁面。
- `query_wiki()` 新增 `confirm_write_back: bool = False` 參數，預設不寫回；只有明確傳 `True` 且 LLM 答案有引用來源時才觸發寫回。`/query` HTTP endpoint 對應新增 `confirm` 查詢參數，寫回成功後才會 commit/push。
- **範圍定案（2026-07-20 更新）**：`src/personalkm/capture/app.py` 的 LINE webhook（`/webhook/line`）只做 capture，沒有 `reply_message`/`push_message`，write-back 只透過既有的 `/query` HTTP endpoint 或 CLI 觸發——這現在是**確定的最終交付範圍**，不是待補的缺口。LINE 對話式問答已定案不做（見上方「剩下待做」與 SPEC.md 第五層），理由是 AGENTS.md hard rule 禁止 LINE webhook 呼叫 LLM，且 `[[wikilink]]` 引用離開 Obsidian 會失效。
- 測試：`tests/test_query_engine.py`（`write_back_answer` 寫入既有頁面 / 找不到引用頁面回 None / `confirm_write_back=True` 但 `use_llm=False` 時仍不寫回三個案例）。

### 16. Entity Distillation Loop — dry-run 第一版 🥇

**優先：第 15 順位**

狀態：✅ dry-run 已完成並測試，2026-07-19。**尚未寫回任何內容**，這是刻意的。

目標：解決 SPEC.md 自己點名的「entity 頁面無限 append、違反知識越存越濃縮精神」問題，但先不冒真的覆寫/折疊知識庫的風險。

決策過程（2026-07-19 討論定案）：
- 模型：cloud 優先、本機 fallback，理由是這是低頻率但高風險（有損、疊代累積、不容易發現壞掉）的任務，跟 `entity_extraction` 那種機械式、可容錯的任務不同，比照系統既有 `query_answer` 的雲端優先模式。Primary 選定 **DeepSeek V4**（`deepseek-v4-flash`，中文品質評價高、$0.14/百萬 input、幾乎免費），fallback 鏈 MiniMax M2.7 → 本機 Qwen3:8b。已用真實 API key 測試過連線與繁體中文輸出（需在 system prompt 明講「請用繁體中文」，DeepSeek 預設會回簡體字）。
- 保留策略：**折疊保留**（AI 摘要放最上面，原始 capture 全文摺疊保留在同一頁後段，不刪除任何內容），而不是真正覆寫；先驗證品質穩定後才考慮改成有損覆寫。
- 上線順序：**先做純 dry-run 預覽，不自動寫回、不接 cron**。理由：處理這個任務時發現 `tests/contracts/test_frontmatter_schema.py`（AGENTS.md hard rule 4 的合約本體）已經跟正式程式碼脫節一段時間卻沒被發現（見下方），代表系統目前的自我檢查能力還不足以放心讓一個「有損、疊代」的自動化直接上線。

目前行為：
- 新增 `src/personalkm/propagate/distill.py`：`check_trigger()` 判斷 captures 數量 ≥ 5 或距 `last_distilled`/`created` ≥ 30 天（SPEC.md `distill_trigger` 的簡化版，**`decay_score_threshold` 故意省略**——`bot/knowledge_decay.py` 現有的新鮮度模型是針對 DevOps/AI 關鍵字分類設計的，套用到任意 entity/concept page 上不合適，留成後續待辦，沒有硬套）；`preview_distillation()` 對觸發的頁面呼叫 `entity_distillation` LLM stage，回傳提議摘要，**不寫入檔案**。
- 新增 `scripts/distill_entities.py`：CLI 入口，`python scripts/distill_entities.py --vault <path>` 印出觸發頁面清單與 AI 提議的濃縮結果，`--no-llm` 可只列候選不呼叫 API，`--json` 輸出機器可讀格式。**這個 session 沒有對你的真實 vault 執行過這支腳本**——AGENTS.md hard rule 1「Never touch the vault」，我只用 `tests/` 底下的假資料測試過；要看真實觸發結果，需要你自己在有 vault 存取權限的環境跑。
- `config/models.yaml` 新增 `entity_distillation` stage 與 `deepseek` provider（`DEEPSEEK_API_KEY` 需設在實際執行環境的 shell/launchd 變數，不是 repo 的 `.env`——LLM router 的 provider 都直接讀 `os.environ`，不會載入 `.env`）。
- 測試：`tests/test_distill.py`（觸發條件、LLM 呼叫/略過、錯誤處理、多頁面掃描共 10 案例，皆用假資料 + monkeypatch，未打真實 API）。
- 附帶修復：處理過程中發現 `tests/contracts/test_frontmatter_schema.py` 宣告的 wiki frontmatter 欄位（`source`/`summary` 必填）跟 `ingestion_v2.py`/`entity_dedup.py` 實際寫入的欄位（`title`/`updated`/`type`/`sources` 複數/`canonical`）完全對不起來，只是因為測試只對照一個手寫 fixture 才沒被抓到；已改成對照真實程式碼輸出重寫，`tests/fixtures/raw/`、`tests/fixtures/wiki/` 兩個 fixture 也換成真實格式。`wiki/stubs/` 頁面的第三種 frontmatter 形狀仍未被這份合約涵蓋，記錄為另一筆待辦。

尚未做（刻意留到你確認 dry-run 結果之後）：
- 真正把折疊/濃縮結果寫回頁面
- 串進 Mac Mini hourly cron（`launchd/com.dannytsao.personalkm.phase-b-wikilink.plist` 呼叫的 `run_mac_mini_phase_b.sh` 在此 session 存取範圍之外）

**2026-07-19 真實 vault dry-run 驗證記錄：**
- 第一次真實測試踩到兩個獨立 bug，皆已修復：① `claude-code.md` 標題含未跳脫冒號（`... on Instagram: "..."`）——`distill.py` 的 frontmatter 解析原本用 `yaml.safe_load`，改成跟 `query_engine.py` 一致的逐行 `partition(":")` 解析，不強求嚴格 YAML；② 你的 `DEEPSEEK_API_KEY` 環境變數實際內容混入了對話介面遮蔽顯示用的 `•` 字元（從對話視窗複製貼上導致），造成 httpx 組 HTTP header 時 `UnicodeEncodeError`——換一把從原始來源取得、未被遮蔽過的 key 後解決，純屬環境變數內容問題，非程式碼 bug。
- 額外意外發現並修復：`scripts/post_link_ollama.py::set_frontmatter_value()` 的正則 `\S` 只匹配舊值的第一個字元，導致 Mac Mini 每小時 cron 跑 Phase B 時，`wikilink_processed` 欄位新舊時間戳沒有正確覆蓋，而是不斷把舊值殘留串接在新值後面（例如 `2026-07-19T01:18:02026-07-18T23:42:56...`），持續在正式跑的 cron 上累積髒資料。已修正為整行覆蓋（`.*$`），並補上回歸測試。
- 品質比較：對 `wiki/entities/claude-code.md`（11 筆累積 capture）分別跑過本機 `qwen3:8b` fallback 與 DeepSeek V4 Flash primary——DeepSeek 涵蓋的主題數量明顯更多（多抓到 codex、Awesome Agent Architecture、Graphify 知識圖譜統計數字等 qwen3:8b 完全沒提到的內容），具體數字/專有名詞保留也更細緻，但**第一次 DeepSeek 輸出的 `key_facts` 完全沒有附日期**，違反 prompt 原本「所有具體日期必須逐字保留」的要求。已在 `build_distillation_prompt()` 新增明確規則：「key_facts 每一條結尾都必須附上該筆 capture 的日期」，並補上對應測試。使用者尚未針對 DeepSeek 版本的具體事實是否有胡編做逐句核對，這步驟仍待你完成。
- 加入可追溯反向連結：`ingestion_v2.py` 兩條合併路徑（一般標題比對、canonical 合併）現在會在每筆 capture 內容後面加一行 `Source: [[Archive/raw/...]]`（之前只有次要的 `_add_capture_to_entity` 路徑有這個）。`distill.py` 新增 `extract_capture_sources()` / `attach_source_links()`，用 key_fact 結尾的日期去比對 capture block 裡的 `Source:` 行，查到就在該條重點後面加上 `→ [[來源]]`。只對修復**之後**新寫入的 capture 有效，既有的 11 筆舊 capture 沒有回溯補上。

**2026-07-19 真實 capture 測試發現：Kimi 相關影片被誤路由，已修復**

手動觸發 Phase A 處理 4 則真實 Kimi K3 YouTube 連結後，發現全部沒有合併成一個 `kimi` 頁面，而是兩則被誤合併進不相關的 `entities/claude-code.md`、`entities/anthropic.md`，另兩則各自變成獨立孤兒頁面。根因：`entity_dedup.canonical_slug_from_name()` 用 `for slug in CANONICAL_ENTITIES: if slug in normalized...` 逐一比對，回傳**字典裡第一個比對到的**canonical entity，不是標題裡實際最先出現、最可能是主題的那個——例如標題「🚀kimi-k3编程能力倍增!在claude-code中全方位实测...」明明主要在講 Kimi，卻因為 `claude-code` 比 `kimi` 更早被列在 `CANONICAL_ENTITIES` 字典裡而誤判。

修復（`entity_dedup.py`）：
- `canonical_slug_from_name()` 改成回傳「在標題中最早出現」的 canonical entity，而不是字典宣告順序最前面的那個
- `CANONICAL_ENTITIES` 新增 `"kimi-k3": "Kimi K3"`，讓之後的 Kimi capture 有專屬頁面可以合併，不會繼續變成孤兒頁面
- 新增 3 個回歸測試（含這次真實踩到的標題原文），全部 174 個測試通過

**範圍限定**：這個修復只影響**之後**新進來的 capture；已經被誤合併進 `claude-code.md`／`anthropic.md` 的那兩筆 Kimi 內容，以及已經變成孤兒頁面的另外兩筆，都需要你自己決定要不要手動搬動／合併（這需要碰真實 vault，agent 不會自己動手）。

**2026-07-19 斷電/斷網韌性補強：**

檢查了 Mac Mini 三支 launchd 腳本（`run_mac_mini_phase_a.sh`、`run_mac_mini_phase_b.sh`、`run_mac_mini_worker.sh`）的斷網/斷電風險：

- **Git 操作本身已經夠韌性**：`scripts/ingest_wiki.py` 的 `git pull --rebase` 失敗只記警告不中斷；commit 在 push 之前就已經完成，就算 push 因斷網失敗，內容已經安全留在本機 git history，不會遺失，下次跑再補推即可。這部分沒有動。
- **真正的缺口：lock 檔案不耐斷電**——三支腳本都用 `mkdir "$LOCK_DIR"` 當 mutex，`trap 'rmdir "$LOCK_DIR"' EXIT` 只會在正常結束或收到訊號時觸發，**硬斷電或 `kill -9` 不會觸發這個 trap**，導致 lock 目錄永遠留著，之後每次 hourly launchd 觸發都會直接判定「已經在跑」而跳過，永遠不會自己恢復，除非人工手動刪除 lock 目錄。
- 已修復：三支腳本在嘗試 `mkdir` 拿鎖之前，先檢查既有 lock 目錄的修改時間，超過 3 小時（遠大於實際觀察到的單次執行時間：Phase A 約 7 分鐘、Phase B 約 17 分鐘）視為異常殘留、自動清除後再正常拿鎖；沒超過門檻的新鮮 lock 維持原本「跳過本次啟動」的行為不變。已用真實 `mkdir`/`stat -f %m` 邏輯個別驗證兩種情境（過期鎖被清除 / 新鮮鎖仍正確擋下同時執行）都符合預期，`bash -n` 語法檢查三支都過。

**2026-07-19/20 `sanity_check.py` 破壞性 schema 衝突 + `sources:` 污染根因排查：**

- **`sanity_check.py` 曾經會刪掉 `wikilink_processed`**：這個欄位是 `post_link_ollama.py` 用來判斷「這頁處理過沒」的必要狀態，但 `sanity_check.py` 的 `_clean_extra_fields()` 把它當「非 schema 欄位」寫死清除。若跑修復模式（非 `--check-only`），會讓全 vault 115 個頁面的處理紀錄一次歸零，下次 Phase B 對每一頁都重新跑 Ollama 分析（實測約每頁 1-1.5 分鐘，115 頁等於 2-3 小時不必要的重工）。已移除這段邏輯，用假資料驗證 `wikilink_processed` 不再被清除，174 測試全過。
- **`sources:` 欄位混入不相關 wiki 頁面路徑，根因是同一個 bug 出現在兩個地方**：`ingestion_v2.py::_auto_promote_entities()` 與 `scripts/phase6_backfill.py::_create_missing_stubs()` 都把「哪些既有頁面提到這個詞」誤寫進 `sources:`（該欄位語意應為「這個 entity 自己的原始 capture 來源」），這筆資訊其實已經在 body 的「## Mentions」區塊正確記錄過一次。已修正兩處，改成 `sources: []`，用假資料驗證兩處輸出都乾淨。**只影響之後新產生的 stub**；已受影響的舊頁面（`antigravity.md`、`deepseek.md`、`inside.md`、`kimi-k3.md`、`openclaw.md`、`qwen.md`）不會自動修正。
- **`anthropic.md` 額外還有第二個根因，屬於一次性遷移的設計取捨，沒有動**：`phase6_backfill.py::aggregate_entity_content()`/`build_canonical_content()` 在 2026-07-15 執行 Phase 6 遷移時，把多個舊的分散頁面全文直接塞進「## Captures」（不截斷、不做 AI 濃縮），這不是明確的 bug，是遷移工具「先求資料不丟失」的取捨；這支腳本已經跑過、不會再自動執行，修改它的邏輯不會讓 `anthropic.md` 現有內容自動變乾淨，需要你手動決定要不要整理。

**尚未做，需要你回來後決定（2026-07-20 更新，移除已解決項目）：**
~~Phase B（`post_link_ollama.py` → `ollama_wikilink.py`）目前完全繞過 `personalkm.llm.router`，違反 AGENTS.md hard rule 2~~ 📋 2026-07-20 已排入 P6#22，排在接 cron（P6#24）之前處理，避免把同樣的架構債複製進新的自動化。
~~`antigravity.md`/`deepseek.md`/`inside.md`/`kimi-k3.md`/`openclaw.md`/`qwen.md` 這 6 個 stub 頁面既有的錯誤 `sources:` 內容~~ 📋 2026-07-20 已排入 P6#18。
~~`detect_entity_mentions()` 持續過度偵測垃圾實體，broken wikilinks 逐漸增加（212 → 223），還沒查根因~~ 📋 2026-07-20 已排入 P6#17，且刻意排在 P6 最前面——在根因未修前若先跑 P6#19 回溯 propagation，會把垃圾實體摘錄擴散到更多頁面，讓清理更困難。

~~Phase A `ingest_synthesis` stage 是否換成雲端優先~~ ✅ 已決定並執行，見上方「2026-07-20：`ingest_synthesis` 正式換成雲端優先」。
~~`anthropic.md` 現有內容的手動清理~~ ✅ 使用者已手動整理完成（拿掉污染的 `sources:` 清單、去除重複內容），已 commit + push。

**2026-07-20：`knowledge-graph.md` health check 長期誤報，已修復**

狀態：✅ 已完成並測試。

每次真實 Phase A 執行的 health check 都回報 `knowledge-graph.md structure invalid ❌`，這個從 session 一開始就每次都看到、但從沒被查過的既有問題，這次查出根因：

- `ingestion_health_check.py::check_knowledge_graph()` 要求檔案裡要有 `"# 📊 Knowledge Graph"`、`"## 🔗 Entities"`、`"## 💡 Concepts"` 這幾個帶 emoji 的標題，但 `personalkm.propagate.knowledge_graph.build_knowledge_graph()` 從來沒有產生過這個格式——實際輸出是純文字的 `"# Knowledge Graph"`，而且 `## Canonical Entities`/`## Concepts` 這些索引區塊是**條件式**的（該分類沒有任何頁面時整段都不會出現），沒有一個是能無條件要求的標記。這是這次 session 第三次遇到同一類問題（`sanity_check.py`、`test_frontmatter_schema.py` 也是檢查邏輯描述一個從沒被實作過的理想格式，不是真實產出）。
- 修法：改成檢查產生器**真正保證會有**的東西——標題、時間戳、Mermaid 區塊、以及一定會出現的 `subgraph Entities`/`subgraph Concepts`（即使沒有任何節點，這兩個區塊骨架也一定存在）。
- 新增 `tests/test_ingestion_health_check.py`（真實產出通過驗證 / 真的壞掉的內容仍正確判定失敗 / 檔案不存在時視為可選不算失敗），185 個測試全過。

## P6 — Karpathy LLM-Wiki 差距收斂（第二輪）

背景：2026-07-20 對照真實 vault 數據驗證（`entities/`=89、`concepts/`=31、日期前綴 legacy=70、canonical=19、`knowledge-graph.md` edges=282，平均 1.8 backlinks/page）後排定。原本散落在「剩下待做」的 5 個缺口（entity 過度偵測、stub sources 污染、Phase B router bypass、decay_score_threshold、stub frontmatter 合約）與原本獨立的 4 項差距收斂待辦，一併依邏輯依賴關係重新排序——核心原則：**先止血（避免自動化把問題擴散），再補回溯，再動架構，最後才接更多 cron**。

### 17. detect_entity_mentions() 過度偵測根因修復 🥇

**優先：第 16 順位**

狀態：🔲 待開始。

目標：查出 `detect_entity_mentions()` 為何持續把中文主題片段（如 `topic-下載`、`topic-五步驟剪片流程`）誤判成 entity，導致 broken wikilinks 持續增加（212 → 223，每次真實 Phase A 跑都在惡化）。

排序理由：這是本輪**唯一每小時都在自動惡化**的問題，且直接影響 #19（回溯補跑）與 #20（entity 白名單）的資料品質——如果先做 #19 再回頭修這個，等於把垃圾實體的摘錄再擴散進更多既有頁面，之後要清理的範圍只會更大。必須排在所有會擴大 entity 圖譜覆蓋範圍的動作之前。

計畫：
- 針對已知誤判樣本（中文 `topic-*` 片段）反查 `detect_entity_mentions()` 的抽取規則，確認是規則過寬還是缺少停用詞/長度過濾。
- 修復後跑一次全 vault 掃描，確認新誤判樣本不再產生；已存在的 broken wikilinks 是否需要一次性清理另外評估。

### 18. Stub 頁面 sources: 污染清理（6 頁）🥇

**優先：第 17 順位**

狀態：🔲 待開始。

目標：清理 `antigravity.md`/`deepseek.md`/`inside.md`/`kimi-k3.md`/`openclaw.md`/`qwen.md` 這 6 個 stub 頁面裡誤寫入的 `sources:` 內容（根因已在 `ingestion_v2.py::_auto_promote_entities()` 與 `phase6_backfill.py::_create_missing_stubs()` 修復，但只影響之後新產生的 stub，這 6 頁是舊資料殘留）。

排序理由：這 6 頁都已經是 canonical entity page，屬於 #20（entities.yaml 白名單）會直接管理的同一批頁面；在建立正式的 canonical 登記檔之前，先把已知會被登記進去的頁面資料清乾淨，比登記完才發現要回頭清理更省事。工時低、無風險，適合跟 #17 一起當作本輪的「止血」步驟。

計畫：
- 手動或寫一支一次性腳本，對這 6 頁的 `sources:` 欄位重設為 `[]`（跟修復後的正確行為一致），不動其他欄位。

### 19. Propagation 回溯補跑 🥈

**優先：第 18 順位（前置：#17 完成）**

狀態：🔲 待開始。

目標：驗證「1 source → N pages」（P5#14 `_propagate_to_entity_pages()`）對既有 157 頁是否也有效，而不是只對 2026-07-19 之後的新 capture 生效。

背景：P5#14 已完成並測試，但**只在 propagation 上線後新進的 capture 上跑過**；現有 157 頁裡大多數是上線前建立的，從未被回溯掃描過。目前 knowledge-graph.md 只有 1.8 backlinks/page（282 edges / 157 pages），這個數字有可能是「機制沒問題、只是舊頁面沒補跑」造成，也可能真的還有覆蓋率問題——兩者需要先用一次回溯跑分開來看，才知道下一步該做 #20/#21 還是別的。

計畫：
- 確認 #17 已修復，避免這次回溯把垃圾實體摘錄擴散到更多頁面。
- 寫一支一次性腳本，對 `wiki/entities/` 與 `wiki/concepts/` 既有頁面的 body 重跑 `detect_entity_mentions()` + `_propagate_to_entity_pages()`，只做「新增」不做「覆寫」既有內容。
- 跑完後重新產生 `knowledge-graph.md`，比較回溯前後的 edges/page 數字。
- 若密度回升明顯 → 這條缺口視為解決，不需要再動 propagation 邏輯本身。
- 若密度回升有限 → 才進一步查是 `detect_entity_mentions()` 覆蓋率不足，還是摘錄式 append（非 LLM 蒸餾）本身限制了連結密度。

### 20. entities.yaml 動態白名單取代硬編碼 CANONICAL_ENTITIES 🥈

**優先：第 19 順位**

狀態：🔲 待開始。

目標：解決 70/89 entity 頁面仍是日期前綴檔名的根本原因。

背景：`entity_dedup.py` 的 `CANONICAL_ENTITIES` 是一個**手動維護、目前只有 34 個 slug** 的硬編碼字典，19/34 已有對應頁面。任何 capture 主題只要不在這 34 個裡面，就必然落到日期前綴檔名——這是設計限制，不是 bug，因此不需要（也不會找到）「呼叫路徑沒被觸發」這類問題。SPEC.md 原始 P2 待辦「entities.yaml 取代 code 內硬編碼」正是同一件事，此輪正式排入執行。

計畫：
- 把 `CANONICAL_ENTITIES` 從程式碼內常數改為 `wiki/_registry/entities.yaml`（SPEC.md 第三層已提到的檔案位置），程式讀檔取代讀常數。
- 新增自動晉升規則：非 canonical 的日期前綴頁面若累積達到一定 capture 次數或被 `detect_entity_mentions()` 多次提及，提示（不自動）候選晉升為 canonical entity，寫入 `entities.yaml`。
- 對現有 70 個日期前綴頁面：晉升清單確定後，跑一次 migration 合併到對應 canonical page（沿用 P3#9 `phase6_backfill.py` 的既有 backfill 邏輯）。
- 測試涵蓋：讀取 `entities.yaml` 取代常數後既有行為不變、新增晉升候選不影響現有 34 個 canonical 判斷。

### 21. Entity 合併路由改用 LLM 偵測結果 🥉

**優先：第 20 順位**

狀態：🔲 待開始（需你先拍板容錯門檻，見下方風險）。

目標：新 capture 合併到既有 entity/concept page 時，用 LLM 實際判斷出的 entity 名稱去比對，而不是只看 capture **標題文字**。

背景：P5#12 已經點名這個問題「比時間戳更根本」，但當時刻意不動，因為改動合併目標的判斷邏輯屬於行為變更，可能造成內容誤併。2026-07-19 真實測試就踩到對應案例（Kimi K3 影片因為標題比對規則被誤合併進 `claude-code.md`/`anthropic.md`），雖然那次的 bug（字典比對順序）已修，但**用標題文字而非 LLM entity 判斷**這個更根本的問題本身還在。排在 #20 之後，因為合併目標的候選池（canonical slug 清單）要等 #20 的動態白名單定案後才穩定。

風險與需要你決定的事：
- 需要設定信心門檻——LLM 判斷的 entity 要多確定才觸發合併，避免把不相關內容誤併進一個熱門 entity 頁面（例如什麼都往 `claude-code.md` 塞）。
- 建議先在既有的 `entity_distillation`/`entity_extraction` LLM stage 之外新增一個「合併目標判定」的獨立 LLM 呼叫，回傳候選 slug + 信心分數，只有信心分數超過門檻才自動合併，否則 fallback 回現有的標題文字比對規則（不改變現況、不會更差）。
- 測試涵蓋：高信心正確合併、低信心 fallback 到標題比對、以及 2026-07-19 踩到的 Kimi K3 案例作為回歸測試。

### 22. Phase B 遷移到 personalkm.llm.router 🔵

**優先：第 21 順位**

狀態：🔲 待開始。

目標：把 Phase B（`post_link_ollama.py` → `ollama_wikilink.py`）目前直接寫死呼叫 Ollama HTTP API 的部分，改成走 `personalkm.llm.router`，修正對 AGENTS.md hard rule 2 的長期違反。

排序理由：這是架構債，不阻塞 #17-21，但必須排在 #24（Distillation Loop 接進 cron）之前——如果 Distillation Loop 真的併入 Phase B 尾端執行，應該接在已經修正、走 router 的版本上，而不是把同樣繞過 router、缺乏 fallback/告警覆蓋的架構債複製進新的自動化。

計畫：
- 改寫 `post_link_ollama.py`/`ollama_wikilink.py`，呼叫改走 `router.route("wikilink_analysis")`（或等效新 stage），保留 Ollama 為 fallback 鏈末端。
- 確認 router 的 `LLMError` 告警機制（P0#3）也涵蓋到 Phase B 呼叫路徑。

### 23. Distillation Loop decay_score_threshold 決定 🔵

**優先：第 22 順位**

狀態：🔲 待開始。

目標：決定 SPEC.md `distill_trigger` 定義的第三個觸發條件 `decay_score_threshold` 要不要實作、如何實作，而不是無限期擱置。

排序理由：這是 #24（接進 cron）正式上線前必須拍板的最後一個懸而未決的觸發條件，因此緊接排在 #24 之前，避免 #24 上線後才發現觸發邏輯還缺一塊。

計畫：
- 評估 `bot/knowledge_decay.py` 現有的新鮮度模型（針對 DevOps/AI 關鍵字設計）是否能泛化到任意 entity/concept page，或需要另一套更通用的版本。
- 拍板後：要嘛實作一個通用版 decay score 並接上 `distill_trigger`，要嘛正式在 SPEC.md 註記「刻意省略」並說明理由，不留模糊地帶。

### 24. Entity Distillation Loop 接進 hourly cron 🔵

**優先：第 23 順位（前置：#17、#21、#22、#23）**

狀態：🔲 待開始。

目標：把 P5#16 已經 dry-run + 寫回機制驗證過的 Distillation Loop 真正接進 Mac Mini hourly cron，讓「知識越存越濃縮」變成自動發生，而不是手動 `--apply` 才會發生。

背景：`distill.py` 的折疊保留寫回機制（P5#16 續）已完成並測試，`scripts/distill_entities.py --apply` 可用但需要逐頁人工 y/n 確認。上一輪決定先手動跑過幾次確認品質穩定再排進 cron，理由是同一 session 連續踩到好幾個「自動化跑很久才被發現壞掉」的 bug（Kimi 誤路由、`wikilink_processed` 疊加、`sources:` 污染）。這個顧慮依然成立，此輪排在 #17（止血）、#21（合併精準度）、#22（架構債）、#23（觸發條件拍板）都處理過之後才執行，是本輪風險最高、也最晚才動的自動化，刻意疊加最多前置確認。

計畫：
- 完成 backlog 上一輪標記為「你尚未完成」的動作：對 DeepSeek 輸出的 `key_facts` 逐句核對是否有胡編。
- 手動 `--apply` 再跑 3-5 輪不同 entity 頁面，確認折疊保留格式、`distill_count` 遞增、來源反向連結都穩定無誤。
- 品質確認後，新增 Phase C（或併入已遷移到 router 的 Phase B 尾端）呼叫 `distill.py` 的 `apply_distillation()`，觸發條件沿用 SPEC.md `distill_trigger`（`captures_threshold: 5` / `max_age_days: 30` / #23 拍板後的 `decay_score_threshold`）。
- 新增 launchd plist 或延伸現有 Phase B plist，並比照 Phase A/B 現有的 lock 機制（含過期鎖自動清除）與斷電韌性設計。
- 測試涵蓋：cron 觸發路徑的 mock 呼叫、與既有 `tests/test_distill.py` 十案例整合不衝突。

### 25. wiki/stubs/ frontmatter 合約補齊 🔵

**優先：第 24 順位**

狀態：🔲 待開始。

目標：`wiki/stubs/` 頁面（IG/Threads 等抓不到內容時建立的 stub，欄位為 `stub`/`platform`/`worker_status`/... ，跟 entities/concepts 頁面語意完全不同）目前沒有任何合約在驗證其 frontmatter，`test_frontmatter_schema.py` 只涵蓋 entities/concepts 兩種形狀。

排序理由：純粹的測試覆蓋缺口，不阻塞、也不被本輪任何其他項目阻塞，適合排在最後、有餘裕時處理。這類「合約描述跟實際產出脫節」的問題本輪已經在別處踩過三次（`sanity_check.py`、`test_frontmatter_schema.py` 舊版、`knowledge-graph.md` health check），補上這個合約可以避免同類問題第四次發生。

計畫：
- 對照 `wiki/stubs/` 實際產出的 frontmatter 形狀（而非理想設計），新增獨立的 stub schema 合約測試，比照 `test_ingestion_health_check.py` 這次「先看真實輸出再寫合約」的做法。
