# Nearby MVP — Requirements Specification

> 狀態：Ready for implementation（僅文件，尚未改動 runtime code）
> 版本：0.1
> 日期：2026-08-28

## 1. 目的與問題

PersonalKM 已有 LINE → Render → GitHub → Lifestyle Vault 的收藏管線，以及由 `wiki/_registry/city-subject-store.json` 維護的城市／主題／店家資料。Nearby MVP 讓使用者以同一個 LINE Bot，從目前位置快速查詢「我已收藏的地點」；只有明確加上 `+`／`＋` 時，才擴展到 Google Places 的網路候選。

本 MVP 的目標是「第一時間可判斷」，不是即時導航或另一個 Google Maps：距離使用直線距離，時間使用固定速度粗估。

## 2. 範圍

### In scope

- 1:1 與 LINE 群組皆可使用；只允許設定的 LINE user ID 觸發 Nearby。
- 位置輸入：文字經緯度（`lat, lon`）與 LINE 原生 location message。
- 以使用者最後一次位置作為參考；同一 user ID 跨群組與 1:1 共用。
- 自然語言條件：主題／店家類型、距離或時間、走路／開車、`+`／`＋`、數量、營業狀態、評分等明確 filter。
- 預設只讀 Lifestyle Vault registry；結果由近到遠排序。
- `+` 模式分成「★ 已收藏」與「＋ 網路發現」，各最多 5 筆。
- 顯示店名、距離、粗估時間、GPS；有資料時顯示 rating／review count 與收藏 highlights。
- 保留最近一次 Nearby 結果 30 分鐘；新查詢覆蓋舊結果。
- 支援「收藏第 2 家」、「收藏 B」、「收藏 1、3」、「全部收藏」等明確指令，並沿用既有 Lifestyle capture pipeline。

### Out of scope（Phase 2 以後）

- 地名／地址 geocoding（MVP 必須有 GPS）。
- 即時導航路線、路況、道路距離或真實 ETA。
- Nearby 查詢時替已收藏 POI 補 GPS、查歇業或更新 rating。
- Nearby 直接寫入 registry、直接改 wiki、或自動收藏 Google Places 結果。
- Flex Message、多人共享位置／權限模型、持久化位置資料庫。

## 3. 名詞與資料來源

| 名詞 | 定義 |
|---|---|
| 已收藏 | Lifestyle Vault registry 中的有效 entry（`status` 不為永久停業／不存在），來源標示為 `★`。 |
| 網路發現 | `+`／`＋` 觸發 Google Places 查到、且去重後不是已收藏的 POI，來源標示為 `＋`。 |
| 位置 | 使用者最近提供的合法 `(latitude, longitude)`；MVP 僅存在 Render process memory。 |
| registry | `wiki/_registry/city-subject-store.json`，唯一的 Nearby 收藏讀取來源。 |
| 明確 filter | 使用者明說的條件，例如「現在營業」、「評分 4.5 以上」、「前 10 家」。不得被系統默默放寬。 |

registry entry 至少使用下列欄位：`id`、`city`、`subject`、`store`、`source`、`address`、`gps`、`status`、`highlights`、`rating`、`rating_count`；可選 `place_id`（Google Place ID）。欄位缺漏時顯示可取得資料，不編造。

## 4. 使用流程

### 4.1 設定位置

使用者傳文字 GPS 或 LINE 原生位置後，Bot 回覆：

> 已記住位置：`lat, lon`
> 你可以問：「走路 10 分鐘內有什麼餐廳？」

位置以 LINE user ID 為 key，跨群組／1:1 共用；傳入新位置即覆蓋舊位置。Render restart／redeploy 後記憶可能消失，下一次 Nearby 查詢必須明確說明「目前沒有已記住的位置，可能是服務重新啟動」，並要求重新傳 GPS。

若座標格式合法但明顯可疑，不自動修正；先指出疑點並等待使用者確認。

### 4.2 完整查詢

例如：

`開車 20 分鐘內有沒有牛肉麵？`

1. 解析 intent。
2. 若有足夠條件，讀 Lifestyle registry。
3. 套用主題／狀態／評分等 filter。
4. 以 Haversine 直線距離計算，限制在時間換算範圍內，依近到遠排序。
5. 預設回最多 5 筆；「前 10 家」或「全部」改變顯示上限。

若未說交通方式或時間，不使用預設值，先追問缺少的欄位；回答後沿用原查詢上下文完成查詢。

### 4.3 Nearby Plus

`開車 20 分鐘內牛肉麵＋`

- 先回「★ 已收藏」，再回「＋ 網路發現」；兩組各自由近到遠、各最多 5 筆。
- Google Places 只在明確 `+`／`＋` 時搜尋新候選；同時可補充網路候選的 rating、review count、營業狀態與基本 POI 欄位。
- 已收藏優先去重，不在兩區重複顯示。低信心疑似同店時標示「可能已收藏」，不硬判為新店。
- `+` 預設排除永久停業／不存在；休息中、尚未營業或今日未開仍可列出並標示狀態。若使用者明說「現在營業」，只列營業中。
- 回覆結尾詢問「要不要加入收藏？」；不自動寫入。

