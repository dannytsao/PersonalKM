# AskDanny Phase 1：限定需求與檔案範圍

> 狀態：Phase 1 runtime 修正進行中；資料分享邊界與「北投早午餐」驗收案例已確認
> 日期：2026-09-06
> 本文件只定義 AskDanny／Lifestyle 範圍；runtime 修正限於第 6 節列出的 query 範圍。

## 1. 產品定義

AskDanny 是給約 10 人以內受邀親友使用的生活知識查詢介面。

它回答的是：

> Danny 已經整理、收藏或明確標記可分享的生活資訊。

它不是：

- 公開的全台旅遊搜尋引擎；
- Danny 的完整私人知識庫入口；
- 即時房況、價格、交通或訂房服務；
- DSS、Astro-bot 或 Tech Vault 的介面。

## 2. Phase 1 目標

提供唯讀、可追溯的 Lifestyle Q&A：

1. 親友用自然語言詢問美食、住宿、景點、咖啡廳、休閒等內容。
2. 系統只從已發布的 Lifestyle 資料中找答案。
3. 回覆列出少量相關候選、特色、地區與來源。
4. 資料不足時說明「目前 Danny 的資料沒有整理到」，不推論成「該地沒有這個選項」。
5. 不因 LLM 流暢生成而擴大資料範圍或補造缺漏欄位。
6. 首次回覆先列出 5 筆，讓使用者選擇繼續分頁、終止，或匯出目前已顯示資料。

## 3. 資料邊界

### 3.1 可讀資料

Phase 1 只可讀 Lifestyle Vault 的已發布資料，優先使用：

- `wiki/_registry/city-subject-store.json`：結構化地點資料；
- 已明確指定為可分享的 `wiki/entities/` 或 `wiki/concepts/` 頁面；
- 被結構化資料的 `source` 欄位指向、且已確認可分享的詳細頁面。

### 3.2 不可讀資料

Phase 1 不得讀取或送入 LLM：

- `raw/`；
- `Archive/raw/`；
- `resolved/`；
- `wiki/stubs/`；
- 未確認可分享的私人筆記；
- Tech Vault；
- DSS、Astro-bot 或其他外部專案資料。

### 3.3 資料語意

- 「Danny 已整理／收藏」不等於「Danny 親自使用過或強烈推薦」。
- 只有來源文字明確表達個人經驗或偏好時，才可如此描述。
- 缺少地址、GPS、評分、營業時間或特色時，省略該欄位，不補猜。
- `source`、`last_updated` 或頁面 `updated` 日期要保留，供回答標示來源與新鮮度。

### 3.4 發布閘門決策

Danny 已確認：**目前 registry 中的有效資料全部可供這 10 位親友查詢。**

因此 Phase 1 不新增 Lifestyle Vault 的 `shareability` 或 `publish_status` schema。AskDanny 可讀取 registry 中非 `removed` 的有效資料，但仍不得讀取 `raw/`、`Archive/raw/`、`resolved/`、`wiki/stubs/` 或未進入 registry 的私人筆記。

若未來出現需要分開公開與私人內容的情境，再另案討論資料標記與 schema 變更。

## 4. Phase 1 功能需求

### FR-01：受邀使用者

- 只有設定的 LINE user ID 可以查詢。
- Production 不得以空 allowlist 代表全開放。
- 未授權使用者不得讀取 Lifestyle Vault，也不得讓 LLM 收到查詢內容與資料上下文。

### FR-02：精準取資料

- 先依地區、類型、店名與特色等結構化欄位篩選。
- 只把相關候選與必要的詳細頁面送給 LLM。
- 不把整個大型 Markdown 彙整頁直接當成唯一 context。
- 同一個 registry snapshot 與同一個查詢，候選排序應可重現。

### FR-03：自然語言生活問答

至少支援：

