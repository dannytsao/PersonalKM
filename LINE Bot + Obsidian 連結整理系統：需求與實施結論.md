# LINE Bot + Obsidian 連結整理系統：需求與實施結論

更新日期：2026-06-10

## 一、專案目標

建立一個低成本、可靠、可追蹤的個人知識收集漏斗：在 LINE 群組中分享連結、長文或分段文章後，系統自動保存原始資訊，轉成統一 Markdown 筆記，推送到 GitHub，最後同步到 Obsidian。

核心目標不是只做「連結摘要」，而是把外部凌亂、格式不一的資訊，先在後端整理成可長期維護的 `.md` 知識素材，再交給 Obsidian 後續整理成 wiki。

## 二、目前實施結論

目前採用的方案是：

**LINE Bot on Render + GitHub repo as durable queue + Obsidian Git + Mac mini local worker**

選擇原因：

- Render 負責即時接收 LINE webhook，不需要 Mac mini 一直開著。
- GitHub repo 是可靠暫存層，所有 raw notes、pending 狀態與 worker 結果都有版本控制。
- Obsidian 透過 Git 同步，不需要直接連線到 Render 或 Mac mini。
- YouTube、Google AI Mode、X、Threads 等雲端不易完整擷取的平台，先保存 partial/blocked note，再由 Mac mini worker 補強。
- Mac mini worker 只在電腦開著時運作，成本為 0；關機時 pending notes 仍安全留在 repo。

## 三、核心需求與目前狀態

| 項目 | 目前狀態 |
|:-----|:---------|
| LINE 群組文字與連結接收 | 已完成，Render live service 接收 webhook |
| URL 偵測 | 已完成，支援同一則訊息多個 URL |
| 長文保存 | 已完成，完整 LINE pasted text 會保存成 note |
| 分段長文合併 | 已完成，支援 `[文章 1/3]` 這類分段格式 |
| `log_id` 追蹤 | 已完成，格式為 `YYYYMMDDHHMM_00001` |
| 同一則 LINE 訊息的多篇 note 共用 `log_id` | 已完成 |
| LINE 已讀標示 | 已完成，成功寫入 repo 後呼叫 LINE mark-as-read |
| Markdown 標準化 | 已完成，URL、社群貼文、AI Mode、貼文文字統一成 canonical Markdown |
| Worker queue metadata | 已完成，新舊 raw notes 都已補上 worker 欄位 |
| Mac mini local worker | 已完成，可自動處理 pending YouTube notes |
| Mac mini worker 自動排程 | 已完成，launchd 每 15 分鐘跑一次 |
| Render plan | 已改 Starter，避免 Free plan idle spin down |

## 四、系統架構

```text
LINE group message
    ↓
LINE Messaging API webhook
    ↓
Render web service: personal-km-line-bot
    ↓
Parse text, merge multipart posts, extract URLs, assign log_id
    ↓
Generate canonical Markdown notes under raw/
    ↓
Write YAML metadata: platform, extraction_status, worker_status, log_id
    ↓
Commit and push to GitHub repo
    ↓
LINE mark-as-read after successful repo write
    ↓
Obsidian Git pulls notes into local vault
```

對於需要本機補強的平台：

```text
raw note with worker_status: pending
    ↓
GitHub repo as durable queue
    ↓
Mac mini launchd worker checks every 15 minutes
    ↓
Dedicated worker clone: ~/.personalkm/PersonalKM-worker
    ↓
yt-dlp / whisper.cpp / Ollama qwen3:8b
    ↓
Update note body and YAML metadata
    ↓
Commit and push back to GitHub
    ↓
Main Obsidian repo pulls enriched note
```

## 五、Vault / Repo 結構

目前主要入口已從舊的 `Inbox/` 演進為 `raw/`。

```text
raw/
├── Food/          LINE Bot 新捕獲的美食與旅遊資訊
├── Photography/  攝影景點與影像相關資訊
├── Tech/         技術、AI、工具與工程資訊
└── General/      尚未明確分類或一般資訊

wiki/
├── entities/     後續整理出的工具、人物、品牌、地點等實體
├── concepts/     知識概念與主題整理
├── sources/      來源型資料
└── knowledge-graph.md

outputs/          自動生成報告
Archive/          歷史資料與舊 Inbox 遷移
Trash/            已刪除資料
Templates/        Obsidian 模板
```

`raw/` 是收集與清洗後的 canonical note 暫存區；後續 wiki 化流程可以再把 raw note 組織進 `wiki/`。

## 六、Canonical Markdown 筆記格式

每篇由 LINE Bot 或 worker 產生的 note 都應盡量符合以下 YAML/Markdown 結構。

```markdown
---
tags: [技術]
source: LINE
date: 2026-06-10
log_id: 202606101106_00001
url: https://example.com
platform: youtube
content_type: video
extraction_status: partial
needs_review: true
needs_local_worker: true
worker_status: pending
worker_type: omnichannel_md
worker_retry_count: 0
summary: AI 自動摘要
status: unread
---

# Note title

## Log ID
202606101106_00001

## 摘要
...

## 重點
- ...

## 原始內容
...

## 內含連結
- ...

## 擷取狀態
- 平台：youtube
- 擷取狀態：partial
- 需要人工確認：true

## 原文連結
https://example.com
```

