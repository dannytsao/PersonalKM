---
tags:
  - tech
  - hermes
  - Claude
  - gemma4
source: LINE
date: 2026-06-17
log_id: 202606170659_00001
url: https://youtu.be/sD7ZgcjAV90
platform: youtube
content_type: video
extraction_status: ok
needs_review: false
needs_local_worker: false
worker_status: done
worker_type: omnichannel_md
worker_retry_count: 0
summary: 本視頻展示如何透過Claude code工具安裝Hermi's agent並整合至Gemma 4模型，以建立AI助手，過程中利用CLI指令自動化設置，避免手動配置的複雜性。 內容進一步探討硬體配置與模型選擇，強調需確保Mac mini持續運行以維持Hermi's agent的即時性，並建議根據使用情境測試不同模型（如Gemma 412B與QAT版本）的效能差異。
status: unread
worker_error: ""
worker_processed_at: 2026-06-17T07:08:53+08:00
worker_name: mac-mini-omnichannel
---
# Gemma 4 12B + Hermes Agent: Build Your Own AI Assistant

## 摘要
本視頻展示如何透過Claude code工具安裝Hermi's agent並整合至Gemma 4模型，以建立AI助手，過程中利用CLI指令自動化設置，避免手動配置的複雜性。
內容進一步探討硬體配置與模型選擇，強調需確保Mac mini持續運行以維持Hermi's agent的即時性，並建議根據使用情境測試不同模型（如Gemma 412B與QAT版本）的效能差異。

## 重點
- 本視頻展示如何透過Claude code工具安裝Hermi's agent並整合至Gemma 4模型，以建立AI助手，過程中利用CLI指令自動化設置，避免手動配置的複雜性。
內容進一步探討硬體配置與模型選擇，強調需確保Mac mini持續運行以維持Hermi's agent的即時性，並建議根據使用情境測試不同模型（如Gemma 412B與QAT版本）的效能差異。

## 原始內容
In our last video, we installed Gemma 4 onto this 16-gig Mac mini, and in this video, I want to take things a step further, and I want to install Hermi's agent and plug it into the Gemma 4 model so that we can build our first AI assistant. Okay, so let's start by opening up our favorite coding tool, and I want to be using Claude code in the Claude desktop app. I'll set myself to Opus 4.8, and I'll just go to Ultra code, and you can just use this as a bench mark for what's possible. But we'll be using Claude code to do everything for us. We'll be using it to help change the settings on our Mac. We'll then be using it to install Hermi's agent, to plug it into our Gemma model. We'll also be using it to build out any dashboards or workflows. The better the model that you have, the better the output you can get. You just want like a really, really smart person setting all this stuff up for you. So one of the reasons why we're able to manage everything on a computer is because all these coding tools run in the terminal. If they run in the terminal, they have access to your device. They can read your device and tell you what, you know, what RAM you have available. They can change the settings for you. And a lot of these tools and apps that you download, like as we know with Hermi's agent, they have a install line here. So our Claude can actually just go to the website, find this install line, and then automatically run that in a terminal. It then help us set up everything without us actually having to go to the very tedious and sometimes confusing process of setting up a Hermi's agent. So once it installs this, a lot of these tools also have a CLI and a CLI is just a way that you can run, use, change settings of, for example, Hermi's directly in the terminal. So for example, let me just go to the LM Studio CLI. We have list your models. That's the command. And to run that, we just need to do LMS space Ls. So I've got, it's already open. I'm just going to go LMS space Ls. And I'm going to hit enter. And then we see all the different models that I've got available on my LM studio. And I'm actually using LM link, which means that across all my different devices, I can share the local models that I have. That's why you see like 20 models on here. As you can see, we can just operate under the hall. We can operate LM Studio. We can operate Hermi's agent. And we can do that directly from Claude code or codex or open code, whatever's got access to your terminal. So let's just start by running through a very basic command. Hey, can you let me know what hardware I'm running on this device? So we're just checking the max hardware details. And as you can see, it's just executing a command that runs in the terminal. Here we have an Mac mini with M4 chip. We have 16 gigs of RAM. The display that we have is a 1920 by 1080. So it can read everything that we have on a device. So the second thing you want to do before we even start installing any of these Hermi's agent is, hey, can you confirm if this Mac ever turns off or if it's set to always be on? And one of the reasons what you want to have this device to always be on is if if your Mac mini goes to sleep, your Hermi's agent goes to sleep. So if it's sleeping at 3 a.m. and you have like a really important email that you wanted your agent to get, it's not going to get it until it wakes up. So you want to have your Mac always on. So in this case, I think this Mac is always set to always be on. You can also do

...（內容已截斷）

## 內含連結
- https://youtu.be/sD7ZgcjAV90

## 媒體
- 未擷取

## 擷取狀態
- 平台：youtube
- 類型：video
- 擷取狀態：ok
- 需要人工確認：否

## 原文連結
https://youtu.be/sD7ZgcjAV90
