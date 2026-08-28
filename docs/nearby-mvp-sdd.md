# Nearby MVP — Software Design Description

> 狀態：Ready for implementation（本文件只定義設計，尚未改動 runtime code）
> 版本：0.1
> 日期：2026-08-28
> Requirement：[`nearby-mvp-requirements.md`](nearby-mvp-requirements.md)

## 1. 設計邊界

本設計沿用 PersonalKM 現有雙 vault 與 LINE Bot 架構：Render 接收 LINE、GitHub 作 durable queue、Mac Mini 執行 ingest／propagate；Nearby 是 Query stage 的讀取能力。Lifestyle Vault 是唯一收藏資料來源，Tech Vault 不參與 Nearby。

Capture stage 只負責驗證事件、解析必要的 user／reply context 與委派；Nearby parser、registry 查詢、距離計算與外部 provider 都放在 Query stage，避免把查詢副作用塞回 capture。

## 2. 現況對接點

| 現有位置 | 目前責任 | Nearby 對接 |
|---|---|---|
| `src/personalkm/capture/app.py` | `/webhook/line`、文字事件背景處理、按 category 選 vault、`save_note()` | 增加事件分派與 Nearby reply adapter；不得在此實作 registry／Places／距離邏輯。 |
| `src/personalkm/capture/line.py` | LINE signature、文字事件解析、URL 抽取、mark-as-read | 擴充 location event、`replyToken` 與聊天室 source metadata，並提供純文字 reply API。 |
| `src/personalkm/capture/config.py` | env-backed `Settings`、tech／lifestyle vault 設定 | 增加 allowlist、registry 相對路徑、Google provider 設定。 |
| `src/personalkm/capture/git_store.py` | `VaultConfig`、clone／pull／commit／push；目前 capture sparse checkout 只 materialize `raw/` | 增加 Query 專用唯讀 checkout helper，只 materialize `wiki/_registry/`；收藏動作重用既有 `ensure_vault`／`commit_and_push`。 |
| `src/personalkm/query/query_engine.py` | 一般 wiki／raw／resolved query 與 LLM answer | 保持既有 `/query` 行為；Nearby service 作獨立 deterministic path。 |
| `src/personalkm/capture/notes.py` | `LinkNote`、raw Markdown render | 收藏 adapter 產生既有格式可接受的 Lifestyle raw capture。 |
| `config/cron_jobs.yaml` | tech／lifestyle Phase A/B/C 排程 | 不新增 Nearby cron；registry 由既有 Lifestyle enrichment 維護。 |

## 3. 目標架構

```text
LINE webhook
  │
  ├─ location event / GPS text ──► LocationStore (process memory, user_id key)
  │                                  └─ confirmation reply
  │
  └─ text event ──► NearbyIntentRouter
                       ├─ not Nearby ──► existing capture flow
                       └─ Nearby ──► NearbyService
                                      ├─ parse / validate intent
                                      ├─ load Lifestyle vault snapshot
                                      │    wiki/_registry/city-subject-store.json
                                      ├─ deterministic filter + Haversine rank
                                      ├─ optional GooglePlacesProvider (+ only)
                                      ├─ de-duplicate (Place ID/address/GPS/name)
                                      └─ PlainTextRenderer ──► LINE reply

"收藏第 N 家"
  └─► ResultSession (≤30 min, user_id key)
       └─► Existing Lifestyle capture pipeline
             raw/ → Phase A → wiki/ → enrichment → registry
```

### 元件責任

