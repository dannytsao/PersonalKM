# Karpathy LLM Wiki 入口完成檢查表

> 最後更新：2026-07-16
> 用途：確認系統已達到「Karpathy LLM Wiki 入口」標準，才往前推進知識深化（Distillation Loop）。
> 全部 29 項打勾 → 可以開始實作 `SPEC.md` 第二節。
>
> 狀態標記：
> - ✅ + ~~刪除線~~：已由目前 repo、測試、GitHub ref 或 live health check 確認。
> - ☐ 需你確認：需要實際 LINE/Obsidian/vault 觀察或 48 小時運行證據。
> - ☐ 需實作/重構：目前證據顯示尚未交付，不能只靠人工確認關閉。

---

## 判斷標準

| 完成門檻 | 說明 |
|---------|------|
| **格式 + Router**（第四、五欄）全勾 | contracts 健康，可開始 MIGRATION Step 3 |
| **Capture + 內容品質 + Query**（第一、三、六欄）全勾 | 入口真正完成 |
| **全部 29 項**全勾 | 可以實作 Distillation Loop |

---

## 一、Capture 功能（4 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 1 | ~~LINE Bot 收到訊息後 raw note 在 60 秒內出現在 vault~~ | 貼一則訊息，看 vault repo commit 時間 | ✅ 已確認：2026-07-16 live LINE URL / YouTube / social URL capture 到 GitHub + Obsidian |
| 2 | Raw note 有正確 frontmatter（created / source / url / fetch_status: pending） | 打開任一 raw note 檢查 | ☐ 需實作/重構：目前 raw note renderer 是純 Markdown body，未寫 YAML frontmatter |
| 3 | Bot 掛掉或 Render timeout 不會導致訊息遺失（webhook 有 retry） | 看 Render logs | ☐ 需你確認：需 Render/LINE retry 實測或失敗案例證據 |
| 4 | ~~純文字訊息（無 URL）也能正確 capture~~ | 貼一段純文字測試 | ✅ 已確認：2026-07-16 使用者 live 測試通過 |

---

## 二、Resolve 功能（5 項）

> 注意：Resolve layer 程式與單元測試已存在，但下列 checklist 項目仍以「實際 LINE/vault 流程」為準。

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 5 | GitHub URL → fetch_status: fetched，content 有 README 內容 | 貼一個 GitHub repo URL | ☐ 需你確認：adapter 單元測試已過，但需 live LINE/vault note 證據 |
| 6 | ~~一般 URL / 新聞 URL 可從 LINE capture 到 raw note~~ | 貼一篇新聞連結 | ✅ 已確認：2026-07-16 live URL / YouTube capture 通過；`fetch_status` frontmatter 契約仍待 #2 定案 |
| 7 | ~~IG / Threads / X URL → auth/social-limited 仍有 raw/stub note~~ | 貼一個 IG/Threads/X 連結 | ✅ 已確認：2026-07-16 live X / Threads capture 通過 |
| 8 | 失敗的 URL 在下一個 hourly cycle 有 retry（retry_count 遞增） | 看 raw note frontmatter | ☐ 需實作/確認：需 raw frontmatter/status 契約先定案 |
| 9 | fetch_status: pending 的 note 不會進入 LLM 合成 | 檢查 ingest log | ☐ 需實作/確認：需 pending raw note 實例與 ingest log 證據 |

---

## 三、Wiki Note 內容品質（5 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 10 | ~~Summary 是 AI 真正讀過內容後產的（不是從 URL 猜測）~~ | 打開 5 個 wiki note 對照原文 | ✅ 已確認：2026-07-16 使用者確認 vault/wiki content quality OK |
| 11 | ~~Tags 和 topic 與內容相符~~ | 抽查 10 個 note | ✅ 已確認：2026-07-16 使用者確認 vault/wiki content quality OK |
| 12 | ~~Entities 對應到 canonical entity slugs（不是自由發揮的字串）~~ | grep entities wiki/**/*.md \| head -20 | ✅ 已確認：2026-07-16 使用者確認 vault/wiki content quality OK |
| 13 | ~~沒有 skip_llm=True 產出的假 wiki note~~ | grep -r "skip_llm" wiki/ 應無結果 | ✅ 已確認：2026-07-16 使用者確認 vault/wiki content quality OK |
| 14 | ~~confidence: low 的 note 有被 sanity_check 列出~~ | 跑 python3 scripts/sanity_check.py | ✅ 已確認：2026-07-16 使用者確認 vault/wiki content quality OK |

