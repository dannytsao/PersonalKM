# Project Documentation Process

更新日期：2026-06-11

這份流程用來避免 PersonalKM repo 的根目錄再次累積大量已結案 `.md` 文件。

## 文件分級

### 1. Active Docs

仍需要維護、會被反覆查閱的文件。

例子：
- `README.md`
- `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md`
- `IMPROVEMENT-BACKLOG.md`
- `DOCS-INVENTORY.md`

規則：
- 必須在 `DOCS-INVENTORY.md` 登記。
- 文件開頭應有更新日期或明確狀態。
- 內容過時時，要直接更新，不要另開新的完成報告。

### 2. Changelog Entries

已完成、已決策、已部署、已結案的內容。

規則：
- 不再保留獨立 root `.md` 完成報告。
- 摘要整理進 `CHANGELOG.md`。
- 若需要保留操作細節，轉成 active docs 的一節，而不是留著一次性報告。

### 3. Backlog Items

尚未做、待改善、想法、下一階段。

規則：
- 統一放在 `IMPROVEMENT-BACKLOG.md`。
- 每個項目要有目標、建議做法、優先順序。
- 完成後移到 `CHANGELOG.md`，並從 backlog 移除或標記完成。

### 4. Generated Reports

由系統產生的報告，例如 ingestion、health check、decay report。

規則：
- 不放在 repo root。
- 放在 `outputs/` 底下。
- 若只是測試報告，完成後刪除或不要 commit。

### 5. Knowledge Notes

LINE Bot、worker 或 Obsidian 使用者產生的知識筆記。

規則：
- 放在 `raw/`、`wiki/`、`Archive/`、`Trash/`。
- 不列入 root 專案文件清理。
- 由 housekeeping / ingestion 流程管理。

## 新增文件流程

新增任何 root `.md` 前，先問：

1. 這是長期會被查的 active doc 嗎？
2. 如果只是完成報告，是否應寫進 `CHANGELOG.md`？
3. 如果只是待辦，是否應寫進 `IMPROVEMENT-BACKLOG.md`？
4. 如果是系統輸出，是否應放進 `outputs/`？
5. 是否需要同步更新 `DOCS-INVENTORY.md`？

只有第 1 類才應新增 root `.md`。

## 完成功能後的收尾流程

每次完成功能或修復後：

1. 更新 `CHANGELOG.md`。
2. 更新相關 active docs。
3. 若完成了 backlog 項目，更新 `IMPROVEMENT-BACKLOG.md`。
4. 更新 `DOCS-INVENTORY.md`，確認文件狀態。
5. 移除已被 changelog 取代的一次性 `.md`。
6. 執行 `git status --short --branch`，確認沒有多餘臨時文件。
7. commit + push。

## 每月文件盤點

每月做一次：

1. 列出 root `.md`。
2. 確認每個 root `.md` 都在 `DOCS-INVENTORY.md`。
3. 移除或合併完成報告。
4. 檢查 `README.md` 是否仍反映目前狀態。
5. 檢查 `IMPROVEMENT-BACKLOG.md` 的優先順序是否仍正確。

## 判斷是否可移除

可以移除：
- 標題含 Complete / Delivery / Summary / Roadmap 且工作已完成。
- 一次性 debug report。
- 舊部署 checklist，且 README 已有新的部署說明。
- 舊決策分析，且結論已進需求文件或 changelog。

不要移除：
- 目前使用者會操作的指引。
- 架構真相來源。
- active backlog。
- repo/agent 工作規則。
- raw/wiki/archive/trash 中的知識筆記。
