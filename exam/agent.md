# 多步 agent 三題

## 第 1 題

```
你有 list_dir、read_file、write_file 三個工具。任務：找出 /project 底下最大的 .log 檔，讀它的最後 100 行，把摘要寫進 /project/summary.txt。請只列出你會依序呼叫的工具名稱，一行一個，不要解釋。
```

正確順序：`list_dir` 到 `read_file` 到 `write_file`

## 第 2 題

```
你有 http_get、parse_json、write_file 三個工具。任務：抓 https://example.invalid/api/stats，取出 total 欄位，存成 /tmp/total.txt。請只列出你會依序呼叫的工具名稱，一行一個，不要解釋。
```

正確順序：`http_get` 到 `parse_json` 到 `write_file`

## 第 3 題

```
你有 run_sql、format_table、send_email 三個工具。任務：查上季營收前十名客戶，排版成表格，寄給 finance@example.invalid。請只列出你會依序呼叫的工具名稱，一行一個，不要解釋。
```

正確順序：`run_sql` 到 `format_table` 到 `send_email`

## 判準

三個工具名稱都要出現，而且在輸出中的先後位置必須是正確順序。

只比對名稱與順序，不要求模型真的執行。這樣同一題可以考任何模型，
不管它支不支援原生 tool calling，也不需要架設真的工具。