---

## 四、Wiki Note 格式（4 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 15 | ~~所有 wiki note 有完整 frontmatter~~ | `uv run pytest tests/contracts -q` | ✅ 已確認：2026-07-16 contracts `7 passed` |
| 16 | Wikilink 格式正確（[[entity-slug]] 可在 Obsidian 點擊跳轉） | 在 Obsidian 點幾個 wikilink | ☐ 需你確認：需 Obsidian 點擊/Graph View |
| 17 | Entity page 存在對應的 wiki note（不是死連結） | Obsidian Graph View 無孤立紅點 | ☐ 需你確認：需 Obsidian Graph View |
| 18 | wiki/_registry/entities.yaml 是 canonical 來源（code 無硬編碼 dict） | grep -r "CANONICAL_ENTITIES\s*=" bot/ 應無結果 | ☐ 需實作/重構：目前 canonical registry 仍在 `src/personalkm/propagate/entity_dedup.py` 程式碼中 |

---

## 五、LLM Router（5 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 19 | ~~`python3 -m pytest tests/contracts -q` 通過~~ | Terminal 跑 | ✅ 已確認：2026-07-16 contracts `7 passed` |
| 20 | ~~`python3 -m personalkm.llm.usage report` 有輸出今日用量~~ | Terminal 跑 | ✅ 已確認：2026-07-16 usage report 有 `minimax` / `ollama` 用量 |
| 21 | 現有 ingest/propagate/query 已改用 route() 而非直接呼叫 SDK | grep -r "MiniMaxClient\|get_default_client" bot/ 應無結果 | ☐ 需實作/重構：`bot/llm_clients.py` legacy path 仍存在；主線 ingest/query 已用 router |
| 22 | ~~Budget fallback 行為有測試覆蓋~~ | contract test: over-budget provider skipped | ✅ 已確認：`test_over_budget_provider_is_skipped` 通過；若要指定 MiniMax live config，仍可另做手動驗證 |
| 23 | ~~Pipeline LLMError 會觸發 alert hook~~ | contract test: all exhausted sends alert | ✅ 已確認：`test_all_exhausted_sends_llm_alert` 通過；實際 LINE/Discord channel delivery 需另用真 webhook 驗證 |

---

## 六、可查詢性（3 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 24 | 從 LINE 問一個 wiki 裡有答案的問題，得到正確回答 | 實際測試 3 個問題 | ☐ 需你確認：query engine 已有測試，但 LINE 查詢體驗需 live 測 |
| 25 | 問一個 wiki 裡沒有的問題，AI 明確說不知道（不是亂答） | 實際測試 | ☐ 需你確認：需 live query 測試 |
| 26 | 查詢回應在 10 秒內 | 計時 | ☐ 需你確認：需 live latency 測試 |

---

## 七、系統穩定性（3 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 27 | Mac Mini hourly cron 連續跑 48 小時無靜默失敗 | 看 launchd log | ☐ 需你確認：需 Mac Mini launchd log 連續 48 小時證據 |
| 28 | Vault repo 和 code repo 已分離（vault 是 private） | GitHub 確認 | ☐ 需你確認：需 GitHub repo visibility/remote 設定證據 |
| 29 | ~~Render health check 回 200~~ | `curl -i https://personal-km-line-bot.onrender.com/health` | ✅ 已確認：2026-07-16 `HTTP/2 200`, body `{"status":"ok"}`；「長期穩定」仍需監控 |

---

## 更新紀錄

| 日期 | 變更 |
|------|------|
| 2026-07-04 | 初版建立，項目 15 / 19 已完成（contracts 全綠） |
| 2026-07-16 | 重新標記已確認交付項目：15、19、20、22、23、29；其餘保留為需你 live/manual 確認或需實作/重構。 |
| 2026-07-16 | 使用者確認 live LINE capture 測試通過：一般 URL、YouTube、純文字、failure/auth-required social URL；標記項目 1、4、6、7。 |
| 2026-07-16 | 使用者確認 vault/wiki content quality checks OK；標記項目 10-14。 |
