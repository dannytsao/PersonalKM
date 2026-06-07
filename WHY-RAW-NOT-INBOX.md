# 為什麼需要 `raw/` 而不是用 `Inbox/`？

**問題:** 目前有 `Inbox/` 和新增的 `raw/`，為什麼不能讓 `Inbox/` 扮演 `raw/` 的角色？

---

## 📊 當前 Inbox 結構

```
Inbox/
├── General/        ← 已分類的一般內容
├── Tech/          ← 已分類的技術內容
├── Food/          ← 已分類的食物內容
├── Photography/   ← 已分類的攝影內容
└── [已分類的文件]
```

**問題:** Inbox 已經有**預定義的分類結構**！

---

## 🎯 為什麼 Inbox 不能是 raw？

### 1️⃣ **Inbox 已經是「預分類」的**

| 特點 | Inbox | raw |
|------|-------|-----|
| 結構 | 有子資料夾 (General, Tech, Food, Photography) | 平面結構 |
| 目的 | 已按用途分類 | **未經分類** |
| 分類方式 | 手動分類 (General/Tech/Food/Photography) | AI 自動分類 (entities/concepts) |
| 靈活性 | 固定的四類 | 動態的無限類別 |

### 2️⃣ **分類系統衝突**

**Inbox 的舊分類系統:**
```
Inbox/
├── General/
├── Tech/
├── Food/
└── Photography/
```

**新的 Karpathy 框架:**
```
raw/           ← 所有新抓取都來這
  ↓ (每週日自動組織)
wiki/
├── entities/  ← Docker, Kubernetes 等具體工具
├── concepts/  ← 知識概念
└── sources/   ← 參考資源
```

**為什麼衝突？**
- Inbox 是**人工預定義**的 4 個類別
- raw→wiki 是 **AI 自動提取**的無限實體
- 一個文件在 Inbox/Tech 中，但應該在 wiki/entities/kubernetes
- 無法共存！

### 3️⃣ **實際例子**

假設您傳送一個 Karpathy 影片連結：

**如果用 Inbox:**
```
Inbox/Tech/karpathy-video.md
  ├── 問題：放在 Tech 下面
  ├── 但 AI 想標記為：entities/claude, entities/knowledge-graph
  ├── 衝突！怎樣移動？
  └── 手動才能重新組織
```

**用 raw:**
```
raw/karpathy-video.md
  ↓ (週日自動)
wiki/entities/claude.md
wiki/entities/knowledge-graph.md
  ↓ (自動同步到 Obsidian)
完成！無衝突
```

### 4️⃣ **Inbox 的角色是「過渡」**

```
時間線：
2026-06-06 之前：
  LINE → Inbox/ (分類式存儲)

2026-06-07 之後（現在）：
  LINE → raw/ (無分類的臨時倉庫) → wiki/ (自動組織)
  
Inbox/ 變成「歷史檔案」
```

---

## 💻 技術原因

### bot/app.py 的邏輯

**舊版 (之前):**
```python
# 保存到 Inbox，需要指定子資料夾
note_path = write_note(vault_path, settings.inbox_dir, note)
# settings.inbox_dir = "Inbox"
# 實際存: Inbox/General/ 或 Inbox/Tech/
```

**新版 (現在):**
```python
# 保存到 raw，無分類
note_path = write_note(vault_path, "raw", note)
# 實際存: raw/

# 每週日自動組織
ingest_raw_to_wiki()
# 根據內容分析，移動到 wiki/entities/ 或 wiki/concepts/
```

**為什麼不能混用？**
1. Inbox 需要指定子資料夾 (General/Tech/Food/Photography)
2. raw 必須是平面結構（無子資料夾）
3. 混用會造成：
   - 邏輯混亂
   - 自動化衝突
   - 無法正確分類

---

## 🔄 實際工作流程對比

### ❌ 如果用 Inbox 當 raw

