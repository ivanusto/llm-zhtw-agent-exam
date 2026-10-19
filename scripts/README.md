# 執行方式

兩支腳本都只需要一個 OpenAI 相容的 `/v1/chat/completions` 端點，
不依賴任何特定引擎，vLLM、llama.cpp 的 llama-server、SGLang 或雲端 API 都可以。
除了標準函式庫之外沒有相依套件，需要 Python 3.8 以上。

```bash
# 主考卷：繁中十題 + 工具呼叫十輪 + 多步 agent 三題 + 速度
python3 exam.py http://127.0.0.1:8000 <model-name> <label> [--repeats 4]

# JSON 緊湊度，預設 50 輪、每 10 輪一組
python3 json-compact.py http://127.0.0.1:8000 <model-name> <label> [temp] [top_p] [--rounds 50]
```

兩支都會先印人類可讀的逐題結果，最後一行印一個完整的 JSON，
方便接後續處理；加 `--out result.json` 會另存一份。`-h` 列出全部參數。

## 共用參數

| 參數 | 用途 |
|---|---|
| `--api-key` | Bearer 金鑰，預設讀環境變數 `OPENAI_API_KEY` |
| `--ctk '{json}'` | 送出的 `chat_template_kwargs`；給 `'{}'` 就完全不送 |
| `--retries 3` | 逾時、連線錯誤、HTTP 429 與 5xx 的重試次數。用盡後該題記為失敗，整輪不中斷 |
| `--timeout 900` | 單一請求逾時秒數 |
| `--out` | 另把最後的 JSON 寫進檔案 |

端點網址結尾的 `/v1` 可有可無。

## 雲端 API

OpenAI 等官方 API 會把 `chat_template_kwargs` 與 `top_k` 當成未知參數拒絕，
所以要關掉這兩個欄位：

```bash
export OPENAI_API_KEY=...
python3 exam.py         https://api.openai.com <model> <label> --ctk '{}'
python3 json-compact.py https://api.openai.com <model> <label> --ctk '{}' --no-top-k
```

## 關思考模式

繁中判準會被思考內容汙染：多數模型思考時用簡體中文，
如果思考內容混進 `content` 欄位，「繁體用字」這一項就失真了。

`exam.py` 預設送 `chat_template_kwargs: {"enable_thinking": false}`，
但**不同模型的開關名稱不一樣**，而且送錯會讓某些 chat template 直接丟例外。實測過的兩種：

- Qwen3.8-27B 系列：`{"enable_thinking": false}`（預設值）
- Qwen3.8-Flash-Next：`reasoning_effort` 只接受 `xhigh` / `medium` / `low`，
  送 `none` 會丟 Jinja 例外。這一顆要改在伺服器層級關，
  llama-server 用 `-rea off`，腳本這邊給 `--ctk '{}'`。

`json-compact.py` 預設不送任何 `chat_template_kwargs`，需要時同樣用 `--ctk` 指定。

## 取樣設定與重複次數

前三項用 `temperature=0`，判準是二元通過制。但 **`temperature=0` 不保證可重現**：
Day 15 在 vLLM 上同一題連跑六次得到六種輸出
（連續批次改變批次組成，MoE 路由與 kernel 歸約順序跟著變）。
所以正式比較請用 `--repeats 4`，報中位數與全距，不要只引用單次結果。

`json-compact.py` **不能**用貪婪解碼：每輪必然一模一樣，
比數只會是全有或全無，量不出格式偏好的分佈。
預設用 `temp=0.7 / top_p=0.80 / top_k=20`，並把設定寫進輸出的 JSON。
引用比數時請連取樣設定一起報，否則數字無法比較。

預設 50 輪、每 10 輪一組並報每組的全距。Day 15 量到每十輪的散布可達 2–7，
十輪分得開 0 與 5，分不開 5 與 7。

每輪會送不同的 `seed`（第 i 輪是 `--seed` 加 i，預設從 0 開始）。有些引擎沒收到 seed 時
用固定的預設值，例如 TensorFold：temp 0.7 下 50 輪會逐字相同，等於只抽了一個樣本。
逐輪遞增的 seed 讓各輪不同，同一組 seed 重跑又能重現。不接受 seed 的端點用 `--no-seed`。
腳本會報「幾種不同輸出」，只有一種時會提醒，怎麼分辨原因見
[results/v2-2026-10-20.md](../results/v2-2026-10-20.md)。

## 速度

`exam.py` 最後用串流請求量三次取中位數，分開報：

- `decode_tps`：第一個 token 之後的純解碼速率
- `ttft_s`：首個 token 延遲，主要是 prefill
- `e2e_tps`：輸出 token 數除以總時間，相當於 v1 報的「decode」，會把 prefill 算進去

token 數優先用伺服器在串流結尾回報的 `usage`；伺服器不支援 `stream_options` 時改數內容區塊，
輸出的 `token_count` 欄位會標明是哪一種。用 `--no-speed` 跳過。
