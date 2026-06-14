---
title: 2026-06-11-202606111253_00001-how-to-build-a-multi-agent-workflow-for-llm-wikis-in-hermes
created: 2026-06-14
updated: 2026-06-14
type: entity
tags: ["tech"]
sources: ["/Users/dannytsao/Documents/PersonalKM/raw/Tech/2026-06-11-202606111253_00001-how-to-build-a-multi-agent-workflow-for-llm-wikis-in-hermes.md"]
confidence: medium
---# How to Build a Multi-Agent Workflow for LLM Wikis in Hermes Kanban

## 摘要
1. 本文介紹如何利用Hermes Kanban建立多代理工作流程，用於維護和更新LLM維基知識庫，以確保資訊準確且持續更新。
2. 這個流程包含scouts、orchestrator、ingesttor等角色，透過自動化監測、審核與整理，協助清理過時資料並保持知識庫的精準與可管理性。

## 重點
- 1. 本文介紹如何利用Hermes Kanban建立多代理工作流程，用於維護和更新LLM維基知識庫，以確保資訊準確且持續更新。
2. 這個流程包含scouts、orchestrator、ingesttor等角色，透過自動化監測、審核與整理，協助清理過時資料並保持知識庫的精準與可管理性。

## 原始內容
So, I did a video last week showing you how to build a multi- aent framework in Hermes agent using their combon board. And the example I did uh for that one was about doing research on pain points for agent users and then either building a tool or creating materials for a video about that topic. So, that's a useful workflow for me, but it might be a little bit specific for people out there. So, I wanted to do another video, kind of a follow-up and another example of a multi- aent workflow. This one, I think, is more generally uh applicable. It's going to be for maintaining and updating uh an LLM wiki, also called a knowledge base uh in the Carpathy style. You can watch some of my videos about that if you want to learn exactly what the structure is. I'm not going to go into that that much, but you can watch those videos. But in this one, I'm going to kind of break down what the structure is, what the design of the workflow is going to be. And then in this one, I'm actually show you building from the template. This is my Hermes multi-agent workflow template. It's open sourced on Tobi Studio GitHub. You can use use it yourself. I'm going to show you exactly starting from this template what needs to be changed and exactly how I built uh this workflow out. So, it's going to be a more hands-on demo so you can kind of see how this can actually be made quite easily by yourself. So, let's get started. And if you like this video, please consider supporting the channel by joining Team Garage, which will give you early access to videos or Team Garage Max, where you will get exclusive videos each week, as well as many other perks. I'd like to continue providing as much free valuable content as possible, as well as better experiments on different hardware. So, these memberships will really make it possible. So, this is the idea, and it's fairly straightforward. This was my idea. Um, I have a lot of these now, these, uh, LLM wikis. Here's an example. This is my Hermes agent one, and this is in Obsidian. I've been building a lot of these for kind of long range projects that I have. I found it extremely useful instead of, you know, asking my agent to drive all this information every single time I want to work on a certain topic, just to build this one knowledge base once, have it update it from time to time, and it really gives me very detailed answers to questions I have. I've just found it's very much more accurate answers. It's a lot quicker. There's no hallucinating. There's no kind of obsolete information included, especially for something like Hermes Agent that is constantly evolving. Like literally every day, it seems there's an update about it. So something like this, you really need to have the most updated information. And I use this knowledge base for a lot of my videos for the full master class. It's really become essential. And it's organized. It has raw sources up here. And the raw source sources are a lot of it's from the official docs of Hermes agent um from new research but it also includes all the you know change logs all the information from their GitHub and a lot of community resources as well. Uh there's a lot of really good community resources about information about Hermes agent, other plugins, skills, MCP servers, integrations, and it pulls kind of like got answers to very detailed specific questions. And that's all compiled in this raw folder. But then I organized it into a wiki as you would do in a a knowledge base. Like if you

...（內容已截斷）

## 內含連結
- https://youtu.be/hbKvO5MWq08

## 媒體
- 未擷取

## 擷取狀態
- 平台：youtube
- 類型：video
- 擷取狀態：ok
- 需要人工確認：否

## 原文連結
https://youtu.be/hbKvO5MWq08

