# Personal KM

LINE 群組連結整理到 Obsidian 的 MVP。LINE Bot 收到群組文字訊息後會偵測 URL，擷取網頁標題與內容，使用 LLM 產生 2-3 句摘要與自動分類，最後寫成 Markdown 並推送回這個 GitHub repo。分類明確時會自動放到對應資料夾，不確定才留在 `Inbox/`。

## Vault 結構

```text
Inbox/          不確定分類或待人工整理
Photography/    攝影景點自動歸檔
Food/           美食自動歸檔
Tech/           技術自動歸檔
Archive/        已讀或歸檔
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

開啟 webhook 後，把 Bot 加入 LINE 群組。群組中有人貼 URL 時，Bot 會依分類在 `Food/`、`Tech/`、`Photography/` 或 `Inbox/` 新增一篇筆記並推送 commit。

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
| `photography` | `Photography/` |
| `food` | `Food/` |
| `tech` | `Tech/` |
| `general` | `Inbox/` |

所有筆記仍會保留 `status: unread`，方便之後人工閱讀與整理。

## 下一步

- 加入 LINE 回覆訊息，告知已建立哪一篇筆記。
- 增加手動指定分類指令，例如 `#food https://...`。
- 加入定期摘要報告推送回 LINE。