- 地區＋類型，例如「嘉義阿里山有什麼住宿？」；
- 地區＋廣義美食，例如「新北市有什麼美食？」；廣義美食涵蓋 registry 的餐廳、小吃、早午餐、咖啡廳、甜點與酒吧主題；
- 地區＋需求，例如「北海岸適合看海又能吃飯的地方？」；
- 店名或主題查詢；
- 少量候選比較。
- 「再看幾筆」分頁：使用者自行指定要再看的筆數。

旅遊區或其他可能跨越多個行政區的地名，由 LLM 先判斷查詢意圖；若需要擴大地區範圍，先列出將納入的行政區請使用者確認，確認後才執行 registry 篩選。

查詢先使用 AskDanny 專用的記憶體倒排索引，從 registry 的主題、店名、地址與特色欄位找出候選；索引是唯讀且可重建，不寫回 Lifestyle Vault。LLM 僅處理索引無法安全判斷的語意。

若地區或類型不足以產生可靠結果，可以追問一個最關鍵的澄清問題；Phase 1 只保存短期的查詢分頁狀態，不建立旅遊規劃狀態。

### FR-04：回答格式

回覆使用 LINE 純文字，最多列出 3–5 個相關候選。簡單查詢應優先使用 deterministic renderer；LLM 可先負責自然語言意圖理解與地區範圍正規化，但不選擇店家或改寫資料。

回覆不得包含：

- `<think>`、`<analysis>` 或任何模型內部推理文字；
- 「我先檢視」「接下來搜尋」「我發現」等內部工作過程；
- 與問題無關的候選清單；
- 未被資料支持的距離、比較或推論；
- 長篇背景說明或重複資料。

Registry 命中時，每筆依下列順序使用 LINE 純文字顯示；欄位缺漏就省略，不補猜：

- 主題；
- 店名；若 registry 有已查證的 Google Maps URL，或有地址／GPS 可產生標準 Google Maps 連結，於店名行附上可點擊的 Google 地圖連結；
- 地址；
- 電話；
- 預約連結；
- Google 星等（有評論數時一併顯示）；
- 特色說明；
- GPS：使用可點擊的 Google Maps 搜尋連結。

欄位缺漏就省略，不補猜；沒有 GPS 時不得自行從地址推算座標。來源名稱仍由訊息尾端統一標示。

首批 5 筆後提供三個選項：

1. 再看幾筆：使用者回覆「再看 N 筆」，只顯示同一次查詢尚未顯示的資料；
2. 終止輸出：清除這次查詢狀態；
3. 匯出到 Google Sheet：只匯出目前已顯示的資料，使用者先以自己的 Google 帳號完成一次性 OAuth 授權，匯出完成後終止這次查詢。AskDanny 不保存 Google email、帳號識別、access token 或 refresh token。

不得輸出原始檔案路徑、raw 內容、frontmatter 或私人筆記全文。

### FR-05：資料不足與不確定性

- 沒有符合資料時，回覆「目前 Danny 的 Lifestyle Vault 沒有整理到相關資料」。
- 不得說「該地沒有住宿／餐廳」等全域性結論。
- 來源互相矛盾或資料過舊時，要明確標示限制。
- 不提供未查證的即時房況、價格、營業狀態、交通時間或可訂保證。

### FR-06：LLM 邊界

- LLM 可將自然語言查詢轉成結構化主題與地區範圍，必要時提出區域涵蓋確認；實際候選集合仍由 registry deterministic filter 產生。
- LLM 不負責決定資料是否屬於 Lifestyle、是否可分享或是否為最新真相。
- LLM 失敗時回傳可理解的暫時無法回答訊息，不使用未授權的資料或靜默捏造答案。

### FR-07：簡潔與輸出安全

