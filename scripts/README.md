# 執行方式

兩支腳本都只需要一個 OpenAI 相容的 `/v1/chat/completions` 端點，
不依賴任何特定引擎，vLLM、llama.cpp 的 llama-server、SGLang、
或任何雲端 API 都可以。除了標準函式庫之外沒有相依套件。

```bash
# 主考卷：繁中十題 + 工具呼叫十輪 + 多步 agent 三題 + decode
python3 exam.py http://127.0.0.1:8000 <model-name> <label>

# JSON 緊湊度十輪
python3 json-compact.py http://127.0.0.1:8000 <model-name> <label> [temp] [top_p]
```

兩支都會先印人類可讀的逐題結果，最後一行印一個完整的 JSON，
方便接後續處理。

## 關思考模式

繁中判準會被思考內容汙染：多數模型思考時用簡體中文，
如果思考內容混進 `content` 欄位，「繁體用字」這一項就失真了。

`exam.py` 送的是 `chat_template_kwargs`，但**不同模型的開關名稱不一樣**，
而且送錯會讓某些 chat template 直接丟例外。實測過的兩種：

- Qwen3.8-27B 系列：`{"enable_thinking": false}`
- Qwen3.8-Flash-Next：`reasoning_effort` 只接受 `xhigh` / `medium` / `low`，
  送 `none` 會丟 Jinja 例外。這一顆要改在伺服器層級關，
  llama-server 用 `-rea off`。

所以 `CTK` 那個常數請照你的模型調整，或乾脆留空 `{}` 並在伺服器端關。

## 取樣設定

前四項用 `temperature=0`，因為判準是二元通過制，要的是可重現。

`json-compact.py` **不能**用貪婪解碼：十輪必然一模一樣，
比數只會是 0/10 或 10/10，量不出格式偏好的分佈。
預設用 `temp=0.7 / top_p=0.80`，並把設定寫進輸出的 JSON。
引用比數時請連取樣設定一起報，否則數字無法比較。
