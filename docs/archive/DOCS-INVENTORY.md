# Documentation Inventory

更新日期：2026-06-28

這份清單是 PersonalKM 專案文件的單一盤點表。每次新增、移除或重命名專案文件時，都要同步更新本表。

## Active Root Documents

| 文件 | 狀態 | 用途 | 更新時機 |
|:-----|:-----|:-----|:---------|
| `README.md` | Active | 專案入口、目前狀態、部署與使用方式 | 每次重要功能或流程改變 |
| `AGENTS.md` | Active | Codex/agent 工作規則、提交與部署流程 | 工作流程改變時 |
| `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md` | Active | 系統需求、架構、核心狀態與限制 | 架構或需求變更時 |
| `IMPROVEMENT-BACKLOG.md` | Active | 後續改善事項與優先順序 | 每次新增/完成改善項 |
| `CHANGELOG.md` | Active | 已完成事項與移除文件摘要 | 每次完成重要變更 |
| `DOCS-INVENTORY.md` | Active | 文件清單與維護狀態 | 每次文件異動 |
| `PROJECT-DOCUMENTATION-PROCESS.md` | Active | 文件管理流程與移除規則 | 文件治理規則改變時 |
| `KNOWLEDGE-DECAY-GUIDE.md` | Active | 知識衰退檢測操作說明 | 衰退檢測流程改變時 |

## Active Subfolder Documents

| 文件 | 狀態 | 用途 | 更新時機 |
|:-----|:-----|:-----|:---------|
| `docs/llm-wiki-v2-plan.md` | Active | LLM-Wiki v2 完整計畫、Phase 規格、Exit Conditions、執行紀錄 | v2 迭代時 |
| `docs/mac-mini-omnichannel-worker.md` | Active | Mac mini local worker 操作、安裝與排查 | worker 行為或安裝流程改變時 |
| `scripts/migrate_wiki_to_v2.py` | Active | LLM-Wiki v2 一次性遷移腳本（已用過，未來 Phase 6 可能再用） | 需再次遷移時 |
| `scripts/fix_broken_wikilinks.py` | Active | 修復失效 wikilinks 腳本 | wikilink 問題時 |
| `scripts/sanity_check.py` | Active | Repair-first vault health checker (frontmatter fixer) | 每次前端迭代時更新 |
| `scripts/query_wiki.py` | Active | CLI wiki query interface with hybrid search | 查詢邏輯改變時 |
| `outputs/ingestion-reports/*.md` | Generated | 自動 ingestion 報告 | 系統自動產生 |
| `outputs/health-check*.txt` | Generated | 健康檢查輸出 | 系統自動產生 |
| `raw/**/*.md` | Knowledge Note | LINE Bot 或 worker 捕獲的 raw notes | 系統自動產生或人工整理 |
| `wiki/**/*.md` | Knowledge Note | 整理後的 wiki notes（LLM-Wiki v2 格式） | ingestion 或人工整理 |
| `archive/**/*.md` | Knowledge Note | 已歸檔或歷史 notes | housekeeping 或人工整理 |
| `Trash/**/*.trash` | Trash | 不再視為 active note 的資料 | housekeeping 或人工整理 |

## Removed Root Documents

以下文件已不再作為獨立維護文件；內容已濃縮進 `CHANGELOG.md`、`README.md`、系統需求文件或 backlog。

| 文件 | 移除原因 | 取代位置 |
|:-----|:---------|:---------|
| `00-README-PHASE-1-4.md` | Phase 1+4 已完成 | `CHANGELOG.md` |
| `ANALYSIS-COMPLETE-DECISION-TIME.md` | 一次性決策摘要 | `CHANGELOG.md` |
| `ARCHIVE-STRATEGY.md` | 策略已併入目前 archive/trash 流程 | `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md` |
| `COMPARISON-KARPATHY-VS-PERSONALKM.md` | 一次性比較分析 | `CHANGELOG.md` |
| `DEBUG-YOUTUBE-NOT-FOUND.md` | 單次問題診斷已結案 | `CHANGELOG.md` |
| `DEPLOYMENT-CHECKLIST.md` | 舊部署檢查表已過時 | `README.md` |
| `DEPLOYMENT-COMPLETE.md` | 完成報告已結案 | `CHANGELOG.md` |
| `ENHANCEMENT-ANALYSIS.md` | 初期方案分析已結案 | `IMPROVEMENT-BACKLOG.md` |
| `ENHANCEMENT-DECISION.md` | 初期決策文件已結案 | `CHANGELOG.md` |
| `HEALTH-CHECK-SYSTEM.md` | 設計摘要已併入 backlog | `IMPROVEMENT-BACKLOG.md` |
| `IMPLEMENTATION-DELIVERY.md` | 交付報告已結案 | `CHANGELOG.md` |
| `INBOX-MIGRATION-LOG.md` | 遷移紀錄已結案 | `CHANGELOG.md` |
| `KARPATHY-ENHANCEMENT-SUMMARY.md` | 初期分析已結案 | `CHANGELOG.md` |
| `LLM-WIKI-BOT-INTEGRATION-PLAN.md` | LLM-Wiki v2 完成 | `docs/llm-wiki-v2-plan.md` |
| `LLM-WIKI-DEPLOYMENT-GUIDE.md` | LLM-Wiki v2 完成 | `docs/llm-wiki-v2-plan.md` |
| `LLMWIKI-INTEGRATION-CHANGENOTE.md` | LLM-Wiki v2 完成 | `CHANGELOG.md` |
| `OPTION-B-COMPLETE.md` | Option B 交付完成 | `CHANGELOG.md` |
| `OPTION-B-SUMMARY.md` | Option B 交付完成 | `CHANGELOG.md` |
| `PHASE-1-4-COMPLETE.md` | 完成報告已結案 | `CHANGELOG.md` |
| `PHASE-1-4-ROADMAP.md` | Roadmap 已完成 | `CHANGELOG.md` |
| `PHASE-4-MONITORING-CHECKLIST.md` | Phase 4 一次性監控完成 | `CHANGELOG.md` |
| `PREVENTION-SYSTEM-COMPLETE.md` | 完成報告已結案 | `CHANGELOG.md` |
| `QUICK-REFERENCE.md` | 舊 quick reference 已由 README 取代 | `README.md` |
| `SYSTEM-SUMMARY.md` | 完成摘要已結案 | `README.md` |
| `TODAY-SUMMARY-2026-06-07.md` | 日結摘要已結案 | `CHANGELOG.md` |
| `TOMORROW-ACTION-PLAN-2026-06-10.md` | 行動計畫已完成 | `docs/mac-mini-omnichannel-worker.md` |
| `UNIVERSAL-HEALTH-CHECK-v2.md` | 設計摘要已併入 backlog | `IMPROVEMENT-BACKLOG.md` |
| `UNIVERSAL-SYSTEM-COMPLETE.md` | 完成報告已結案 | `CHANGELOG.md` |
| `WHY-RAW-NOT-INBOX.md` | 設計決策已併入需求文件 | `LINE Bot + Obsidian 連結整理系統：需求與實施結論.md` |
| `YOUTUBE-SUMMARY-ENHANCEMENT.md` | 完成報告已結案 | `CHANGELOG.md` |

## Review Cadence

- 每次功能完成：更新 `CHANGELOG.md` 和必要的 active docs。
- 每週：檢查 root 是否出現新的臨時 `.md`。
- 每月：重新檢查 active docs 是否仍準確、必要、未過時。
- 若文件只是在描述「已完成的一次性工作」，應整理到 `CHANGELOG.md` 後移除。