沒有 `+` 時，不搜尋新 POI。若使用者明說「現在營業」，允許只對已收藏 entry 做一次唯讀狀態驗證，但不得擴張候選名單；平常查詢仍以 registry 既有狀態為準，任何狀態更新由上游 enrichment 負責。

### 4.4 收藏結果

只有明確指令才寫入，例如「收藏第 2 家」、「收藏 B」、「收藏 1、3」、「全部收藏」。30 分鐘後或已有新查詢覆蓋時，回覆「上一輪搜尋結果已過期，請重新查詢」，不得猜測指向哪一筆。

收藏動作必須呼叫既有 Lifestyle capture pipeline，不直接改 registry。至少保留 `source_context: nearby_plus`、Google Maps／Place 識別資訊與店家基本資料；不保存當時個人 GPS 作為知識內容。

## 5. 功能需求

| ID | Requirement | 驗收要點 |
|---|---|---|
| FR-01 | 只允許 allowlist user ID 使用 Nearby | 非 allowlist 的相同文字照既有 capture 規則處理，不讀私人 registry。 |
| FR-02 | 接受文字 GPS 與 LINE location event | 合法座標更新 user-scoped last location 並確認；非法輸入不更新。 |
| FR-03 | 位置跨聊天室共用、僅記憶體保存 | 群組與 1:1 同一 user ID 得到同一位置；restart 後明確提示遺失。 |
| FR-04 | 解析查詢與缺欄位追問 | 缺 mode 或 time 時只追問缺的欄位，保留原 query。 |
| FR-05 | 預設只查 Lifestyle registry | 不含 `+` 時不得呼叫 Google Places；多類型可混合並由近到遠。 |
| FR-06 | 支援 Plus 分區與去重 | `+`／`＋` 等價；收藏與網路各最多 5 筆；Place ID 優先去重。 |
| FR-07 | 套用明確 filters | 營業、評分、類型、數量等明確條件嚴格執行；不得靜默放寬。 |
| FR-08 | 距離／時間可重現 | walk = 4.5 km/h、drive = 20 km/h；回覆標示整段「時間為粗估，非即時導航」。 |
| FR-09 | 0 筆提供最小放寬建議 | 嚴格結果仍為 0；最多計算並顯示 3 個替代（例如放寬時間／評分／營業條件），不自動套用。 |
| FR-10 | Plus 結果可收藏 | 明確收藏指令解析 index／名稱／全部；逾時或覆蓋結果拒絕寫入。 |
| FR-11 | 收藏走既有 pipeline | 產生 raw capture，後續由既有 ingest／enrichment 更新 wiki／registry。 |
| FR-12 | 查詢為讀取路徑 | 不在 query path 補 GPS、更新歇業狀態、改 registry 或改 wiki。 |

## 6. 非功能與安全要求

- 位置與結果 session 以 user ID 隔離；不接受使用者在訊息中冒充其他 ID。
- 不把 last location 寫入 vault、raw note、registry、log 或 LLM prompt。
- Google API key 只放環境變數；不得寫入 repo 或回覆。
- registry 缺失、格式錯誤或 Lifestyle vault 未設定時 fail closed，清楚回報無法查詢，不改查 Tech Vault。
- 結果需可重現：同一 registry snapshot、位置與條件產生相同排序；回覆時間戳可供排查。
- 既有 URL／文字 capture 行為不得因普通聊天或他人 Nearby-like 文字而改變。

## 7. 驗收情境

1. allowlist 使用者在 1:1 傳 GPS，再問「開車 20 分鐘內牛肉麵」；回已收藏結果，無 Google 呼叫。
2. 同一使用者在群組更新位置後於 1:1 查詢；沿用同一位置。
3. 非 allowlist 使用者傳相同查詢；不進 Nearby、不讀 Lifestyle registry。
4. 沒有位置、或 restart 後查詢；回明確遺失提示並要求 GPS。
5. 只說「附近有沒有牛肉麵」；追問走路／開車與分鐘數，收到回答後完成原查詢。
6. `牛肉麵+` 與 `牛肉麵＋`；兩者皆分列收藏／網路，各最多 5 筆，收藏優先去重。
7. 「現在營業、評分 4.5 以上」查無結果；回 0 筆與最多 3 個可計算的放寬選項。
8. 「收藏第 2 家」在 30 分鐘內成功送既有 capture；超過 30 分鐘或新查詢後拒絕。
9. registry 含海外 GPS；不因國家限制而拒絕，只按合法座標計算。
10. GPS 可疑（例如緯度少一位數）；先提醒，不自動修正或查詢。