1. **Intent router**：用明確、可測試的規則判斷 Nearby；非 allowlist 或非 Nearby 文字原樣回既有 capture。
2. **Parser**：解析位置、主題／subject、交通模式、分鐘、`+`、數量、營業／評分 filters；不使用 LLM。
3. **Location store**：只保存 user-scoped last location；不落盤、不進 vault。
4. **Registry repository**：讀取 JSON、檢查 schema、建立不可變 snapshot；只回傳有效 entry。
5. **Geo/ranking**：Haversine 距離與固定速度換算；所有結果走同一套 filter／sort。
6. **Google Places provider**：只在 Plus 或使用者明確要求驗證已收藏 POI 的即時營業狀態時呼叫；provider 只讀不寫資料。
7. **Result session**：保存最近一輪已排序結果、查詢摘要與建立時間，供收藏指令解析。
8. **Renderer**：產生 MVP 純文字回覆；不在每筆重複估算免責聲明。
9. **Capture adapter**：把明確收藏的 POI 轉成既有 Lifestyle raw capture，交回現有 ingest，不碰 registry。

## 4. 事件與查詢流程

### 4.1 LINE 事件分派

`line.py` 將文字與 location message 正規化為共用事件模型，帶有 `user_id`、聊天室類型／source、LINE `replyToken`（若可用）與內容。`app.py` 只做順序控制：

1. 驗證 LINE signature。
2. 對 allowlist user 將 location／GPS 事件送 LocationStore。
3. 對 allowlist user 的文字先交 NearbyIntentRouter。
4. Router 回傳 `NOT_NEARBY` 時，沿用目前 URL／pasted-text capture；回傳 `NEEDS_INPUT` 時回追問；回傳 `RESULT`／`ACTION` 時由 Nearby reply／capture adapter 處理。
5. 群組與 1:1 使用同一 user-scoped state；其他使用者的訊息不讀取該 state。

### 4.2 Intent 判斷與追問

MVP 先採 deterministic parser，避免 LLM 分類延遲與不可預測副作用：

- Nearby cue：位置 + 附近／有沒有／找／推薦等查詢語意，或已有位置時的同類自然語言查詢。
- `+`／`＋`：移除符號後保留原 query，並設 `plus=true`。
- mode：`walk`／`drive` 的同義詞映射。
- time：解析整數分鐘；不接受無法明確換算的模糊值。
- count：`前 N`、`N 家`、`全部`；預設 5。
- filters：`現在營業`、`評分 X 以上`、店家類型／subject；明確指定即設為 hard filter。

Parser 輸出：

```text
NearbyQuery {
  subject_terms: list[str]
  mode: walk | drive | missing
  max_minutes: int | missing
  plus: bool
  count: int | all
  open_now: bool | unset
  min_rating: float | unset
  source_scope: saved | saved_plus_web
}
```

若 mode 或 max_minutes 缺少，回傳缺欄位而非套預設；`PendingIntentStore` 暫存原 query 與已解析欄位，下一則回答合併後重跑 parser。沒有位置時優先回「可能服務重新啟動」提示。

### 4.3 Registry snapshot

由 Query 專用的唯讀 checkout helper 取得 Lifestyle clone／path；該 helper 使用 `_get_vault_config(settings, "food")` 的 repo／branch，在獨立 query path 以 sparse-checkout materialize `wiki/_registry/`，不與 capture 的 `raw/` sparse worktree 共用 index。若設定缺失或檔案不存在，直接回可理解的 unavailable 結果。每次查詢讀取一次 JSON，或以檔案 mtime 做 process-local cache；cache key 必須含 vault path 與 mtime，避免雙 vault 混用。

只接受 `entries` 陣列中 `gps` 為兩個有限數字的 entry。`status` 為永久停業／不存在的 entry 不列為候選；其他狀態原樣帶出。缺 `rating`、`rating_count` 或 `highlights` 時省略該行。來源頁面使用 `source` 建立可點擊連結，但不在 query time 讀 wiki 補資料。

### 4.4 篩選、距離與排序

1. 先依 subject／store／city／highlights 的正規化文字篩選。
2. `distance_km = haversine(origin, entry.gps)`。
3. `max_distance_km = max_minutes × speed_kmh / 60`，其中 `walk=4.5`、`drive=20`。
4. 僅保留 `distance_km <= max_distance_km`，再套用 open_now／min_rating 等 hard filters。
5. 以 `(distance_km, stable_id)` 排序，確保同距離結果穩定。
6. `estimated_minutes = round(distance_km / speed_kmh × 60)`；整段回覆附註「時間為第一階段粗估，非即時導航時間」。

