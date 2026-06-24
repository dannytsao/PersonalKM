---
epoch: 1782278097444
modelKey: "google/gemini-2.5-flash|openrouterai"
topic: "No NotebookLM Obsidian Integration"



tags:
  - copilot-conversation
---

**ai**: Based on the provided document, there is no information about linking Obsidian with Google NotebookLM. The document focuses on improvements for a personal knowledge management system using LINE Bot and Obsidian, with features like content cleaning, structured extraction, and YouTube summary upgrades. It also discusses creating canonical entity pages within Obsidian.

Therefore, I cannot tell you how to link Obsidian with Google NotebookLM based on this document.
[Timestamp: 2026/06/24 13:14:57]

**user**: How does obsidian work with google notebooklm
[Timestamp: 2026/06/24 13:16:25]

**ai**: I'm not familiar with a tool called "Google NotebookLM" that integrates with Obsidian. Could you provide more context or clarify what you mean by "Google NotebookLM"?
[Timestamp: 2026/06/24 13:16:26]

**user**: 依照 LLM 模型（如 GPT-4, Claude 3.5）分類，統計我目前收集了多少篇相關文章
[Timestamp: 2026/06/24 13:27:06]

**ai**: 很抱歉，我無法直接統計您收集了多少篇關於特定 LLM 模型（如 GPT-4, Claude 3.5）的文章。

我是一個語言模型，無法直接存取您的 Obsidian 筆記庫來進行分類和統計。

如果您想讓我幫助您統計，您需要提供給我相關的資訊，例如：

*   **您是如何標記這些文章的？** 例如，您是否使用了特定的標籤（tags）、資料夾結構，或者在筆記內容中明確提到了模型名稱？
*   **您希望我如何進行統計？** 例如，您希望我搜尋包含特定關鍵字（如 "GPT-4" 或 "Claude 3.5"）的筆記，還是根據筆記的屬性（properties）進行分類？

如果您能提供這些資訊，我可以嘗試根據您提供的內容來回答您的問題。
[Timestamp: 2026/06/24 13:27:09]

**user**: ```dataview
TABLE topic AS "主題", status AS "狀態", file.ctime AS "收集時間"
FROM "Wiki"
WHERE type = "youtube" AND status = "待閱讀"
SORT file.ctime DESC
```
[Timestamp: 2026/06/24 16:05:22]

**ai**: 這個 Dataview 查詢語法看起來是想從 "Wiki" 資料夾中，找出 `type` 為 "youtube" 且 `status` 為 "待閱讀" 的筆記，並顯示它們的 "主題"、"狀態" 和 "收集時間"，然後依照收集時間降序排列。

請問您是想讓我解釋這個查詢語法的功能，還是想讓我根據這個查詢語法來做些什麼？

如果您希望我能根據這個查詢語法來統計或分析您的筆記，我需要您提供這個查詢語法執行後的結果。因為我無法直接執行 Dataview 查詢來存取您的 Obsidian 筆記庫。
[Timestamp: 2026/06/24 16:05:25]

**user**: 這個查詢語法應該要在哪裡執行？
[Timestamp: 2026/06/24 16:06:31]

**ai**: 這個 Dataview 查詢語法應該在 **Obsidian 筆記** 中執行。

具體來說，你需要：

1.  **在 Obsidian 中創建一個新的筆記** (或打開一個現有的筆記)。
2.  **將這個查詢語法貼到筆記中。**
3.  **確保這個查詢語法被包裹在 Dataview 的代碼塊中。** 這通常是使用三個反引號 (```) 和 `dataview` 關鍵字來實現的。

所以，在你的 Obsidian 筆記中，它會看起來像這樣：

```
```dataview
TABLE topic AS "主題", status AS "狀態", file.ctime AS "收集時間"
FROM "Wiki"
WHERE type = "youtube" AND status = "待閱讀"
SORT file.ctime DESC
```
```

當你將這段代碼塊貼到 Obsidian 筆記中後，Dataview 插件會自動解析並執行它，然後在預覽模式下顯示查詢結果。
[Timestamp: 2026/06/24 16:06:34]