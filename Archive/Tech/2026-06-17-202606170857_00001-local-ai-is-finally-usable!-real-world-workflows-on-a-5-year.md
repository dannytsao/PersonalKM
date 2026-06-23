---
tags: [技術]
source: LINE
date: 2026-06-17
log_id: 202606170857_00001
url: https://youtu.be/uOHI47l215U
platform: youtube
content_type: video
extraction_status: ok
needs_review: false
needs_local_worker: false
worker_status: done
worker_type: omnichannel_md
worker_retry_count: 0
summary: 1. 作者在五年前的MacBook Pro上成功運行Google Gemma本地AI模型，260億參數的模型能快速處理文章摘要與自動化任務，表現遠超以往本地模型的局限。 2. 透過MLX Studio工具，Gemma模型不僅能處理文本，還可識別圖像內容，例如準確辨識照片中的太空梭型號，展現本地AI在圖像分析上的應用潛力。
status: unread
worker_error: ""
worker_processed_at: 2026-06-17T09:27:17+08:00
worker_name: mac-mini-omnichannel
---
# Local AI is Finally Usable! Real-World Workflows on a 5-Year-Old Mac with Google Gemma

## 摘要
1. 作者在五年前的MacBook Pro上成功運行Google Gemma本地AI模型，260億參數的模型能快速處理文章摘要與自動化任務，表現遠超以往本地模型的局限。
2. 透過MLX Studio工具，Gemma模型不僅能處理文本，還可識別圖像內容，例如準確辨識照片中的太空梭型號，展現本地AI在圖像分析上的應用潛力。

## 重點
- 1. 作者在五年前的MacBook Pro上成功運行Google Gemma本地AI模型，260億參數的模型能快速處理文章摘要與自動化任務，表現遠超以往本地模型的局限。
2. 透過MLX Studio工具，Gemma模型不僅能處理文本，還可識別圖像內容，例如準確辨識照片中的太空梭型號，展現本地AI在圖像分析上的應用潛力。

## 原始內容
(upbeat music) Hey, everybody, it's Lon. So I've been downloading local AI models for the last couple of years now to see if I can do anything useful with them. And typically they fizzle out when I have them work on some of my automation tasks or even do simple summarization of articles, for example. But lately, things have been getting a lot better. And the other day, I downloaded a new version of Gemma that is optimized to work with the Mac. This is one of their MLX models. And I am going to have this right now, summarize a transcript from one of my recent videos here. And I'm just gonna drop in that transcript. I've given it a prompt here that you can see. I'm using an app called Studio MLX to get this model going. And I'm gonna drop all this stuff in. And what's been impressive to me is not only how fast this model is. Certainly it's a little bit slower than what you might get through a cloud interface. But for a locally running interface here, it is super quick. So if we look here, this is the 26 billion parameter model running on this MacBook Pro here. And I'm pulling about 50 or so tokens per second. And right now it's going through its thinking process. And now it is generating the summary of the video that I uploaded on Saturday. And a lot of times when I do this with a local model, it gives up, it doesn't give me a comprehensive summary here. But now look at it. It's giving me a really good article here that summarizes what that entire video was about. And it seems like it's sticking to the script and not going off in some crazy direction as these models have tended to do in the past. So this is really cool. And what I thought I would do in this video is show you some examples of this model running on this MacBook and also see if we can tie it into my N8N automation server to have it do some more advanced things that I'm typically relying on the cloud to do. The Mac I'm running with here is pretty old by computer standards. I bought this in November of '21. This is a MacBook with an M1 Macs and 32 gigabytes of RAM. The reason why Macs are so coveted in the local AI space lately is because they have a lot of unified memory that can tie right into the GPU at very high speeds. And when you've got a model that's optimized for the Mac, as you can see, it can crank out text very quickly, even with larger models. So what I did is I downloaded the biggest model I could fit in memory here. And that is what we're running with now. So we're going to dive into this in more detail in just a second. But I do want to let you know in the interest the full disclosure, this is not a sponsored video. I don't make any money doing AI tutorials or any kind of courses or anything. I am just a casual user that likes to find tools that are turn key. And this is certainly getting close to that point. So without further ado, let's dive in and see what else this Gemma model can do running on my MacBook Pro. Now, as I mentioned in the intro, I think I mispronounced it, but we're using MLX Studio here on my Mac. I found this to be a very effective front end for optimized models that will work the best on Apple Silicon. On Windows and on Linux, there are also other options. You could use Olama, for example, or LM Studio. There's a lot of options out there for front ends. So again, on the Mac, I think this one works pretty well at the moment. And I'm sure a lot of you may have some other suggestions. Now, to find a model, what you do is go over to the server

...（內容已截斷）

## 內含連結
- https://youtu.be/uOHI47l215U

## 媒體
- 未擷取

## 擷取狀態
- 平台：youtube
- 類型：video
- 擷取狀態：ok
- 需要人工確認：否

## 原文連結
https://youtu.be/uOHI47l215U