多 subject 查詢不分組，所有符合項目統一由近到遠。0 筆時重新執行最多三個「只放寬一項」的候選計算（例如 +10 分鐘、降低 rating、移除 open_now），只報告數量與新條件，不改原結果。

### 4.5 Plus provider 與去重

`GooglePlacesProvider` 的輸入是 `(subject_terms, origin, radius, optional open_now)`，輸出只保留必要欄位：`place_id`、name、address、gps、rating、rating_count、business_status、maps_url。API key 來自 env，禁止記錄完整 key。

- 無 `+`：不得搜尋新 POI。若明確要求即時營業，provider 只能驗證已收藏 ID；這是一次性唯讀驗證，不更新 registry。一般查詢不做此呼叫。
- 有 `+`：搜尋網路候選，先排除永久停業，再與 registry 去重。
- 去重優先序：相同 `place_id` → 正規化地址相同 → GPS 小於明確 proximity threshold 且名稱相似。低信心只標「可能已收藏」，不歸入網路新店。
- 已收藏與網路結果各自套用相同距離／時間／hard filters，各自最多 5 筆（除非 query 指定其他數量）。

## 5. 回覆與 session contract

### 5.1 純文字回覆

每筆結果至少：

```text
1. ★ 店名 — 3.2 km｜約 10 分鐘
   主題：牛肉麵｜地址：...
   ⭐ 4.4（2,341 則）
   GPS：25.xxxxxx, 121.xxxxxx
```

Plus 回覆先輸出 `★ 已收藏`，再輸出 `＋ 網路發現`；有 highlights 才加入「特色」行。結尾只註明一次估算限制，並在存在網路結果時詢問是否加入收藏。

### 5.2 ResultSession

```text
key: user_id
created_at: timezone-aware timestamp
expires_at: created_at + 30 minutes
query_fingerprint: normalized query + location + registry/provider snapshot ids
items: ordered result items with source_kind and provider identifiers
```

新 Nearby 查詢覆蓋同 user 的 session。收藏 parser 僅接受未過期 session；index 以當次顯示順序計算。名稱指令須在當次結果中唯一匹配，否則回歧義提示，不猜測。

## 6. 收藏 adapter 與既有管線

Nearby 不直接寫 `city-subject-store.json`。`CaptureAdapter` 將選定 POI 轉成 Lifestyle capture，包含店名、地址、GPS、Google Maps URL、`place_id`、`source_context: nearby_plus` 與可取得的 rating／highlights，然後呼叫現有 `save_note()`／`commit_and_push()`。後續仍由 Lifestyle 的 Phase A／enrichment／registry runner 產生正式 entry。

若 capture 失敗，回報未完成且保留原 ResultSession（直到 expiry）；不得假裝已收藏。若重複收藏同一 Place ID，adapter 應回「已送出／可能已存在」並交由既有去重規則處理。

## 7. 設定與檔案層級變更計畫

以下是下一個 implementation change set；本輪不執行。

### 新增檔案

| 檔案 | 內容與邊界 |
|---|---|
| `src/personalkm/query/nearby_models.py` | `Location`、`NearbyQuery`、`PlaceCandidate`、`ResultSession`、解析結果／錯誤型別；公開型別完整 type hints。 |
| `src/personalkm/query/nearby_parser.py` | 純 deterministic parser、GPS parser、缺欄位追問資料、收藏指令 parser；不呼叫網路／LLM。 |
| `src/personalkm/query/nearby_location.py` | user-scoped process-memory location／pending intent store；不落盤、不寫 log 內容。 |
| `src/personalkm/query/nearby_registry.py` | Lifestyle vault path resolution、JSON schema validation、mtime cache、subject／status 篩選。 |
| `src/personalkm/query/nearby_geo.py` | Haversine、固定速度、距離／粗估時間與 stable sort。 |
| `src/personalkm/query/nearby_places.py` | Google Places client boundary、response mapping、API error／quota fail-closed、Place ID 去重。 |
| `src/personalkm/query/nearby_service.py` | orchestration：位置檢查 → registry → filter/rank → optional provider → session；不直接寫 vault。 |
| `src/personalkm/query/nearby_renderer.py` | MVP 純文字 renderer、追問／錯誤／0 筆放寬建議／收藏提示。 |
| `tests/test_nearby_*.py` | parser、geo、registry、session expiry、dedupe、renderer、authorization 的單元與 contract tests。 |

