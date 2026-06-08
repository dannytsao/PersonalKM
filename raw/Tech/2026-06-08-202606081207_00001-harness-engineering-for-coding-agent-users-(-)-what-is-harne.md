---
tags: [技術]
source: LINE
date: 2026-06-08
log_id: 202606081207_00001
url: https://martinfowler.com/articles/harness-engineering.html
platform: line-message
extraction_status: ok
needs_review: false
summary: Harness Engineering 是 AI 領域中新興的系統工程學科，專注於為 AI Agent 設計控制環境、工具接口、約束機制與反饋迴路。它不改變模型本身權重，但決定模型的行為與安全性。此架構包含環境管理、約束規則、工具接口、反饋迴路與可觀測性等五大核心組件，已被 OpenAI 等企業用於提升 AI 自主編碼效率與穩定性。
status: unread
---

# [Harness engineering for coding agent users]( ) [What Is Harness Engineering for

## Log ID
202606081207_00001

## 原始貼文
[Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)
[What Is Harness Engineering for AI Agents? | Milvus - Milvus ...](https://milvus.io/blog/harness-engineering-ai-agents.md)
[Harness Engineering 是什麼？企業AI Agent 框架導入完整指南 ...](https://oakmega.com/blog/ceo-insights-010)
[What Is Harness Engineering for AI Agents? | Milvus - Milvus ...](https://milvus.io/blog/harness-engineering-ai-agents.md)

Harness Engineering（駕馭工程） 是 AI 領域中一門新興的系統工程學科，專注於為 AI Agent（智慧體）設計外圍的控制環境、工具接口、約束機制與反饋迴路。 [1, 2] 
這個術語借鑑自馬術中的「馬具（Harness，韁繩、馬鞍、馬嚼子）」。在 AI Agent 系統中，大型語言模型（LLM）是那匹強壯的馬，而 Harness Engineering 就是設計整套馬具的工程。它不改變模型本身的權重，但決定模型能走多快、往哪走、出錯時如何被拉回來。 [1, 3, 4] 
## 核心演進：從 Prompt 到 Harness [5] 
隨著 AI 從單純的「文字生成」走向能讀寫檔案、呼叫 API 的「自主執行代理」，開發重心經歷了三次遷移： [3, 5] 

* Prompt Engineering（提示工程）：優化單次對話的輸入，給予清晰指令（戰術層面）。
* Context Engineering（上下文工程）：在正確的時間將正確的知識與記憶餵給模型（信息供給）。
* Harness Engineering（駕馭工程）：建立長期運作、跨輪次任務的自動化基礎設施與安全護欄（架構層面）。 [2, 3, 6, 7] 

------------------------------
## Harness 的五大核心組件
一個完整的 AI Agent Harness 架構通常包含以下五大維度： [5, 8] 

* 環境與狀態管理 (State & Sandbox)：提供隔離的運行沙盒（如 Docker、安全虛擬機），並持久化跨對話的任務狀態。
* 架構約束與規則 (Constraints)：透過機械化規則約束 AI 行為（例如限制修改特定核心檔案、定義 AGENTS.md 規範）。
* 工具與協議接口 (Tools & MCP)：透過模型上下文協議（[MCP](https://github.com/walkinglabs/awesome-harness-engineering)）等標準，賦予 AI 呼叫 CLI、資料庫與外部 API 的能力。
* 反饋迴路與自動驗證 (Verification Loops)：將編譯錯誤、Linter 檢查或測試套件（Test Suite）的失敗訊息自動回傳給模型，使其能自我修正（背壓機制）。
* 可觀測性與人工介入 (Observability & HITL)：監控權杖（Token）消耗與成本，並在涉及刪除檔案或部署等高風險操作時觸發人類審查（Human-in-the-loop）。 [1, 3, 5, 6, 7, 8, 9, 10, 11, 12] 

------------------------------
## 行業實踐與效果
這套思維徹底改變了軟體開發與知識工作的模式： [13] 

* OpenAI 實驗案例：OpenAI 的一個 3 人團隊透過精密的 Harness 設計，讓 AI Agent 自主寫出高達 100 萬行代碼，且人均日 PR 達 3.5 個。
* 能力釋放而非模型升級：Anthropic 與知名軟體大師 [Martin Fowler 的文章](https://martinfowler.com/articles/harness-engineering.html) 指出，透過優化 Harness（如改進工具、引入更強的反饋機制），同一個模型在基準測試上的表現能從前 30 名飆升至前 5 名。AI 犯錯時，正確的做法不是換更強的模型，而是修正 Harness 環境。 [2, 5, 11, 14, 15] 

(備註：在傳統軟體工程或 DevOps 中，[Harness Engineering](https://octopus.com/devops/harness/harness-vs-jenkins/) 亦可指測試自動化中的「測試套件/測試床 Test Harness」或自動化部署平台 [Harness.io](https://www.harness.io/)，但近年在 AI 浪潮下已普遍被用來指稱 AI Agent 的駕馭系統工程。) [6, 16, 17, 18, 19] 
------------------------------
由於 Harness Engineering 依賴於具體的應用場景，為了更精準地提供幫助，請問： [6, 20, 21] 

* 您目前是希望將這套架構應用在軟體開發（AI Coding Agent）、自動化工作流（Workflow Automation），還是其他知識管理領域？
* 您目前主要使用的 AI 工具或開發框架是什麼（例如 Claude Code、LangChain 或是自行封裝的 API）？ [4, 6, 21, 22] 


[1] [https://www.nxcode.io](https://www.nxcode.io/zh-TW/resources/news/what-is-harness-engineering-complete-guide-2026)
[2] [https://www.runoob.com](https://www.runoob.com/ai-agent/harness-engineering.html)
[3] [https://wenwender.wordpress.com](https://wenwender.wordpress.com/2026/04/02/harness-engineering-ai-%E5%B7%A5%E7%A8%8B%E5%B8%AB%E7%9A%84%E7%AC%AC%E4%B8%89%E5%80%8B%E7%B6%AD%E5%BA%A6/)
[4] [https://abmedia.io](https://abmedia.io/harness-engineering-ai-agent-framework-explained)
[5] [https://rar.design](https://rar.design/posts/harness-engineering-guide)
[6] [https://oakmega.com](https://oakmega.com/blog/ceo-insights-010)
[7] [https://ai-coding.wiselychen.com](https://ai-coding.wiselychen.com/harness-engineering-architecture-overview-ai-code-production-guardrails/)
[8] [https://www.oreilly.com](https://www.oreilly.com/radar/agent-harness-engineering/)
[9] [https://github.com](https://github.com/ai-boost/awesome-harness-engineering)
[10] [https://github.com](https://github.com/walkinglabs/learn-harness-engineering)
[11] [https://addyosmani.com](https://addyosmani.com/blog/agent-harness-engineering/)
[12] [https://hackmd.io](https://hackmd.io/@BASHCAT/SkQEW0F2bg)
[13] [https://www.bnext.com.tw](https://www.bnext.com.tw/article/90734/harness-engineering-ai-guidance-gemma-experiment)
[14] [https://github.com](https://github.com/deusyu/harness-engineering)
[15] [https://martinfowler.com](https://martinfowler.com/articles/harness-engineering.html)
[16] https://www.harness.io
[17] [https://en.wikipedia.org](https://en.wikipedia.org/wiki/Test_harness)
[18] [https://octopus.com](https://octopus.com/devops/harness/harness-vs-jenkins/)
[19] [https://data.landbase.com](https://data.landbase.com/technology/harness/)
[20] [https://zhuanlan.zhihu.com](https://zhuanlan.zhihu.com/p/2014014859164026634)
[21] [https://github.com](https://github.com/walkinglabs/awesome-harness-engineering)
[22] [https://medium.com](https://medium.com/@visrow/harness-engineering-the-infrastructure-layer-that-makes-ai-agents-actually-work-598a279c1c5f)

## 內含連結
- https://martinfowler.com/articles/harness-engineering.html
- https://milvus.io/blog/harness-engineering-ai-agents.md
- https://oakmega.com/blog/ceo-insights-010
- https://github.com/walkinglabs/awesome-harness-engineering
- https://octopus.com/devops/harness/harness-vs-jenkins/
- https://www.harness.io/
- https://www.nxcode.io
- https://www.nxcode.io/zh-TW/resources/news/what-is-harness-engineering-complete-guide-2026
- https://www.runoob.com
- https://www.runoob.com/ai-agent/harness-engineering.html
- https://wenwender.wordpress.com
- https://wenwender.wordpress.com/2026/04/02/harness-engineering-ai-%E5%B7%A5%E7%A8%8B%E5%B8%AB%E7%9A%84%E7%AC%AC%E4%B8%89%E5%80%8B%E7%B6%AD%E5%BA%A6/
- https://abmedia.io
- https://abmedia.io/harness-engineering-ai-agent-framework-explained
- https://rar.design
- https://rar.design/posts/harness-engineering-guide
- https://oakmega.com
- https://ai-coding.wiselychen.com
- https://ai-coding.wiselychen.com/harness-engineering-architecture-overview-ai-code-production-guardrails/
- https://www.oreilly.com
- https://www.oreilly.com/radar/agent-harness-engineering/
- https://github.com
- https://github.com/ai-boost/awesome-harness-engineering
- https://github.com/walkinglabs/learn-harness-engineering
- https://addyosmani.com
- https://addyosmani.com/blog/agent-harness-engineering/
- https://hackmd.io
- https://hackmd.io/@BASHCAT/SkQEW0F2bg
- https://www.bnext.com.tw
- https://www.bnext.com.tw/article/90734/harness-engineering-ai-guidance-gemma-experiment
- https://github.com/deusyu/harness-engineering
- https://martinfowler.com
- https://www.harness.io
- https://en.wikipedia.org
- https://en.wikipedia.org/wiki/Test_harness
- https://octopus.com
- https://data.landbase.com
- https://data.landbase.com/technology/harness/
- https://zhuanlan.zhihu.com
- https://zhuanlan.zhihu.com/p/2014014859164026634
- https://medium.com
- https://medium.com/@visrow/harness-engineering-the-infrastructure-layer-that-makes-ai-agents-actually-work-598a279c1c5f
