# Antigravity CLI（agy）快速上手 | Antigravity 速速上手

## Log ID
202606270549_00001

## 摘要
Antigravity CLI（agy）是一款由Google Antigravity開發的終端機AI代理工具，支援Windows、macOS及Linux平台，無需Node或Python環境即可安裝使用。本文詳細介紹了agy的安裝方法、基本指令用法、子指令功能以及從Gemini CLI或Claude的遷移方式，並提供官方文件與教學連結。

## 重點
- Antigravity CLI（agy）是一款由Google Antigravity開發的終端機AI代理工具，支援Windows、macOS及Linux平台，無需Node或Python環境即可安裝使用。本文詳細介紹了agy的安裝方法、基本指令用法、子指令功能以及從Gemini CLI或Claude的遷移方式，並提供官方文件與教學連結。

## 原始內容
Antigravity CLI（agy）快速上手 | Antigravity 速速上手 ← 回課程首頁 ⌨️ Antigravity CLI（agy）快速上手 Antigravity CLI（ agy ）快速上手筆記 本筆記指令皆以本機 agy --help 實測為準（非網路文章），可放心照抄。 撰寫：阿亮老師工作流 ｜ 對應版本： agy 1.0.12 一、它是什麼 agy 是 Google Antigravity 的終端機 AI Agent CLI，於 2026/6/18 取代 Gemini CLI 。 單一編譯執行檔， 不需 Node / Python ，一行指令安裝。 跨平台：Windows / macOS / Linux。 本機現況（已安裝）： - 路徑： C:\Users\user\AppData\Local\agy\bin\agy.exe - 版本： 1.0.12 - 驗證： agy --version 二、安裝（重裝或別台機器用） Windows · PowerShell（建議） irm https://antigravity.google/cli/install.ps1 | iex agy --version Windows · CMD curl -fsSL https://antigravity.google/cli/install.cmd -o install.cmd && install.cmd && del install.cmd macOS / Linux curl -fsSL https://antigravity.google/cli/install.sh | bash export PATH="$HOME/.local/bin:$PATH" agy --version 三、基本用法 動作 指令 啟動互動式對話（TUI） agy 單次提問、印出結果就結束 agy -p "幫我解釋這段程式" 帶初始提示但繼續對話 agy -i "先看看這個專案" 接續上一段對話 agy -c 用 ID 恢復某段對話 agy --conversation <ID> 指定模型 agy --model <模型名> 把資料夾加入工作區（可重複） agy --add-dir ./src --add-dir ./docs 開新專案 session agy --new-project 指定專案 agy --project <專案ID> 在受限終端沙箱中執行 agy --sandbox 自動核可所有工具權限（⚠️ 危險） agy --dangerously-skip-permissions ⚠️ --dangerously-skip-permissions 會讓 Agent 不問你就執行所有工具/指令，僅在你信任的隔離環境用。 四、子指令 子指令 用途 agy models 列出可用模型 agy plugin （別名 plugins ） 管理外掛（見下節） agy update 更新 CLI 到最新版 agy changelog 看更新日誌 / 版本說明 agy install 設定環境路徑與 shell 設定 agy help 看各子指令說明 五、從 Gemini CLI（或 Claude）遷移 ★ agy 內建匯入，把舊的外掛/設定直接接過來： # 從 Gemini CLI 匯入 agy plugin import gemini # （也支援從 Claude 匯入） agy plugin import claude # 確認匯入結果 agy plugin list 外掛管理其他常用指令： agy plugin install <name@marketplace> # 安裝外掛 agy plugin enable <name> # 啟用 agy plugin disable <name> # 停用 agy plugin uninstall <name> # 移除 agy plugin validate <path> # 驗證外掛 📌 注意：網路上有文章寫 agy inspect 、 agy config --edit —— 這兩個指令不存在 ，請以本筆記為準。 六、更新與維護 agy update # 更新到最新版 agy --version # 確認版本 agy changelog # 看這版改了什麼 七、官方連結 安裝文件：https://antigravity.google/docs/cli-install 快速上手：https://antigravity.google/docs/cli-getting-started GitHub：https://github.com/google-antigravity/antigravity-cli 官方 Codelab 教學：https://codelabs.developers.google.com/antigravity-cli-hands-on 📘 《Google Antigravity 速速上手》延伸番外篇 · 阿亮老師 | YouTube

## 內含連結
- https://chatgpt3a01.github.io/Antigravity-Pandoc-AI/agy-cli.html
- https://antigravity.google/cli/install.ps1
- https://antigravity.google/cli/install.cmd
- https://antigravity.google/cli/install.sh
- https://antigravity.google/docs/cli-install
- https://antigravity.google/docs/cli-getting-started
- https://github.com/google-antigravity/antigravity-cli
- https://codelabs.developers.google.com/antigravity-cli-hands-on

## 媒體
- 未擷取

## 擷取狀態
- 平台：web
- 類型：webpage
- 擷取狀態：ok
- 需要人工確認：否

## 原文連結
https://chatgpt3a01.github.io/Antigravity-Pandoc-AI/agy-cli.html