### 修改檔案

| 檔案 | 變更 |
|---|---|
| `src/personalkm/capture/line.py` | 擴充 LINE `message.type=location` 解析、`replyToken`／source 欄位與純文字 reply；保留現有文字／URL API 相容性。 |
| `src/personalkm/capture/app.py` | 在既有 capture 前加入 allowlist-aware Nearby dispatch；只負責委派與回覆，普通 capture 路徑不變；接上 `CaptureAdapter`。 |
| `src/personalkm/capture/config.py` | 增加 `ALLOWED_LINE_USER_IDS`、`LIFESTYLE_REGISTRY_PATH`（預設 `wiki/_registry/city-subject-store.json`）、`GOOGLE_PLACES_API_KEY` 與可調速率／TTL設定。 |
| `config/settings.yaml` | 放非秘密 Nearby defaults（registry 相對路徑、`walk_kmh: 4.5`、`drive_kmh: 20`、`result_ttl_minutes: 30`、每區上限 5）。秘密仍只走環境變數。 |
| `src/personalkm/capture/notes.py` | 若既有 `LinkNote` 欄位不足，增加最小、向後相容的 capture metadata（尤其 `source_context`／`place_id`）；不改既有 frontmatter contract，必要時同步 contract test。 |
| `src/personalkm/query/__init__.py` | 匯出 Nearby service 的穩定入口；不改既有 `query_wiki` API。 |

### 明確不修改

`bot/*.py` 相容 shim、`src/personalkm/ingest/`、`src/personalkm/propagate/`、`config/models.yaml`、Lifestyle Vault 內容與 registry 檔案、既有一般 `/query` contract。Nearby 不新增 cron，也不把 Google Places 結果直接寫入 registry。

## 8. 測試與驗收策略

### 單元／contract

- GPS 格式、範圍、可疑座標提醒；walk／drive 速度與 Haversine 已知值。
- parser 對中英文與全／半形 `+`、前 N／全部、open_now／rating filter 的表格測試。
- 缺 mode／time 的追問與 pending intent merge。
- registry fixture 包含缺 GPS、停業、缺 rating、海外座標、多 subject。
- Plus 去重：Place ID、地址、近距離同名、低信心「可能已收藏」。
- 30 分鐘 expiry、新查詢覆蓋、index／名稱／全部收藏指令。
- allowlist 隔離與「不呼叫 provider」的 mock assertion。
- CaptureAdapter 只產生 raw capture，且不呼叫 registry write。

### 手動／整合 gate

使用測試 fixture 與 mock Google provider，實際走 LINE webhook event → reply 的 10 個 Requirement 驗收情境；確認既有 URL capture、mark-as-read 與 dual-vault routing 無回歸。未取得 Google key 時應驗證 fail-closed 訊息，不以 HTTP 200 或 mock 呼叫本身宣稱 provider 成功。

## 9. 實作順序與發佈邊界

1. 先落地 models／parser／geo／location，完成無網路的 contract tests。
2. 接 registry snapshot 與 renderer，對 Lifestyle fixture 完成收藏-only query。
3. 接 LINE location／allowlist dispatch，驗證普通 capture 不變。
4. 加 ResultSession／收藏 adapter，驗證 30 分鐘與既有 Lifestyle pipeline。
5. 最後加入 Google provider／Plus，先以 mock 驗證去重、quota／error；取得明確授權與秘密後才做受控 live check。

每一步都保持 query read-only 與雙 vault 隔離；任何 registry schema 或 frontmatter 欄位變更，必須同一變更集更新對應 contract tests。
