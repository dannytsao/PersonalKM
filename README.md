# Personal KM

LINE 群組連結整理到 Obsidian 的 MVP。LINE Bot 收到群組文字訊息後會偵測 URL，擷取網頁標題與內容，使用 LLM 產生 2-3 句摘要與自動分類，最後寫成 Markdown 並推送回這個 GitHub repo。新筆記會依分類放到 `Inbox/` 底下的子資料夾；`Archive/` 底下維持相同子資料夾，方便看完後歸檔。YouTube / `youtu.be` 連結會優先擷取字幕或逐字稿來摘要。

## Vault 結構

```text
Inbox/          不確定分類或待人工整理
├── Food/       美食待讀
├── General/    待分類待讀
├── Photography/ 攝影景點待讀
└── Tech/       技術待讀
Archive/        已讀或歸檔，子資料夾與 Inbox 相同
├── Food/
├── General/
├── Photography/
└── Tech/
Trash/          不要的項目，搬入後會改成非 Markdown 副檔名
├── Food/
├── General/
├── Photography/
└── Tech/
Templates/      筆記模板
Attachments/    圖片等附件
```

## 本機啟動

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn bot.app:app --reload --port 8000
```

健康檢查：

```bash
curl http://127.0.0.1:8000/health
```

## Render 部署

這個 repo 已包含 `render.yaml`。在 Render Dashboard 選擇 **New +** -> **Blueprint**，連接 `dannytsao/PersonalKM`，Render 會自動帶入：

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn bot.app:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Auto Deploy: false
```

`Auto Deploy` 預設關閉是刻意的：Bot 會把每個 LINE 連結寫成筆記並 push 回同一個 repo，如果開啟自動部署，每新增一篇筆記就會觸發一次 Render deploy。

## 必填環境變數

`LINE_CHANNEL_SECRET`：LINE Messaging API channel secret，用來驗證 webhook 簽章。

`LINE_CHANNEL_ACCESS_TOKEN`：保留給未來回覆 LINE 訊息使用；目前 MVP 不主動回覆訊息。

`OPENAI_API_KEY`：用於 AI 摘要與分類。若未設定，系統會用簡易規則產生 fallback 摘要與分類。

`VAULT_REPO_URL`：Bot 要 clone/push 的 Vault repo。Render 上建議使用只授權此 repo 的 GitHub fine-grained token，例如：

```text
https://你的GitHub帳號:你的Token@github.com/dannytsao/PersonalKM.git
```

這個值只能填在 Render Environment，不要 commit 到 repo。

`VAULT_PATH`：部署環境中的暫存 clone 路徑，預設為 `/tmp/personal-km-vault`。

`PYTHON_VERSION`：建議設為 `3.11.9`。

## LINE Webhook

部署後，在 LINE Developers 後台把 webhook URL 設為：

```text
https://你的部署網域/webhook/line
```

開啟 webhook 後，把 Bot 加入 LINE 群組。群組中有人貼 URL 時，Bot 會依分類在 `Inbox/Food/`、`Inbox/Tech/`、`Inbox/Photography/` 或 `Inbox/General/` 新增一篇筆記並推送 commit。

## Obsidian 設定

1. 將這個 repo clone 成 Obsidian Vault。
2. 安裝 Obsidian Git。
3. 設定自動 pull，每 10-15 分鐘一次。
4. 建議安裝 Dataview、Tag Wrangler、Templater。

## 目前支援的分類

| category | Obsidian tag |
| --- | --- |
| `photography` | `攝影景點` |
| `food` | `美食` |
| `tech` | `技術` |
| `general` | `待分類` |

## 自動歸檔規則

| category | target folder |
| --- | --- |
| `photography` | `Inbox/Photography/` |
| `food` | `Inbox/Food/` |
| `tech` | `Inbox/Tech/` |
| `general` | `Inbox/General/` |

所有筆記仍會保留 `status: unread`，方便之後人工閱讀與整理。看完後可手動移到 `Archive/` 底下相同分類資料夾，例如 `Inbox/Tech/` -> `Archive/Tech/`。

## 歸檔與丟棄筆記

在 Obsidian 看完筆記後，如果要歸檔，把 frontmatter 的狀態改成：

```yaml
status: archived
```

或：

```yaml
status: done
```

如果確定不要這篇筆記，把狀態改成：

```yaml
status: X
```

接著在 Vault 根目錄執行 dry-run，先確認會搬哪些檔案：

```bash
python scripts/archive_inbox.py --dry-run
```

確認無誤後執行搬移：

```bash
python scripts/archive_inbox.py
```

如果要搬移後直接 commit 並 push 到 GitHub：

```bash
python scripts/archive_inbox.py --commit
```

腳本只會搬 `Inbox/<分類>/` 裡符合狀態的 Markdown 檔：

| status | result |
| --- | --- |
| `done` | move to `Archive/<分類>/` |
| `archived` | move to `Archive/<分類>/` |
| `X` | move to `Trash/<分類>/` and rename to `.md.trash` |
| `unread` | stay in `Inbox/<分類>/` |

`status: X` 搬到 Trash 後會變成非 Markdown 副檔名，例如 `note.md.trash`，因此 Obsidian 不會把它當作一般筆記索引。

## YouTube 摘要

YouTube 連結不會直接抓影片頁 HTML。Bot 會先辨識 `youtu.be`、`youtube.com/watch`、`shorts`、`embed` 等 URL，接著嘗試取得影片標題與字幕/逐字稿，再交給 LLM 摘要。

如果影片沒有可用字幕、字幕端點拒絕存取，或影片本身限制擷取，Bot 仍會建立筆記並保留原文連結，但摘要會標註需要直接觀看影片。

## Universal Extractor v1

Bot 會優先擷取 OpenGraph / Twitter Card metadata，再使用正文文字摘要。對常見登入或反爬平台會標註擷取狀態，避免把平台樣板頁誤摘要成內容。

目前會特別辨識：

| platform | examples |
| --- | --- |
| `instagram` | `instagram.com/reel/...`, `instagram.com/p/...` |
| `tiktok` | `tiktok.com/@user/video/...`, `vm.tiktok.com/...` |
| `x` | `x.com/...`, `twitter.com/...` |
| `threads` | `threads.net/...` |
| `youtube` | `youtu.be/...`, `youtube.com/watch`, `shorts`, `embed` |

新筆記會增加：

```yaml
platform: instagram
extraction_status: blocked
needs_review: true
```

`extraction_status` 常見值：

| value | meaning |
| --- | --- |
| `ok` | 已取得可摘要內容 |
| `partial` | 已取得部分資訊，例如標題但無字幕 |
| `blocked` | 平台需要登入、反爬或只回傳樣板頁 |
| `error` | 一般網頁擷取失敗 |

Instagram、TikTok、X、Threads 若只取得登入頁或平台樣板內容，Bot 會建立一篇保留原文連結的筆記，摘要標註需直接開啟查看，避免產生「Instagram 是社群平台」這類不相關摘要。

## 下一步

- 加入 LINE 回覆訊息，告知已建立哪一篇筆記。
- 增加手動指定分類指令，例如 `#food https://...`。
- 加入定期摘要報告推送回 LINE。
