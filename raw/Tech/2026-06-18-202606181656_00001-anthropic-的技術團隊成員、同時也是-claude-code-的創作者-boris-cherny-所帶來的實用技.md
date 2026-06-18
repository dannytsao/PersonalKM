---
tags: [技術]
source: LINE
date: 2026-06-18
log_id: 202606181656_00001
url: https://www.youtube.com/watch?v=M8HuXu_bOco%E9%80%99%E9%83%A8%E5%BD%B1%E7%89%87%E6%98%AF%E7%94%B1
platform: line-message
content_type: pasted_text
extraction_status: ok
needs_review: false
needs_local_worker: false
worker_status: not_required
worker_type: none
worker_retry_count: 0
summary: Anthropic 的技術團隊成員 Boris Cherny 分享了 Claude Code 的實用技巧，強調它是一個完全代理型的 AI 助手，能夠協助建構功能、修復 Bug 並深入 codebase 問答。影片介紹了新手導入、進階程式碼編寫、自動化工作流、專案上下文管理及終端機快捷鍵等多項實用功能，並探討了為何選擇終端機 CLI 工具而非 IDE 外掛的原因。
status: unread
---

# Anthropic 的技術團隊成員、同時也是 **Claude Code 的創作者 Boris Cherny** 所帶來的實用技巧分享。 影片核心重點在於：**

## Log ID
202606181656_00001

## 摘要
Anthropic 的技術團隊成員 Boris Cherny 分享了 Claude Code 的實用技巧，強調它是一個完全代理型的 AI 助手，能夠協助建構功能、修復 Bug 並深入 codebase 問答。影片介紹了新手導入、進階程式碼編寫、自動化工作流、專案上下文管理及終端機快捷鍵等多項實用功能，並探討了為何選擇終端機 CLI 工具而非 IDE 外掛的原因。

## 重點
- Anthropic 的技術團隊成員 Boris Cherny 分享了 Claude Code 的實用技巧，強調它是一個完全代理型的 AI 助手，能夠協助建構功能、修復 Bug 並深入 codebase 問答。影片介紹了新手導入、進階程式碼編寫、自動化工作流、專案上下文管理及終端機快捷鍵等多項實用功能，並探討了為何選擇終端機 CLI 工具而非 IDE 外掛的原因。

## 原始貼文
https://www.youtube.com/watch?v=M8HuXu_bOco這部影片是由 Anthropic 的技術團隊成員、同時也是 **Claude Code 的創作者 Boris Cherny** 所帶來的實用技巧分享。

影片核心重點在於：**Claude Code 絕非傳統的單行程式碼補全工具，而是一個完全代理型（Agentic）的 AI 助手。** 它可以直接幫你建構完整功能、修復 Bug、深入 codebase 進行問答，並能完美融入你現有的任何終端機、IDE、遠端 SSH 或 tmux 工作流中。

以下為你整理 Boris 在演講中分享的核心技巧與支持原因：

---

### 一、 新手與團隊導入：從「Codebase Q&A」開始

