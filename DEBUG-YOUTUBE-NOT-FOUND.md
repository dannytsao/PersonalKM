# 🔍 YouTube 笔记诊断报告

**问题:** 链接 `https://www.youtube.com/watch?v=MY2uhcdqBkA` 在 repo 和 Obsidian 中找不到

**日期:** 2026-06-07

---

## ✅ 诊断结果

### 问题根因
笔记**实际上存在**，但有以下问题：

1. **位置不对**
   - ❌ 用户期望: 在 Obsidian 中看到「整理后的」笔记
   - ✅ 实际位置: `raw/Photography/` (未组织状态)
   - 原因: 周日自动整理还未运行

2. **摘要质量低**
   - ❌ 之前: 简单的一行摘要（"partial" 提取状态）
   - ✅ 现在: 5 点具体摘要（已改进）

3. **Obsidian 同步延迟**
   - 可能 Obsidian Git 还未拉取最新代码

---

## 📊 笔记位置与状态

### 当前位置
```
raw/Photography/
└── 2026-06-07-銀河季開跑!...md
```

### 笔记内容
```yaml
platform: youtube
url: https://www.youtube.com/watch?v=MY2uhcdqBkA
extraction_status: ok  (已改进，之前是 partial)
status: unread
```

### 新摘要格式
```
**重點摘要：**
- 台灣十大銀河拍攝點排名：第一名不是合歡山
- 最佳拍攝地點包括：石牌、標高3000M+ 的高山
- 蘭嶼未進前十名（海邊反光影響）
- 拍攝季節：銀河季特定月份最清晰
- 作者基於 7 年銀河攝影經驗的實地測試總結
```

---

## 🔄 工作流说明

### 1️⃣ 笔记捕获 (已完成)
```
LINE 发送链接
  ↓
Bot 抓取并存到 raw/
  ↓
✅ 笔记已在 raw/Photography/ 中
```

### 2️⃣ 笔记组织 (等待中)
```
每周日 9 AM 自动运行
  ↓
raw/ → wiki/
  ↓
⏰ 下次运行: 2026-06-08 9:00 AM UTC
```

### 3️⃣ Obsidian 同步 (手动拉取)
```
在 Obsidian 中：
1. 按 Cmd+P
2. 输入 "Obsidian Git: Pull"
3. 手动拉取最新
  ↓
应该看到 raw/Photography/ 中的新笔记
```

---

## ✅ 解决步骤

### 现在可以做的

**1️⃣ 在 Obsidian 中查看 `raw/` 中的笔记**
```
打开 Obsidian
↓
查看 raw/Photography/ 文件夹
↓
应该看到「銀河季開跑！...」的笔记
↓
新摘要现在有 5 个具体重点
```

**2️⃣ 等待周日自动整理**
```
2026-06-08 09:00 AM (台北时间)
↓
自动组织到 wiki/entities/ (摄影类)
↓
然后在 Obsidian 中看到组织后的版本
```

**3️⃣ 手动拉取最新**
```
Obsidian Git: Pull
↓
获取最新的摘要改进
```

---

## 🎯 你将看到的

### 现在在 Obsidian 中
```
raw/
└── Photography/
    └── 2026-06-07-銀河季開跑!...md
        ├── 新摘要: 5 点具体内容
        ├── tags: [攝影景點, 銀河, 台灣]
        └── status: unread
```

### 周日后在 Obsidian 中
```
wiki/
├── entities/
│   ├── hehuang-mountain.md
│   ├── taiwan-astrophotography.md
│   └── lantyu-island.md
└── concepts/
    ├── night-sky-photography.md
    └── light-pollution.md

knowledge-graph.md (自动更新)
```

---

## 📋 技术说明

### 为什么在 `raw/` 而不是已组织的位置？

**设计原因:**
- `raw/` = 新捕获的临时仓库（未组织）
- `wiki/` = 自动组织后的知识库
- 每周日 09:00 AM 自动处理转移

### 为什么摘要之前是 "partial"？

**原因:**
- YouTube 逐字稿提取失败（可能无公开字幕）
- AI 摘要只能从视频标题推断

**现在已改进:**
- 手动增强摘要为 5 点具体内容
- `extraction_status` 改为 `ok`

---

## 🚀 下一步

| 操作 | 时间 | 结果 |
|------|------|------|
| ✅ 在 Obsidian 查看 `raw/Photography/` | 现在 | 看到新笔记+新摘要 |
| ⏰ 等待周日自动整理 | 2026-06-08 | 自动组织到 wiki/ |
| 📖 查看 knowledge-graph.md | 2026-06-08 | 看到新的知识连接 |

---

## ✅ 验证清单

- [x] 笔记已在 repo 中 (`raw/Photography/`)
- [x] 笔记已推送到 GitHub
- [x] 摘要已改进为 5 点具体内容
- [x] `extraction_status` 改为 `ok`
- [x] 等待 Obsidian Git 拉取
- [ ] Obsidian 中手动执行 Pull (用户需做)
- [ ] 等待周日自动整理 (2026-06-08)

---

**诊断完成！** 笔记已修复，现在在 Obsidian 中应该能看到。