重要欄位說明：

| 欄位 | 用途 |
|:-----|:-----|
| `log_id` | 追蹤一次 LINE capture；同一則訊息拆出的多篇 note 共用同一 ID |
| `platform` | 來源平台，例如 `web`、`youtube`、`instagram`、`x`、`threads`、`google-ai-mode` |
| `content_type` | 內容型態，例如 `web_page`、`video`、`social_post`、`line_message` |
| `extraction_status` | `ok`、`partial`、`blocked`、`error` |
| `needs_review` | 是否需要人工或 local worker 後續確認 |
| `needs_local_worker` | 是否需要 Mac mini worker 補強 |
| `worker_status` | `not_required`、`pending`、`done`、`failed` |
| `worker_retry_count` | local worker 已嘗試次數 |

## 七、平台處理策略

| 平台/內容 | Render 端策略 | Mac mini worker 策略 |
|:----------|:---------------|:---------------------|
| 一般網頁 | 直接擷取 metadata / page text，產生 canonical Markdown | 通常不需要 |
| LINE 貼文文字 | 保存完整貼文與內含連結 | 通常不需要 |
| YouTube | 優先擷取標題、metadata、字幕；不足時標記 pending | 用 `yt-dlp` 取字幕；必要時用 `whisper.cpp` 轉錄音訊，再用 Ollama 摘要 |
| Instagram / TikTok | 使用可取得的 open graph / 貼文資訊；受阻時保存 partial/blocked | 未來可擴充 local browser 或其他低成本補強 |
| X / Threads | 保存可取得 metadata；登入牆或 blocked 時標記 pending/blocked | 目前先保留 queue metadata，後續再擴充 |
| Google AI Mode share | 不繞過 `share.google/aimode/...` 的 429/blocked；若使用者貼上回答文字，直接整理貼文內容 | 目前不嘗試 bypass，避免不穩定與高成本 |

## 八、Mac mini Worker 自動化

Mac mini worker 已用 `launchd` 安裝。

目前行為：

- 每 15 分鐘自動跑一次。
- 每次只處理 1 篇 pending note，避免一次改動太多歷史筆記。
- 使用 lock 避免重疊執行。
- 使用專用 clone：`~/.personalkm/PersonalKM-worker`。
- 成功後自動 commit/push 回 GitHub。
- 如果 Mac mini 關機，pending notes 會留在 GitHub repo，下一次開機/登入後繼續。

查看狀態：

```bash
launchctl print gui/$(id -u)/com.dannytsao.personalkm.omnichannel-worker
```

查看 log：

```bash
tail -n 80 ~/Library/Logs/PersonalKM/omnichannel-worker.out.log
tail -n 80 ~/Library/Logs/PersonalKM/omnichannel-worker.err.log
```

手動立即觸發：

```bash
launchctl kickstart -k gui/$(id -u)/com.dannytsao.personalkm.omnichannel-worker
```

## 九、成本與可靠性結論

目前最便宜且可靠的組合是：

- Render Starter web service：維持 LINE webhook 常駐，避免 free idle spin down。
- GitHub private repo：作為資料儲存、版本控制與 durable queue。
- Obsidian Git：本機同步。
- Mac mini local worker：只處理雲端不適合處理的重任務，例如 YouTube audio/transcript recovery。
- Ollama `qwen3:8b`：本地摘要與 Markdown 補強，避免增加雲端 token 成本。

這個架構比「所有事情都在 Render 做」更省錢，也比「全部依賴 Mac mini」更可靠，因為 LINE webhook 不會因 Mac mini 關機而漏接。

## 十、已知限制

- Social platforms 例如 X、Threads、Instagram、TikTok 常有登入牆、反爬或 metadata 不完整問題；目前策略是保存可取得資訊並標記狀態，而不是硬抓。
- Google AI Mode share link 可能出現 429 或 blocked；目前不嘗試 bypass，使用者若貼上 AI Mode 回答文字，系統會保存並整理該文字。
- Mac mini worker 目前主要成熟支援 YouTube 補強；其他社群平台 local recovery 仍是後續擴充方向。
- Obsidian wiki 後續整理品質取決於 raw note 的完整度；因此 `worker_status: pending` 的 note 代表仍可再補強。

## 十一、後續擴充方向

- 擴充 Mac mini worker 對 X、Threads、Instagram 的低成本 local recovery。
- 增加 worker dashboard 或 Dataview query，快速查看 pending/failed notes。
- 增加針對 `worker_status: failed` 的重試策略與人工標記流程。
- 強化 wiki 化流程，讓 `raw/` 中的 canonical Markdown 更穩定整理到 `wiki/entities`、`wiki/concepts`。
- 建立每日或每週 ingestion report，列出新增 notes、pending notes、failed notes 與已補強 notes。

## 十二、目前結論

本系統已從早期的「LINE Bot + Inbox」概念，升級為一個全通路資訊收集漏斗：

```text
LINE input
  → Render canonical Markdown normalizer
  → GitHub durable queue
  → Obsidian raw notes
  → Mac mini local enrichment
  → Obsidian wiki workflow
```

目前設計符合兩個核心原則：

- **先完整保存，再逐步補強。**
- **雲端負責即時可靠，本機負責低成本重運算。**