* **結論：** 不要一開始就讓 Claude Code 幫你改寫大塊程式碼，先從詢問專案架構與歷史開始。
* **支持原因：**
* **大幅縮短新手登陸（Onboarding）時間：** Boris 指出，Anthropic 內部新進工程師第一天就會下載 Claude Code 來熟悉專案。以前技術 onboarding 需要 2 到 3 週，現在縮短到 **2 到 3 天** [[04:46](https://www.youtube.com/watch?v=M8HuXu_bOco&t=286)]。
* **無須漫長的索引（Indexing）等待：** 它是完全在本地運行的，沒有遠端資料庫，也不會拿你的程式碼去訓練模型，因此「不需要等待索引」，開箱即用 [[04:50](https://www.youtube.com/watch?v=M8HuXu_bOco&t=290)]。
* **深入歷史與問題：** 你可以直接叫它去翻閱 Git History 或 GitHub Issues [[05:53](https://www.youtube.com/watch?v=M8HuXu_bOco&t=353)]。例如可以問它：「為什麼這個 function 有 15 個參數？當初是誰、為了解決什麼 issue 加上去的？」它會自動讀取 git log 並給出總結 [[05:58](https://www.youtube.com/watch?v=M8HuXu_bOco&t=358)]。



### 二、 進階程式碼編寫與自動化工作流

* **結論：** 給予 AI 自我檢查的工具，並在動手前先要求它「規劃」。
* **支持原因：**
* **先思考、再動手（Brainstorm & Plan）：** 遇到大型功能（如 3000 行的 feature）時，直接叫它寫很容易做歪。好習慣是先對它說：`"Before you write code, make a plan."`（寫扣前先提計劃），等確認邏輯後再放行 [[08:55](https://www.youtube.com/watch?v=M8HuXu_bOco&t=535)]。
* **建立「閉環自我迭代」：** 當你把 Claude Code 結合單元測試（Unit Tests）、Puppeteer 網頁截圖或 iOS 模擬器時，它能自己看著錯誤訊息或畫面落差「重複修改 2 到 3 次」，直到產出完美的結果 [[11:05](https://www.youtube.com/watch?v=M8HuXu_bOco&t=665)]。
* **一鍵推進（Commit & Push）：** 你可以直接對它下達日常指令，例如叫它建立新分支、整理符合專案規範的 commit 訊息、推上去並在 GitHub 建立 Pull Request。它會自己去觀察專案先前的 git log 格式並完美複製，不需要特別設定 system prompt [[09:11](https://www.youtube.com/watch?v=M8HuXu_bOco&t=551)]。



### 三、 精準控制與管理專案上下文（Context）

* **結論：** 利用階層式的 `.claudemd` 檔案與全域配置，建立團隊共享的 AI 記憶。
* **支持原因：**
* **自動載入的記憶檔 `.claudemd`：** 在專案根目錄放這個檔案，每次啟動 session 就會自動讀入。適合放常用的 bash 指令、團隊風格指南（Style Guide）或架構決策 [[12:24](https://www.youtube.com/watch?v=M8HuXu_bOco&t=744)]。
* **階層式權限與配置（Enterprise Policies）：** 可以透過 `config.json` 進行全域或企業級的管理。例如：可以「自動允許（Auto-approve）」某些常用且安全的測試指令，避免每次都要手動確認 [[16:15](https://www.youtube.com/watch?v=M8HuXu_bOco&t=975)]；或者「封鎖（Block-list）」特定敏感的 URL，確保 AI 絕對不會去 fetch，維護程式碼安全 [[16:26](https://www.youtube.com/watch?v=M8HuXu_bOco&t=986)]。



### 四、 終端機不可不知的快捷鍵與秘訣

Boris 特別分享了幾個在終端機操作時非常實用、但通常不容易被發現的隱藏功能 [[18:31](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1111)]：

* **`Shift + Tab`（自動允許編輯）：** 切換到自動接受程式碼修改的模式，這樣就不用每一次修改檔案都要按 y 确认（但執行 bash 指令依然會跳提示，確保安全） [[18:55](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1135)]。
* **`#`（記住這件事）：** 如果發現 Claude 某個工具用錯了，按 `#` 然後告訴它正確做法，它會直接寫入記憶，接下來的 session 就會自動遵守 [[19:16](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1156)]。
* **`!`（下達本地 Bash）：** 想自己執行指令時，打 `!` 加上指令，執行結果會同時灌入當前的 Context 中，讓 Claude 下一輪對話能看見 [[19:31](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1171)]。
* **`Escape`（緊急停止）：** 隨時可以按 Esc 終止 Claude 的動作，不會損壞任何 session。你可以叫它停下來，微調某一行再讓它繼續 [[19:52](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1192)]。
* **`Ctrl + R`（檢視完整 Context）：** 顯示目前 Claude 視野裡看見的完整輸入與輸出，方便除錯 [[20:28](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1228)]。

---

### 💡 精彩問答亮點：為什麼是 CLI 而不是 IDE 外掛？

在 Q&A 階段，有觀眾問到「為什麼 Anthropic 選擇做終端機 CLI 工具，而不是像 Cursor 一樣做一個獨立的 IDE？」 [[25:33](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1533)]

Boris 給出了一個非常大膽且前瞻的反方觀點：

> 1. **最大公約數：** 內部工程師用的 IDE 五花八門（VS Code, Zed, Xcode, Vim, Emacs），終端機是所有人唯一的共同交集 [[25:41](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1541)]。
> 2. **IDE 未來可能會消失：** Anthropic 站在技術最前線，深知模型進步的速度有多恐怖。**「我們認為很有可能在今年（2026年）底之前，工程師就不再需要傳統的 IDE 了。」** 因此，現在過度投資在 UI 介面上，很快就會變成過時的無用功 [[26:01](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1561)]。
> 
> 

此外，他也提到 Claude Code 是完全支援多模態（Multimodal）的，你可以直接把設計稿、Mockup 圖片拖曳丟進終端機，搭配 Puppeteer，它就能幫你把畫面完全刻出來 [[24:50](https://www.youtube.com/watch?v=M8HuXu_bOco&t=1490)]。

## 內含連結
- https://www.youtube.com/watch?v=M8HuXu_bOco%E9%80%99%E9%83%A8%E5%BD%B1%E7%89%87%E6%98%AF%E7%94%B1
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=286
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=290
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=353
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=358
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=535
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=665
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=551
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=744
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=975
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=986
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1111
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1135
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1156
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1171
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1192
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1228
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1533
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1541
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1561
- https://www.youtube.com/watch?v=M8HuXu_bOco&t=1490

## 媒體
- 未擷取

## 擷取狀態
- 平台：line-message
- 類型：pasted_text
- 擷取狀態：ok
- 需要人工確認：否
