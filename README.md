# Personal KM

LINE 群組連結整理到 Obsidian 的 MVP。LINE Bot 收到群組文字訊息後會偵測 URL，擷取網頁標題與內容，使用 LLM 產生 2-3 句摘要與自動分類，最後寫成 Markdown 到 `Inbox/` 並推送回這個 GitHub repo。

## Vault 結構

```text
Inbox/          LINE Bot 自動寫入暫存區
Photography/    攝影景點歸檔
Food/           美食歸檔
Tech/           技術歸檔
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

## 必填環境變數

`LINE_CHANNEL_SECRET`：LINE Messaging API channel secret，用來驗證 webhook 簽章。

`LINE_CHANNEL_ACCESS_TOKEN`：保留給未來回覆 LINE 訊息使用；目前 MVP 不主動回覆訊息。

`OPENAI_API_KEY`：用於 AI 摘要與分類。若未設定，系統會用簡易規則產生 fallback 摘要與分類。

`VAULT_REPO_URL`：Bot 要 clone/push 的 Vault repo。部署到 Railway/Render 時，建議使用帶有權限的 HTTPS URL 或設定平台支援的 SSH deploy key。

`VAULT_PATH`：部署環境中的暫存 clone 路徑，預設為 `/tmp/personal-km-vault`。

## LINE Webhook

部署後，在 LINE Developers 後台把 webhook URL 設為：

```text
https://你的部署網域/webhook/line
```

開啟 webhook 後，把 Bot 加入 LINE 群組。群組中有人貼 URL 時，Bot 會在 `Inbox/` 新增一篇筆記並推送 commit。

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

## 下一步

- 加入 LINE 回覆訊息，告知已建立哪一篇筆記。
- 增加手動指定分類指令，例如 `#food https://...`。
- 將已讀筆記自動或半自動移到對應資料夾。
- 加入定期摘要報告推送回 LINE。
