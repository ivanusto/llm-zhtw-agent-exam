# 工具呼叫十輪

只有一個工具，換十個任務。提示詞前綴：

```
你可以呼叫這個工具：
{"name":"search_files","parameters":{"dir":"string","pattern":"string","max_results":"integer"}}
請只輸出一個 JSON 物件，格式為 {"name":..., "arguments":{...}}，不要有任何其他文字或 markdown 標記。

任務：
```

## 十個任務

1. 在 /var/log 找出所有 .err 檔，最多 20 筆
2. 在 /home/user/docs 搜尋含 invoice 的檔案，最多 5 筆
3. 列出 /etc 底下的 .conf 檔，最多 100 筆
4. 在 /tmp 找 core dump，最多 3 筆
5. 在 /srv/www 找 index.html，只要 1 筆
6. 在 /opt 搜尋 *.tar.gz，最多 50 筆
7. 在 /data 找出 2026 開頭的 csv，最多 10 筆
8. 在 /mnt/backup 找 .sql 檔，最多 25 筆
9. 在 /usr/share 搜尋 licence 相關檔案，最多 15 筆
10. 在 /root 找 .ssh 設定檔，最多 2 筆

## 判準

四項全中才算一輪通過：

1. 回應裡抽得出 `{...}` 且能被 `json.loads` 解析
2. `name` 欄位等於 `search_files`
3. `dir`、`pattern`、`max_results` 三個欄位都在
4. `max_results` 的型別是整數，不是字串

第 4 項是這題真正的鑑別度所在。很多模型會回 `"max_results": "20"`。
