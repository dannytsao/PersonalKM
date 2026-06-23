# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-06-13] init | LLM Wiki integration + schema

- Integrated Karpathy/LLM-Wiki pattern with existing PersonalKM structure
- Created SCHEMA.md with domain (multi-domain KM: Tech, Food, Photography, General)
- Created index.md with navigation
- Created log.md (this file)
- Preserved existing raw/ (285 files across 4 categories), wiki/entities/ (1 test file), wiki/concepts/, wiki/sources/
- Established tag taxonomy covering domain, topic, quality, and processing tags
- Decay management integrated: pages >90 days flagged automatically
- Configured cross-domain linking rules (Tech ↔ Productivity, Tech ↔ Food, Photography ↔ Travel)
- Set WIKI_PATH env var to: /Users/dannytsao/Documents/PersonalKM/wiki

---

**Orientation for new sessions:**
1. Read SCHEMA.md for domain + conventions + tag taxonomy
2. Read index.md to see all pages organized by type
3. Scan recent log.md entries (last 20-30 lines) to understand recent activity
4. search_files for specific topics before creating new pages

## [2026-06-14 08:33:34] ingest | 2026-06-11-202606111452_00001-天文生物學家「們」如何看待發現外星生命
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120616_00001-海邊走走旅居👣-(@cozy_seaside_kenting)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120618_00001-葉咪乓-(@mipong_0722)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100002_00001-好感旅宿開箱-on-instagram-散步的雲-日月潭-低碳療癒風・生態旅宿☁️🌿-🏡-山林與湖畔的慢旅小宿-散步的雲
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101202_00001-田-定豐-on-instagram-當一個地方開始出現在常規的觀光地圖上,有了平整的柏油路與人工修飾的現代線條,那份原本
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120617_00001-邱文寶-(@bao_chiou)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-wikipedia,-the-free-encyclopedia
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-一定要配温開水
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-知乎专栏-随心写作,自由表达-知乎
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-什么值得买_社区频道-笔记_购物攻略_消费主张分享
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-zhuanlan.zhihu.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-medium.com-2
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120615_00001-他和她出乃玩-(@heandshe216)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-medium.com-2
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-medium.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100004_00001-好感旅宿開箱-on-instagram-遇見雲山居-池上・絕美環景玻璃屋-×-縱谷包棟首選-🏔️✨-想在縱谷體驗「白天賞
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-share.google
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-yahoo新聞
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101202_00003-flora光影慢旅-✧-旅行-攝影-日常-on-instagram-台北散步地圖-公館-蟾蜍山煥民新村-很喜歡一些有一些
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606090920_00001-tools.wingzero.tw
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092351_00001-mountain-kids-山小孩-(@mountainnn.kids)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-zhuanlan.zhihu.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-medium.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-medium.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100004_00001-好感旅宿開箱-on-instagram
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-share.google-2
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-medium.com-2
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100009_00001-taichungbaobao-on-instagram-嘿,台中人!你知道台中隱藏的秘境有哪些嗎-✨-想知道更多這些隱藏
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100622_00001-the-biggest-lie-you've-been-told-about-hermes-agent
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-知乎专栏-随心写作,自由表达-知乎
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081300_00001-結論-這篇《今周刊》報導中所提到的耶魯醫學博士健走處方,正確答案是-一次只要走-45-分鐘-。-支持原因與來源引用-根據
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-youtube
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-https-post.m.smzdm.com-p-ak8prew9
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-abmedia.io
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-openai.com
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-linkedin-log-in-or-sign-up
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-https-jdev.tw
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081321_00001-漫步茶香古道間!-臺北大縱走六月限定寶石王等你來挑戰
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-instagram
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-yahoo股市
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101204_00001-smile-taiwan微笑台灣-on-instagram-微笑台灣巡迴講座-▷▷苗栗銅鑼-由老屋長出的新生命-巡迴紀錄
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100003_00001-好感旅宿開箱-on-instagram-茶田關舍-貳館-臺東關山-輕奢雅緻設計,細膩勾勒高質感氛圍-🌿-簡約而俐落的設計
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-在地人才知道,就是瑪瑙綠鏡湖,沿湖步道繞一圈免10分鐘,美麗湖光是招牌
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606090641_00001-生日花有很多個版本,花語也不盡相同。試試看你的chatgpt會跑出的生日花雜誌封面會是什麼。性別和長相請自行修改。-產生
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092349_00002-路小飯-(@palapalakk1489)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101202_00002-dribs-&-drabs-點點滴滴-on-instagram-.-🌿-新竹北埔景點美食-10-選-🔖-走入茶金百年歷史
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120602_00002-凹屋珈琲-awoo-kohii-(@awoo_kohii)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-11-202606112210_00001-一半人不知道,加油站有在賣火鍋,便宜又好吃,每天都大排隊!
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081321_00001-鳥貴族「899元吃到飽」再增南西店-120分鐘無限供應-ettoday旅遊雲-ettoday新聞雲
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101206_00002-美比拌飯-on-instagram-米其林必比登的60年雲南菜老店-菜色很有特色-而且很好訂耶-📍人和園餐廳-台北市中山
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092349_00001-夢飛行-flying-dream-(@flyingdream8888)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120613_00001-嘿!部落!-(@blogimove)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101203_00001-smile-taiwan微笑台灣-on-instagram-台東・大武-南迴四鄉最美書店,山海小鎮裡的「家家酒書房」,讓
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081325_00001-俊2的美食日記-📙台北美食-on-instagram-大同📍大稻埕贏過台南小吃的神級蝦仁飯-在捷運中山跟北門站附近的迪化
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606091420_00001-艾瑪-吃喝玩樂-(@alma_8082)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-一半人沒來過,是大橋景觀咖啡,低消250能窩半天,南洋氣息是主打特色
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120603_00001-天母大頭鵝-鵝肉專賣店-(@tianmu_da_tou_goose)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092346_00001-jacky-chen-(@jacky841229)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092348_00001-譚力詩-jana-(@lishihtan)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120608_00002-google高達4.5顆星!
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100008_00001-april-on-instagram-上次去北投-在石牌站走路6分鐘的地方-吃到一間湯頭有在厲害的火鍋😳-如果開在我家附
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101206_00001-aga不專業食記-on-instagram-🚩主打有機、天然、在地食材的百匯吃到飽-沒有繁複的重口味調味,只有食材本身的
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100007_00001-遇fun胃-台北-台中美食-日韓港泰旅遊展覽-on-instagram-假日不想人擠人-這個台北秘境先收藏✨-不只看得到
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606100009_00001-小杜-on-instagram-📍青雲-misty-龍山寺附近的巷弄裡,竟然藏著一棟百年歷史建築-,-進門後那個挑高的空
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101204_00001-吃貨系紋繡師-✿-變美-美食-生活日常-on-instagram-有些地方,適合用來躲避全世界🌍-北投老宅咖啡廳-隱身巷
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131057_00001-省下96美金!obsidian全平台同步免费教程,5步搞定手机电脑互通(2026最新)
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-hermes-agent-tutorial-for-beginners-(full-step-by-step-setup
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120611_00001-松音(小美)-(@dseditor)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-dev-community
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-大部分的-rag-都是個黑箱。-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-vs.-jenkins-devops-tool-comparison
- Type: entities
- Categories: devops

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606122224_00001-這影片生成-ai-工具太狂!10-分鐘用-codex-+-hyperframe,把圖片、pdf、官網瞬間變成宣傳片,串聯
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-github-·-change-is-constant.-github-keeps-you-ahead.
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101213_00001-傳-openai-內部喊出「聊天已死」!chatgpt-將轉型-ai-超級-app-電腦王阿達
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-11-202606111253_00001-how-to-build-a-multi-agent-workflow-for-llm-wikis-in-hermes
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131054_00001-不用终端!用手机远程让ai管理你的obsidian笔记-openclaw-+-obsidian-cli-教程
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-private-obsidian-ai-add-deepseek-to-your-obsidian-with-ollam
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081320_00002-claude-code-vs-codex-完整教學-新手怎麼選-非工程師也能上手的桌面版比較
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-您的敏銳度非常高!「plan-➔-execute-➔-evaluate(計畫-➔-執行-➔-評估)」-這個核心邏輯,在概
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-hermes-agent-官方正式推出桌面版應用程式!輕鬆一鍵安裝,科技小白也能快速上手
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-skill-issue-andrej-karpathy-on-code-agents,-autoresearch,-an
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-【aigc实战课-109】榨干你的plus会员!在comfyui调用gpt会员生图,无需api,几乎免费!
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-hermes-desktop-從終端機走向-gui,推出原生三平台桌面版本,主打跨通訊平台「統一記憶」-inside
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-claude-platform
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-github-·-change-is-constant.-github-keeps-you-ahead.
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-https-community.hpe.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606130752_00001-ai-agent-benchmark-for-real-world-professional-workflows
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120955_00001-genai-&-agentic-ai-論壇-【claude-code-官方使用秘訣】-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-07-my-full-claude-cowork-setup-(steal-my-workflows!)
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-07-my-obsidian-vault-in-2026-what-i-actually-open-every-day
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-claude-+-karpathy's-second-brain-is-insane
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120619_00001-ai-工具情報局-(@tech.ai_tw)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-plan-mode-vs-direct-execution-the-ai-agent-factory
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-empower-your-business-in-usa-&-canada-with-alibaba-cloud's-c
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-ollama
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606090616_00001-facebook
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-obsidian-smart-connections-update-📝-rediscover-notes-with-ob
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-hermes-桌面版app上線!免終端-mit-開源、支援-macos、windows-與-linux
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-generative-ai-技術交流中心-企業在導入-ai-應用時,常面臨現行「檢索增強生成(rag)」系統的瓶頸-fa
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-07-i-built-an-ai-second-brain-using-obsidian-+-claude-(copy-me)
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-martinfowler.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-hermes-agent-official-new-desktop-app-the-24-7-self-evolving
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-07-我想用ai做一個微電影,大約10分鐘,我應該先怎麼開始-我有個大約的劇本了,gpt幫我寫了,然後我要怎麼變成電影呢-fa
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606091822_00001-govin.ai-(@govin999999)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606102053_00001-claude-應用社群-用-claude-code-跟-codex-久了,我有兩個固定的煩躁點-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081320_00001-微軟公佈-project-solara-新系統平台-不用-windows-改用-android-核心,專門運行-ai-代-2
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131033_00001-从0搭建ai第二大脑-obsidian-+-claude-code-保姆级全流程教程(非技术人也能做)
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606090622_00001-generative-ai-技術交流中心-agent-需要工具時,llm-生成-cli-skill-plugins-mc
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-電腦王阿達
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-addyosmani.com
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092143_00002-别再乱装skill了!这-4-组skill,才是agent的顶级生产力。
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092348_00001-prompt-case-(@prompt_case)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-11-202606112206_00001-小米推出開源編程-cli-mimo-code-具備跨-session-記憶、無限上下文、限時免費使用-電腦王阿達
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-github-·-change-is-constant.-github-keeps-you-ahead.
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-github-hinterdupfinger-obsidian-ollama
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-11-202606110953_00001-這是一個完美的起跑點!既然您已經完成了-sdd(軟體設計規格書),且偏好「看著它一步步改」的精密掌控模式,您現在就像是一
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-engineering-for-coding-agent-users-(-)-what-is-harne
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-stanley-(@stanleysobest)-on-x
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-ralph-wiggum-loop-autonomous-coding-with-fresh-context
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081321_00002-gemini-in-sheets新功能實測-「@」一下就讀雲端硬碟、幫你建表格,3個情境用法一次看
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131208_00001-让-ai-洞察你的知识网络-obsidian-cli
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-obsidian-community-2
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131323_00001-govin.ai-(@govin999999)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-oakmega-social-crm-完美銜接-line-與顧客管理系統
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131242_00001-obsidian必裝插件-新手第一週就該知道的8個神器
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-open-{re}source
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-07-煮酒論英雄-世界政經轉譯機
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-official-hermes-desktop-is-finally-here
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-the-ralph-loop-explained-automate-ai-coding-tasks-in-java
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081250_00001-openclaw-x-hermes-ai-agents-&-monetization-(hidden-opportuni
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-home
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-allow-configuring-different-models-for-plan-mode-vs-executio
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606130754_00001-github-rdi-berkeley-agents-last-exam-agents'-last-exam
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-obs157-用copilot外掛使用本地ai模型服務-使用ollama與lm-studio-–-簡睿隨筆
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-obsidian-community
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-09-202606092143_00001-1000份文档丢给ai,30分钟自动归档+知识图谱,还能写带引用的新方案-claude-code+obsidian
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131006_00001-如何为-obsidian-配置-ai-agent-9-个必备-skill-详解与安装指南
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-07-hermes-agent出桌面端app,告别终端,这才是ai-agent的未来
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131148_00001-explore-&-discover-obsidian-plugins-and-themes
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-ai-app-builder-build-apps-without-coding-2026-nxcode-nxcode
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-prompt-case-(@prompt_case)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101211_00001-mcp-是什麼-claude-code-核心功能詳解-以-figma、n8n-為例打造會動手的-ai
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-engineering-—-ai-工程師的第三個維度
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-11-202606111254_00002-hermes-agent-masterclass-3.-memory,-plugins,-honcho,-and-obs
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-engineering-完全解析-當-ai-agent-的護城河不再是模型,而是環境-hackmd
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-inventing-the-ralph-wiggum-loop-creator-geoffrey-huntley
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131246_00001-claude-code-+-obsidian-個人知識庫,token-用量直接節省-95%
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-13-202606131203_00001-【obsidian-第二大腦-ai-強化】copilot-搭配-ollama-讓你的筆記更聰明!安裝教學
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-ai-for-devops,-testing,-appsec,-and-cost-optimizatio-2
- Type: entities
- Categories: devops

## [2026-06-14 08:33:34] ingest | 2026-06-07-build-an-ai-second-brain-knowledge-base-(step-by-step)
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120619_00001-沈重宗-ai-esg-數位轉型-(@jackshenaiadvisor)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-engineering(驾驭工程)-菜鸟教程
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-agent-harness-engineering
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-hermes-agent-official-new-desktop-app-the-24-7-self-evolving-2
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-github-walkinglabs-learn-harness-engineering-harness-enginee
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120623_00001-@largitdata-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-07-只用codex真实办公的一天-最好用的agent软件-codex使用技巧-提升工作效率
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-hyperframes教程-用这套方法,让-codex-剪视频效果以及效率翻倍
- Type: concepts
- Categories: general

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-what-is-harness-engineering-for-ai-agents-milvus-milvus-blog
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120612_00001-未來商務-(@futurecommerce_official)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606081207_00001-harness-engineering-是什麼-企業-ai-agent-框架導入完整指南-ceo-insights
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-08-202606082356_00001-stop-using-claude-without-an-agentic-os
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-ai-credits-&-startup-perks-save-up-to-$7m-on-220+-tools-get
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-12-202606120624_00001-碩-(@s_h_u_ooo)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:34] ingest | 2026-06-10-202606101713_00001-codecentric-ag-creating-the-digital-future-together.
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-07-the-3-file-ai-system-that-works-with-any-model
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-透過將-obsidian-與-ollama-整合,你可以在完全斷網、保護隱私的環境下,利用本地的-ai-大型語言模型(如
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-11-202606111453_00001-‏‏٢٢-ألف‏-مشاهدة‏-·-‏‏٢٥٢‏-تفاعلاً‏-google-colab-cli-與-skill
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-test-harness-wikipedia
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-ai-技術研究社-chatgpt-gemini-claude-openclaw-𓂀寫扣-x-教學-x-講幹話-分享最近用
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-github-deusyu-harness-engineering-harness-engineering-学习指南-—
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-inside-社群媒體、行動網路、行銷、技術、創業
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-09-202606091813_00001-sliven-(@sliven0722)-on-threads
- Type: entities
- Categories: devops

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-obsidian-and-ollama-free-local-ai-powered-pkm
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-12-202606120602_00001-govin.ai-(@govin999999)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-codewithmukesh-.net-10-tutorials,-benchmarks-&-courses-codew
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-12-202606120603_00002-愛ai大師-(@master_aiaiai)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-harness-ai-for-devops,-testing,-appsec,-and-cost-optimizatio
- Type: entities
- Categories: devops

## [2026-06-14 08:33:35] ingest | 2026-06-07-the-hermes-desktop-app-changes-everything-(full-setup)
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101542_00001-google-ai-mode-share
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-09-202606092143_00003-claude-cowork-深度体验-我把整套内容工作流装进了-ai,从选题到封面全自动
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-harness-engineering-架構全景-ai-可以寫-code,但不能自己上-production
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-ollama-–-obsidian-plugin-·-obsidian-stats
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101710_00001-這是一份為您彙整的完整知識藍圖,記錄了您從最初詢問熱門術語,到逐步理清-「ai-代理自動化開發(agentic-deve
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-github-fathah-hermes-desktop-desktop-companion-for-hermes-ag
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-github-walkinglabs-awesome-harness-engineering-🛠️-awesome-to
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-11-202606110612_00001-電腦王阿達
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-plan-mode-in-claude-code-think-before-you-build-with-ai-code
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-https-community.hpe.com-t5-software-general-building-a-local
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-07-claude-cowork是什麼、怎麼用-新手10分鐘設定教學,一次學會檔案自動化
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606082348_00001-【2026最新】ai短剧制作全套教程!免费送全套资料包+提示词+模型整合包
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606130833_00001-不會寫程式也能用!hermes-agent桌面版完整教學-模型串接-排程任務-實際應用
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-nous-research-推出-hermes-desktop-公測版-ai-agent-告別終端機時代
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-不再開命令列!用-hermes-desktop-一鍵駕馭自我進化的本地-ai-助理(支援-16-種訊息平台-+-ssh
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-hermes-agent-new-desktop-app-the-24-7-self-evolving-ai-agent
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-11-202606111244_00001-openclaw-中文社群-【agent-是你的員工、助理、還是工具人-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-數位時代-businessnext
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-the-ralph-loop-a-practical-pattern-for-reliable-ai-agents-(a
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-threads-•-log-in
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-google-ai-mode-share-2
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606082326_00001-零成本教學-用ai把任何歌曲秒變ktv伴奏帶
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-youtube
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-11-202606111254_00001-2026普通人学ai-推荐吴恩达这8门课,帮你补齐知识地图-ai入门系统化学习
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-12-202606120608_00001-數位時代-(@bnext_official)-on-threads
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-agent-harness-engineering-2
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-github-fathah-hermes-desktop-desktop-companion-for-hermes-..
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-hackmd-your-collaborative-markdown-workspace-for-knowledge-s
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606082306_00001-anthropic-academy-claude-官方-13-門線上課程免費上、可領官方證書-電腦王阿達
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-code-execution-tool
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606130938_00001-跟kaparthy学搭建ai知识库-附obsidian实例
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-rar-設計攻略
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-genai-&-agentic-ai-論壇-google-把整個工程教育團隊裁掉了——這不只是一次裁員,這是一個訊號-f
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-plutoplatypus-on-instagram-using-local-models-through-ollama
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-google-ai-mode-share
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-continuous-deployment-&-delivery-software-for-devops-teams-o
- Type: entities
- Categories: devops

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-how-i-built-a-local-ai-assistant-for-obsidian-—-no-cloud,-no
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-obsidian-publish
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-09-202606092353_00001-prompt-case-(@prompt_case)-on-threads
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-harness-engineering-for-coding-agent-users
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-o'reilly-media-technology-and-business-training
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-releases-·-fathah-hermes-desktop
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101106_00001-new-notebooklm-ai-agent!
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-youtube
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-11-202606111123_00001-linebot-astro-bot-sceret-773c4c47f5368c1853b3fb033abc944c
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-facebook
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-github-martwozniak-ollama-obsidian-integration-this-plugin-i
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-12-202606122105_00001-【附送工具-+-模型网站】10分钟教会你0成本用上codex,不花一分钱,实现agent自由!
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-09-202606092144_00001-codex-額度總是不夠-零基礎先學這4個進階技巧-含多案例實操
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-from-react-to-ralph-loop-a-continuous-iteration-paradigm-for
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-claude-code-by-anthropic-ai-coding-agent,-terminal,-ide
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-obsidian-copilot-auto-completion-docs-how-to-ollama-setup-gu
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606130932_00001-矽谷大神-karpathy-筆記術!十分鐘學會如何用-claude-code-建立個人知識庫
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-【obsidian-第二大腦-ai-強化】copilot-搭配-ollama-讓你的筆記更聰明!安裝教學
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-how-claude-code-works-claude-code-docs
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081251_00001-openclaw-x-hermes-ai-agents-&-monetization-(hidden-opportuni
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-repoinside-開源專案深度解析
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-saturday-morning-with-ralph-→-ralf-from-idea-to-working-exte
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-abmedia.io
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-harness-engineering-是什麼-ai-代寫程式時代你也該懂的工程觀念
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-【2026-5-29-課程錄影】copilot-cowork-ai-協作與自動化最佳實務-微軟-microsoft-36
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-07-gemma-4-12b-on-a-16gb-mac-mini-is-surprisingly-capable
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-什麼是-harness-engineering-ai-agent-開發完整指南-(2026)-nxcode
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606090627_00001-ai-技術研究社-chatgpt-gemini-claude-openclaw-𓂀寫扣-x-教學-x-講幹話-醫院最新引
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606100023_00001-mqtt-與-aiot-整合運用-【本地玩轉-近期較熱門的gemma-4-12b-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-企業-ai-轉型實戰指南-ai-agent-架構、地端-llm、ai-資安完整指南
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-12-202606120627_00001-llm-wiki
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-openai.com
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606102051_00001-facebook
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-the-ai-agent-factory
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-菜鸟教程
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-harness-engineering是什麼-台大教授80字實驗揭-ai為何仍需人類引導,還會越罵越笨
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-github-·-change-is-constant.-github-keeps-you-ahead.
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-github-nousresearch-hermes-agent-the-agent-that-grows-with-y
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-running-a-local-ai-inside-obsidian-with-ollama
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-dev-interrupted-substack
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606130950_00001-karpathy知识库搭建-obsidian+大模型llm
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131109_00001-我用ai-+-obsidian-搭了一个-会思考-的第二大脑-告别灵感焦虑
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-github-ai-boost-awesome-harness-engineering-awesome-list-for
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131148_00001-ollama-obsidian-hub-obsidian-publish
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081207_00001-harness
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131121_00001-ai个人知识库搭建教程-用karpathy的llm-wiki方法,三步让收藏夹真正发挥价值
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-09-202606092356_00001-github-pat-jj-harness-1-🚀-ultra-recipe-for-training-long-hor
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606131015_00001-如何为-obsidian-配置-ai-agent-9-个必备-skill-详解与安装指南
- Type: entities
- Categories: devops, ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606130856_00001-我进入任何新行业都会做这5件事-codex-+-obsidian-行业研究完整流程
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101152_00001-will-保哥的技術交流中心
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-10-202606101713_00001-claude-code-plan-mode-2026-complete-guide-with-shortcuts
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-13-202606130017_00001-claude-taiwan-它今天幫你看額度-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-202606081320_00001-微軟公佈-project-solara-新系統平台-不用-windows-改用-android-核心,專門運行-ai-代
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-08-facebook-2
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-08-動區動趨-blocktempo-最有影響力的區塊鏈新聞媒體-(比特幣,-加密貨幣)
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-07-8萬顆星的hermes-agent少了它根本不能用!3分鐘打造ai中控台
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest | 2026-06-11-202606112209_00001-notebooklm完整攻略-22篇實戰一次收,建知識庫、做簡報、會議財報全應用
- Type: concepts
- Categories: general

## [2026-06-14 08:33:35] ingest | 2026-06-12-202606120931_00001-generative-ai-技術交流中心-現在的ai到底是有多誇張-facebook
- Type: entities
- Categories: ai

## [2026-06-14 08:33:35] ingest_batch | Processed: 273 notes; Trashed (low-quality): 12 notes
- Created: concepts/2026-06-11-202606111452_00001-天文生物學家「們」如何看待發現外星生命, concepts/2026-06-12-202606120616_00001-海邊走走旅居👣-(@cozy_seaside_kenting)-on-threads, concepts/2026-06-12-202606120618_00001-葉咪乓-(@mipong_0722)-on-threads, concepts/2026-06-10-202606100002_00001-好感旅宿開箱-on-instagram-散步的雲-日月潭-低碳療癒風・生態旅宿☁️🌿-🏡-山林與湖畔的慢旅小宿-散步的雲, concepts/2026-06-10-202606101202_00001-田-定豐-on-instagram-當一個地方開始出現在常規的觀光地圖上,有了平整的柏油路與人工修飾的現代線條,那份原本 (+268 more)
- Trashed: General/2026-06-13-202606131148_00001-reddit-please-wait-for-verification.md, General/2026-06-10-202606101713_00001-reddit-please-wait-for-verification.md, General/2026-06-08-reddit-please-wait-for-verification.md, General/2026-06-10-202606101713_00001-reddit-please-wait-for-verification-2.md, General/2026-06-08-x-twitter-post.md, Photography/2026-06-07-銀河季開跑!台灣十大銀河拍攝點,第一名不是合歡山!蘭嶼未進前十名!-這些地點是經過我7年銀河攝影經驗的總結,這部影片絕對.md, Food/2026-06-14-202606140417_00001-膳緣江浙料理-on-instagram-你知道台北永和有一家-正宗道地的上海江浙料理嗎-—膳緣江浙料理-翁師父歡迎大家隨.md, Tech/2026-06-13-202606131148_00001-obsidian-with-ollama.md, Tech/2026-06-13-202606131148_00001-reddit-please-wait-for-verification.md, Tech/2026-06-08-youtube.md (+2 more)

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606180943_00002-post-from-朱學恒的萬事通事務所
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162119_00001-bellataiwan-bella儂儂-on-instagram-儂儂旅社-坐落於台南安平四草大道旁,全新度假村「逸點亦
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170036_00001-新北北海岸不輸國外海島!-天人菊盛開打造橘紅色海岸線
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161617_00001-l.facebook.com-l.php-u=https%3a%2f%2fduringmyjourney.com%2fx
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161425_00001-glasp.co
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161618_00001-duringmyjourney.com
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-22-202606220703_00001-dribs-drabs.com
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-23-202606231026_00002-孤獨感-配對程式設計午餐-claude-code-團隊發現了一個問題-因為大家都在跟自己的-agent-一起工作,開始覺
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-youtube-video-m8huxu_boco這部影片是由
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606201847_00001-share.google
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162248_00001-you're-using-ralph-wiggum-loops-wrong
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170034_00001-youtube
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606201858_00001-好身材不會從天上掉下來!上半身、下半身、全身,3-套各-10-分鐘訓練輪著做,現在開始還來得及!
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162115_00001-田-定豐-on-instagram-這些地點不僅僅是台北的風景,更是我在忙碌與喧囂的日常裡,為自己挑選的獨處角落。-每個
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-23-202606231139_00001-貝德洛-(@hongfande)-on-threads
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606201847_00002-share.google
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606200805_00001-整個6月「人人免門票」!最美「巴洛克風城堡」免費入園-朝聖「3大全台之最」、端午連假加碼「陸上龍舟賽」統統有獎-聯合新聞
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170513_00002-後期合成光影匹配(lighting-&-shadow-matching-in-compositing)-是決定合成圖像是
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170514_00001-dodge-and-burn(閃避與加深)-是數位影像後期中最經典、也最強大的-選擇性光影塑形技術-。它源自傳統暗房時代
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162117_00001-我的旅圖中during-my-journey-on-instagram-金山老街裡的隱藏版老宅咖啡廳☕️-金山老街的巷子
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606201831_00001-網路溫度計dailyview-on-instagram-🥢-台北東門市場吃什麼-🔥-📣十大必吃必買清單出爐-連林青霞、林
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606182244_00001-價格親民!當地人不想被公布的餐廳,看起來不起眼,但餐真的蠻有水準,且不油膩又耐吃!真的是高手在民間。
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162116_00001-那個好吃-on-instagram-🗣️google推薦+台南人推薦的清單-36家🐂🥩🥣-還有誰被遺漏的-👀-✅更正-中
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162116_00001-阿天天-tian-〰️台北新北兼半個台中人-on-instagram-三代傳統開業超過60年老店-500碗美食總統包子,
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170033_00001-兆元男輝達nvidia黃仁勳的最愛,這家湯包真的太好吃了啦
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606201831_00002-老k嘴一下-台北-美食-咖啡廳-旅遊-景點-on-instagram-台北最猛煲仔飯🔥香港師傅坐鎮,低調卻超強的30年老
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-21-202606211804_00001-teamorouter-budget-llm-gateway-for-claude-code-and-codex
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170857_00002-别再乱装skill了!这4组skill才是agent的顶级生产力!
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161428_00001-【2026最新】这绝对是全网最好的obsidian喂饭教程,20分钟搞定一站式入门双向链接笔记软件,手把手教你使用obs
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-15-202606151006_00001-releases-·-allenk-geminiwatermarktool
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-21-202606211804_00001-github-anthropics-claude-code-claude-code-is-an-agentic-codi
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-23-202606231027_00001-genai-&-agentic-ai-論壇-💊💊💊-claudecode-fionafung-ai-pilled-💊💊💊
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142348_00001-hermes-agent-保姆級教學來了!最安全的-ai-私人助理造成-opanclaw-大規模棄養潮,用過就回不去了!
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161425_00001-這部影片詳細介紹了如何將-graphify-、-obsidian-與-claude-code-結合,打造出一個強大的知識
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14-15
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-22-202606221025_00001-hermes-agent-保姆級零基礎教程-玩爆openclaw-codex,小白零基礎零代碼上手
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161909_00001-擴展-claude-code-claude-code-docs
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-23-202606231026_00001-在看-lenny-訪-fiona-fung-這集,fiona-fung-是-ai-研發公司-anthropic-旗下核心
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142217_00001-ai_agent-基本功-ep01-用-agent-來學習-agent
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-22-202606221118_00001-vchewing-唯音輸入法-·
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161425_00001-google-search
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-22-202606221458_00001-即時字幕-studio0808
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170857_00001-碾压-claude!7b开源小模型成功率暴涨15倍,-ai-agent-神作-strata
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-23-202606231212_00001-小白6分钟速通codex,操控电脑、办公、生图、自动化,轻松上手!
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606180620_00001-github-voidful-hung-yi-lee-skill-蒸餾李宏毅老師的skill,結合karpathy的ll
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-21-202606211407_00001-openai-codex-推出-record-and-replay-做一次給-ai-看,自動學會你的工作流程-電腦王阿達
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606180937_00001-openai-codex-cli-開放支援第三方模型!deepseek、claude、gemini、ollama-都能用
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162253_00001-這部由-agentic-lab-頻道發布的影片《you're-using-ralph-wiggum-loops-wron
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170638_00001-harness-engineering-到底是什么-概念、实战与争议,一次全部讲清楚
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606200723_00001-2026-ai-提示詞最佳設計指南-gpt、claude、gemini-共通框架,與-ai-溝通的黃金公式一次看懂直接進
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606171641_00001-chatgpt-x-ai-融入教學-【notebooklm-走向-agent,但真正的護城河不該只是「更會做事」】-fa
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606171639_00001-gemini教學大全!35篇實測整理,notebooks知識庫、workspace辦公自動化一次收
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606180943_00001-loop-engineering-全攻略-2026-工程師必修
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142044_00002-github-farion1231-cc-switch-a-cross-platform-desktop-all-in
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161556_00001-generative-ai-技術交流中心-【davinci-resolve-21-三個以前要付錢才有的-ai-功能,現在
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161422_00001-全网最全保姆级hermes安装教程,别再只养龙虾了,hermes-agent-才是-2026-最狠自进化-ai-助手
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170659_00001-gemma-4-12b-+-hermes-agent-build-your-own-ai-assistant
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142345_00001-gemini-api-提供每日免費-3,000-次呼叫的-gemma-4-26b、31b-模型,免填信用卡、可串-ope
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18-19-20
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606171859_00001-最近看到-google-workspace-studio-這類工具,我覺得它真正值得討論的,不只是「ai-又多了一個新功
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-anthropic-的技術團隊成員、同時也是-claude-code-的創作者-boris-cherny-所帶來的實用技
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-21-202606211804_00001-對於在-codex-desktop-與-claude-code-desktop-(-)-這類開發者-agent-工具中使
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606201043_00001-零基礎30分鐘學會codex-95%功能!【福利贈送】
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162121_00001-🚀【google-colab-也能變身-ai-程式開發神器!】-facebook
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142044_00001-releases-·-farion1231-cc-switch
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161305_00001-claude-官方指南,如何打造-ai-原生新創公司
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12-13-14-15-16-17-18
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-15-202606151001_00001-data-science-machine-learning-ai-freelance-jobs-🚀-struggling
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161425_00002-graphify-+-obsidian-+-claude-code-=-cheat-code
- Type: entities
- Categories: devops, ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606172147_00001-obsidian-bases数据库功能快速入门-dataview可以删了-不用再羡慕notion了,obsidian也有
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162118_00001-chris-ai應用-克里斯-on-instagram-ig-存了-40-個景點-收藏-20-篇美食-真要排行程-→-打
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161426_00001-ai-agent基本功ep01-用agent來學習agent_一個-github-repo,複製我的整套-ai-工作流到
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170815_00001-karpathy-的-llm-wiki-火了,我改造了一下,比原版好用十倍
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11-12
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142314_00001-obsidian教程-如何设置好看的主题
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-20-202606200720_00001-cp值怪物來了!hdmi-無線傳輸器竟然這麼強-業界秘密大公開!-hdmi無線圖傳
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606162233_00001-github-dietrichgebert-ponytail-makes-your-ai-agent-think-lik
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606160001_00001-用claude-5分鐘幹完半天的活!產品經理必備的1.7萬星claude神器
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170856_00001-loop-engineering-火了-ai-agent-的杠杆,正在从-prompt-移到-loop
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-22-202606221459_00001-github-begin0808-livecaption-即時影音雙語字幕翻譯系統。本機離線-ai-語音辨識與翻譯,支援
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-17-202606170453_00001-github-zaxardery8011-design-line-persona-line-影分身-—-低門檻的-byo
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606141220_00001-「openchamber」vs-code-延伸模組(extension)推薦,提升-opencode-開發體驗-face
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-21-202606211804_00001-teamorouter-budget-llm-gateway-for-claude-code-and-codex-2
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-14-202606142354_00001-3步搭出ai时代第二大脑-文字图片skill全进一个库,淘汰notion和obsidian-0代码小白也能用claude
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-16-202606161427_00001-idea-worth-to-think-if-the-tag-of-obsidian-can-auto-gen-muti
- Type: concepts
- Categories: general

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-15-202606151235_00001-🔥別再亂下prompt!22萬人都在抄這份claude.md,原因太震撼!
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-22-202606221404_00001-🚀karpathy知识库工作流终极进化-graphify知识图谱保姆级教程!代码库编译成知识图谱,支持claude-co
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest | 2026-06-18-202606181656_00001-practical-tips-on-how-to-use-claudecode-by-boris-cherny-2-3-4-5-6-7-8-9-10-11
- Type: entities
- Categories: ai

## [2026-06-23 12:31:33] ingest_batch | Processed: 103 notes; Trashed (low-quality): 1 notes
- Created: concepts/2026-06-18-202606180943_00002-post-from-朱學恒的萬事通事務所, concepts/2026-06-16-202606162119_00001-bellataiwan-bella儂儂-on-instagram-儂儂旅社-坐落於台南安平四草大道旁,全新度假村「逸點亦, concepts/2026-06-17-202606170036_00001-新北北海岸不輸國外海島!-天人菊盛開打造橘紅色海岸線, concepts/2026-06-16-202606161617_00001-l.facebook.com-l.php-u=https%3a%2f%2fduringmyjourney.com%2fx, concepts/2026-06-16-202606161425_00001-glasp.co (+98 more)
- Trashed: Tech/2026-06-17-202606170857_00001-local-ai-is-finally-usable!-real-world-workflows-on-a-5-year.md
