```dataview
TABLE tags AS "主題", status AS "狀態", file.ctime AS "收集時間"
FROM "wiki"
WHERE type = "youtube" AND status = "待閱讀"
SORT file.ctime DESC
```