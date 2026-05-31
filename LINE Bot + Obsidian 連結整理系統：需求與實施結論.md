# LINE Bot + Obsidian 連結整理系統：需求與實施結論

## 一、專案目標

在 LINE 群組中自動偵測分享的連結，透過 AI 擷取摘要並自動分類，最終同步至 Obsidian 進行知識管理。

---

## 二、核心需求

| 項目 | 說明 |
|:-----|:-----|
| **連結來源** | LINE 群組中的訊息連結 |
| **分類類別** | 攝影景點、美食、技術（未來可擴充） |
| **分類方式** | Auto-tag（由 LLM 自動判斷） |
| **整理內容** | 網頁標題、AI 摘要（2-3 句）、原文連結、日期 |
| **同步方式** | Git（LINE Bot → GitHub 私有 repo → Obsidian Git 插件） |
| **使用裝置** | 電腦（Obsidian 主力）+ 手機（瀏覽） |

---

## 三、選定方案

**方案二：LINE Bot + Obsidian Git**

選擇原因：
- 不需電腦一直開著
- 資料有版本控制
- 部署後幾乎免維護
- 穩定性與功能性平衡最佳

---

## 四、系統架構

```
LINE 群組訊息
    ↓
LINE Bot（雲端部署）
    ↓ 偵測 URL
網頁擷取（標題 + 內容）
    ↓
LLM 處理（摘要 + Auto-tag 分類）
    ↓
產生 Markdown 筆記
    ↓
推送至 GitHub 私有 Repo（Inbox/ 資料夾）
    ↓
Obsidian Git 插件定時 Pull
    ↓
筆記出現在 Obsidian 中
```

---

## 五、Obsidian Vault 結構

```
MyVault/
├── Inbox/          ← LINE Bot 自動寫入暫存區
├── Photography/    ← 攝影景點（歸檔用）
├── Food/           ← 美食（歸檔用）
├── Tech/           ← 技術（歸檔用）
├── Archive/        ← 已讀/歸檔
├── Templates/      ← 筆記模板
└── Attachments/    ← 圖片等附件
```

---

## 六、筆記格式模板

```markdown
---
tags: [自動分類標籤]
source: LINE
date: YYYY-MM-DD
url: https://example.com
summary: AI 自動摘要
status: unread
---

# 網頁標題

## 摘要
AI 自動生成的 2-3 句摘要

## 原文連結
https://example.com
```

---

## 七、所需工具與服務

| 類別 | 工具/服務 | 用途 |
|:-----|:----------|:-----|
| 筆記軟體 | Obsidian（免費） | 知識管理主體 |
| Obsidian 插件 | Obsidian Git | 同步 Git repo |
| Obsidian 插件 | Dataview | 動態查詢列表 |
| Obsidian 插件 | Tag Wrangler | 管理標籤 |
| Obsidian 插件 | Templater | 筆記模板 |
| 版本控制 | GitHub 私有 Repo | 存放筆記檔案 |
| 機器人 | LINE Messaging API | 群組訊息接收 |
| 雲端部署 | Railway / Render / VPS | LINE Bot 運行環境 |
| AI 模型 | OpenAI API 或其他 LLM | 摘要生成 + 自動分類 |

---

## 八、實施步驟

### 階段一：基礎建設（週末）
1. 安裝 Obsidian，建立 Vault 及資料夾結構
2. 建立 GitHub 私有 Repo
3. 安裝 Obsidian Git 插件，設定自動 Pull（每 10-15 分鐘）
4. 安裝 Dataview、Tag Wrangler、Templater 插件

### 階段二：LINE Bot 開發
1. 申請 LINE Messaging API Channel
2. 開發 Bot 程式（Python/Node.js）
3. 實作連結偵測 + 網頁擷取
4. 串接 LLM 做摘要與 auto-tag
5. 實作 Markdown 產生 + Git push

### 階段三：部署與測試
1. 部署 Bot 到雲端平台
2. 將 Bot 加入 LINE 群組
3. 測試完整流程
4. 調整分類準確度

---

## 九、預估時程

| 階段 | 預估時間 |
|:-----|:---------|
| 階段一：基礎建設 | 1-2 小時 |
| 階段二：LINE Bot 開發 | 4-8 小時 |
| 階段三：部署與測試 | 2-3 小時 |
| **合計** | **約 1-2 個週末** |

---

## 十、未來擴充方向

- 增加更多分類標籤
- 支援圖片/影片連結的處理
- 加入 LINE Bot 互動指令（手動指定分類、搜尋筆記等）
- 整合其他來源（Telegram、Email、瀏覽器書籤等）
- 定期摘要報告推送回 LINE