```
問題 1: 指定分類不明確
LINE → Inbox/General/?  (放哪個子資料夾？)
  → 自動化無法決定

問題 2: 週日自動化無法工作
ingest_raw_to_wiki()
  → Inbox 已經分類了，不好再移動
  → wiki/entities/kubernetes 和 Inbox/Tech/ 重複

問題 3: 歷史數據混亂
Inbox 同時包含：
  - 舊的已分類文件
  - 新的未分類文件
  → 不知道哪個應該移動到 wiki
```

### ✅ 用 raw（現在的做法）

```
步驟 1: 無縫抓取
LINE → raw/karpathy-video.md
  ✓ 無需指定子資料夾
  ✓ 所有新文件都在這

步驟 2: 自動分類清晰
週日 9 AM: ingest_raw_to_wiki()
  raw/karpathy-video.md
  → 分析內容
  → 移動到 wiki/entities/claude.md
  ✓ 清晰的單向流動

步驟 3: 歷史保護
Inbox/ 保持為「歷史檔案」
  ✓ 不再改變
  ✓ 可隨時參考
```

---

## 📐 三層架構設計

Karpathy 框架的核心就是**三個清晰的層級**：

```
raw/          ← 第 1 層：未組織的大腦傾倒
  ↓ (自動化)
wiki/         ← 第 2 層：已組織的知識
  ↓ (查詢)
outputs/      ← 第 3 層：衍生的報告和分析
```

**如果 raw = Inbox (已分類):**
```
Inbox/        ← 混亂的已分類 + 未分類混合
  ↓ (難以自動化)
??? 不知道應該怎樣處理
```

**破壞了整個框架！**

---

## 🎯 Inbox 的新角色

現在 Inbox 應該被視為：
- ✅ **歷史檔案** - 保留之前的舊文件
- ✅ **備份** - 如果需要回查舊的分類
- ❌ **不是 raw** - 不再接收新文件

```
Inbox/
├── 2026-06-06 之前的文件 (保留)
├── 用於查詢歷史
└── 不再接收新文件
```

---

## 📊 總結對比

| 面向 | Inbox | raw |
|------|-------|-----|
| **角色** | 歷史檔案 | 新的臨時倉庫 |
| **結構** | 預定義子資料夾 | 平面結構 |
| **分類方式** | 人工 (General/Tech/Food) | AI 自動 (entities/concepts) |
| **自動化** | 困難 | 簡單 |
| **容納新文件** | ❌ 不再接收 | ✅ 所有新文件來這 |
| **移動規則** | 手動 | 自動（週日） |
| **同步到 wiki** | ❌ | ✅ |
| **框架兼容性** | ❌ 舊框架 | ✅ 新框架 |

---

## 💡 類比

想像您的大腦：

**Inbox = 舊的抽屜系統**
```
抽屜 1: General (一般)
抽屜 2: Tech (技術)
抽屜 3: Food (食物)
抽屜 4: Photography (攝影)
→ 固定的 4 個抽屜
```

**raw = 新的工作台**
```
所有新的想法放上來
↓
智能助理分析
↓
自動放到合適的位置
```

**不能把工作台當成抽屜系統！**

---

## ✅ 最佳實踐

**現在的設置是正確的：**

```
old system:     Inbox/ (歷史)
new system:     raw/ → wiki/
                     → entities/
                     → concepts/
                     → outputs/
```

- ✅ 保持向後相容
- ✅ 新舊系統不衝突
- ✅ 自動化流程清晰
- ✅ 符合 Karpathy 框架

---

## 🎊 結論

**為什麼不用 Inbox？**

1. **Inbox 已預分類** - 有固定子資料夾
2. **raw 必須無分類** - 才能自動組織
3. **框架衝突** - 舊分類系統 vs 新自動化系統
4. **自動化需求** - 需要平面結構才能工作
5. **設計原則** - 三層架構需要明確分離

**結果：** 需要 `raw/` 作為新的臨時倉庫，`Inbox/` 保留為歷史。

---

**這就是為什麼 raw 不能少！** ✨
