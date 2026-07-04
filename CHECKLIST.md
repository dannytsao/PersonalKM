# Karpathy LLM Wiki 入口完成檢查表

> 最後更新：2026-07-04
> 用途：確認系統已達到「Karpathy LLM Wiki 入口」標準，才往前推進知識深化（Distillation Loop）。
> 全部 29 項打勾 → 可以開始實作 `SPEC.md` 第二節。

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
| 1 | LINE Bot 收到訊息後 raw note 在 60 秒內出現在 vault | 貼一則訊息，看 vault repo commit 時間 | ☐ |
| 2 | Raw note 有正確 frontmatter（created / source / url / fetch_status: pending） | 打開任一 raw note 檢查 | ☐ |
| 3 | Bot 掛掉或 Render timeout 不會導致訊息遺失（webhook 有 retry） | 看 Render logs | ☐ |
| 4 | 純文字訊息（無 URL）也能正確 capture | 貼一段純文字測試 | ☐ |

---

## 二、Resolve 功能（5 項）

> 注意：Resolve layer 尚未實作（MIGRATION.md Step 5）。
> 待實作完成後再驗證此欄。

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 5 | GitHub URL → fetch_status: fetched，content 有 README 內容 | 貼一個 GitHub repo URL | ☐ |
| 6 | 一般新聞 URL → fetch_status: fetched，content 有正文 | 貼一篇新聞連結 | ☐ |
| 7 | IG / Threads URL → fetch_status: auth_required，有 stub wiki note | 貼一個 IG 連結 | ☐ |
| 8 | 失敗的 URL 在下一個 hourly cycle 有 retry（retry_count 遞增） | 看 raw note frontmatter | ☐ |
| 9 | fetch_status: pending 的 note 不會進入 LLM 合成 | 檢查 ingest log | ☐ |

---

## 三、Wiki Note 內容品質（5 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 10 | Summary 是 AI 真正讀過內容後產的（不是從 URL 猜測） | 打開 5 個 wiki note 對照原文 | ☐ |
| 11 | Tags 和 topic 與內容相符 | 抽查 10 個 note | ☐ |
| 12 | Entities 對應到 canonical entity slugs（不是自由發揮的字串） | grep entities wiki/**/*.md \| head -20 | ☐ |
| 13 | 沒有 skip_llm=True 產出的假 wiki note | grep -r "skip_llm" wiki/ 應無結果 | ☐ |
| 14 | confidence: low 的 note 有被 sanity_check 列出 | 跑 python3 scripts/sanity_check.py | ☐ |

---

## 四、Wiki Note 格式（4 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 15 | 所有 wiki note 有完整 frontmatter | python3 -m pytest tests/contracts -q 全綠 | ✅ 已完成 |
| 16 | Wikilink 格式正確（[[entity-slug]] 可在 Obsidian 點擊跳轉） | 在 Obsidian 點幾個 wikilink | ☐ |
| 17 | Entity page 存在對應的 wiki note（不是死連結） | Obsidian Graph View 無孤立紅點 | ☐ |
| 18 | wiki/_registry/entities.yaml 是 canonical 來源（code 無硬編碼 dict） | grep -r "CANONICAL_ENTITIES\s*=" bot/ 應無結果 | ☐ |

---

## 五、LLM Router（5 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 19 | python3 -m pytest tests/contracts -q 6 passed | Terminal 跑 | ✅ 已完成 |
| 20 | python3 -m personalkm.llm.usage report 有輸出今日用量 | Terminal 跑 | ☐ |
| 21 | 現有 ingest/propagate/query 已改用 route() 而非直接呼叫 SDK | grep -r "MiniMaxClient\|get_default_client" bot/ 應無結果 | ☐ |
| 22 | 手動把 minimax daily budget 調成 1，確認自動切到 fallback | 改 models.yaml 測試後改回 | ☐ |
| 23 | Pipeline 任何 LLMError 會推 LINE 告警 | 故意讓一個 stage 失敗測試 | ☐ |

---

## 六、可查詢性（3 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 24 | 從 LINE 問一個 wiki 裡有答案的問題，得到正確回答 | 實際測試 3 個問題 | ☐ |
| 25 | 問一個 wiki 裡沒有的問題，AI 明確說不知道（不是亂答） | 實際測試 | ☐ |
| 26 | 查詢回應在 10 秒內 | 計時 | ☐ |

---

## 七、系統穩定性（3 項）

| # | 項目 | 驗證方式 | 狀態 |
|---|------|---------|------|
| 27 | Mac Mini hourly cron 連續跑 48 小時無靜默失敗 | 看 launchd log | ☐ |
| 28 | Vault repo 和 code repo 已分離（vault 是 private） | GitHub 確認 | ☐ |
| 29 | Render health check 穩定回 200 | curl https://personal-km-line-bot.onrender.com/health | ☐ |

---

## 更新紀錄

| 日期 | 變更 |
|------|------|
| 2026-07-04 | 初版建立，項目 15 / 19 已完成（contracts 全綠） |