- 一般地區／類型查詢以 1–5 筆候選為限；若只有一筆，直接回答該筆，不列出其他地區的掃描結果。
- 回覆只保留親友需要採取下一步的資訊；不顯示候選搜尋過程、模型思考或 prompt 指令。
- 對 LLM 回覆執行輸出閘門：若偵測到 `<think>`、`<analysis>`、工具痕跡或不符合純文字格式，必須移除或改走安全的 deterministic response，不得原樣送至 LINE。
- 回覆來源只列實際使用的來源，不列出未被採用的頁面作為裝飾。

## 5. 明確不在 Phase 1

- 完整旅遊行程安排；
- 即時房況、價格、訂房、付款；
- 即時交通、路況、導航或真實 ETA；
- Google Places 或其他外部搜尋；
- Nearby GPS 查詢；
- 親友寫回、收藏或修改 Lifestyle Vault；
- 語音、圖片理解或 Flex Message；
- 修改 Capture、Resolve、Ingest、Propagate 共用流程；
- 修改 Tech Vault 的任何輸出；
- 修改 DSS、Astro-bot 或其部署。

## 6. 允許的檔案範圍

### 6.1 PersonalKM 可修改

實作時只允許觸及以下範圍：

- `src/personalkm/query/line_bot.py`：LINE webhook adapter 與 AskDanny 回覆組裝；
- `src/personalkm/query/search_index.py`：AskDanny 唯讀、可重建的查詢索引；
- `src/personalkm/query/` 下新增的 AskDanny 專用唯讀查詢模組；
- `tests/` 下的 AskDanny fixture、unit tests 與 contract tests；
- 必要時新增 AskDanny 專用設定檔，但不得使用或修改 `config/models.yaml`。

### 6.2 只讀、不修改

- `/Users/dannytsao/Documents/PersonalKM/Personalkm-lifestyle-vault/`；
- Lifestyle Vault 的 registry、wiki、raw、resolved 與 Archive/raw；
- 任何 private token、LINE secret、GitHub credential。

### 6.3 明確禁止修改

- `src/personalkm/capture/`；
- `src/personalkm/resolve/`；
- `src/personalkm/ingest/`；
- `src/personalkm/propagate/`；
- `src/personalkm/llm/`；
- `config/models.yaml`；
- Tech Vault 與其資料處理流程；
- `render.yaml` 中既有 Tech／Capture service 設定；
- DSS、Astro-bot 或其他 repository。

## 7. 驗收案例

1. 已授權親友查詢「嘉義阿里山有什麼住宿？」時，先確認是否包含相關鄉鎮；確認後只回傳已發布資料，並保留資料缺漏說明。
2. 查詢沒有資料的地區時，說明 Vault 沒有整理到，不宣稱全網不存在。
3. Registry 有地址但沒有 GPS 時，可以顯示地址，但不自行產生座標。
4. 來源頁面含有指令文字時，該文字只被視為資料，不得改變系統範圍或觸發外部動作。
5. 未授權 user ID 查詢時，不讀取 Lifestyle Vault，也不呼叫 LLM。
6. Tech、DSS 或 Astro-bot 相關問題不會讀取其他專案，並清楚回覆目前 AskDanny 範圍不包含該內容。
7. 同一份 registry snapshot 的相同問題，產生相同候選集合與排序。
8. LLM 或 Lifestyle Vault 暫時不可用時，不回傳猜測內容，也不把錯誤當成「沒有資料」。
9. 已授權親友查詢「北投有什麼早午餐？」時，回覆只列出符合北投＋早午餐條件的候選；不得出現其他行政區店家、候選掃描過程、`<think>`／`<analysis>` 或未被資料支持的推論。

## 8. 越界處理

若實作需要修改任何共用模組、雙 Vault 分流、共用 schema、LLM routing、Tech 排程或部署設定，立即停止該變更，列出受影響的模組與結果，再由 Danny 明確決定是否擴大 scope。

本文件的範圍與驗收案例是 Phase 1 runtime 修正的依據；任何超出第 6 節檔案範圍的變更仍須先停下討論。
