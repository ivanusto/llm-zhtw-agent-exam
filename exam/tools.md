# 工具呼叫十輪

只有一個工具，換十個任務。提示詞前綴：

```
你可以呼叫這個工具：
{"name":"search_files","parameters":{"dir":"string","pattern":"string","max_results":"integer"}}
請只輸出一個 JSON 物件，格式為 {"name":..., "arguments":{...}}，不要有任何其他文字或 markdown 標記。

任務：
```

## 十個任務

| # | 任務 | 期望 `dir` | 期望 `max_results` |
|---|---|---|---|
| 1 | 在 /var/log 找出所有 .err 檔，最多 20 筆 | `/var/log` | 20 |
| 2 | 在 /home/user/docs 搜尋含 invoice 的檔案，最多 5 筆 | `/home/user/docs` | 5 |
| 3 | 列出 /etc 底下的 .conf 檔，最多 100 筆 | `/etc` | 100 |
| 4 | 在 /tmp 找 core dump，最多 3 筆 | `/tmp` | 3 |
| 5 | 在 /srv/www 找 index.html，只要 1 筆 | `/srv/www` | 1 |
| 6 | 在 /opt 搜尋 *.tar.gz，最多 50 筆 | `/opt` | 50 |
| 7 | 在 /data 找出 2026 開頭的 csv，最多 10 筆 | `/data` | 10 |
| 8 | 在 /mnt/backup 找 .sql 檔，最多 25 筆 | `/mnt/backup` | 25 |
| 9 | 在 /usr/share 搜尋 licence 相關檔案，最多 15 筆 | `/usr/share` | 15 |
| 10 | 在 /root 找 .ssh 設定檔，最多 2 筆 | `/root` 或 `/root/.ssh` | 2 |

## 判準

全部符合才算一輪通過：

1. 回應裡抽得出 `{...}` 且能被 `json.loads` 解析
2. `name` 欄位等於 `search_files`
3. 參數放在 `arguments` 物件裡（v1 也接受 `parameters`，v2 只認提示指定的 `arguments`）
4. `dir`、`pattern`、`max_results` 三個欄位都在
5. `max_results` 的型別是整數，不是字串，也不是布林值
6. `max_results` 等於任務要求的筆數，`dir` 等於任務指定的目錄（結尾斜線不計）

`pattern` 的寫法太多種（`*.err`、`.err`、正規表示式），不比對。

第 5 項是這題原本的鑑別度所在，很多模型會回 `"max_results": "20"`。
Python 的 `bool` 是 `int` 的子類別，v1 用 `isinstance` 判斷，`true` 會被當成整數放行。

另報一個**裸 JSON** 比數：通過的回應裡，整段輸出本身就是那個 JSON 物件
（沒有 markdown 圍籬、沒有前後說明）。提示明說不要有其他文字或 markdown 標記，
這一項量的就是這句話有沒有被聽進去。它不影響 10 分的主分數。
