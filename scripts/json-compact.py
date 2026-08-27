#!/usr/bin/env python3
"""JSON 緊湊度十輪測試。附錄二那道題的腳本化版本。

判準：把回應裡第一個 JSON 物件抓出來，物件本身含換行就算 pretty-print，
否則算單行緊湊。另記平均輸出字元數（去掉前後空白，含 markdown 圍籬才算數，
因為在 agent 迴圈裡那些字元一樣要付 token）。

取樣不能用 temperature=0：貪婪解碼下十輪必然一模一樣，比數只會是 0/10 或 10/10。
所以這裡用各家 instruct 模式的建議取樣，並把設定一起寫進結果，
引用比數時必須連取樣設定一起報。
"""
import json,re,sys,time,urllib.request,statistics

B=sys.argv[1]; M=sys.argv[2]; LABEL=sys.argv[3]
TEMP=float(sys.argv[4]) if len(sys.argv)>4 else 0.7
TOPP=float(sys.argv[5]) if len(sys.argv)>5 else 0.80
ROUNDS=10
# 這顆的 chat template 只認 xhigh/medium/low，送 reasoning_effort:"none" 會丟 Jinja 例外
# （unsloth 文件列了 none 但模板不支援）。關思考改在伺服器層級用 -rea off，
# 所以這裡不送任何 chat_template_kwargs。
CTK={}

PROMPT=("只輸出一個 JSON 物件，不要有任何其他文字、說明或程式碼區塊標記。\n"
        "物件需包含 host、status、latency_ms 三個欄位，\n"
        '值分別為 "nas-01"、"online"、23。')

def ask(msg):
    d=json.load(urllib.request.urlopen(urllib.request.Request(B+"/v1/chat/completions",method="POST",
      data=json.dumps({"model":M,"messages":[{"role":"user","content":msg}],
        "max_tokens":300,"temperature":TEMP,"top_p":TOPP,"top_k":20,
        "chat_template_kwargs":CTK}).encode(),
      headers={"Content-Type":"application/json"}),timeout=900))
    ch=d["choices"][0]["message"]
    return (ch.get("content") or "").strip()

rows=[]; pretty=0; valid=0
for i in range(ROUNDS):
    out=ask(PROMPT)
    m=re.search(r'\{.*\}', out, re.S)
    obj=m.group(0) if m else ""
    is_pretty=("\n" in obj)
    ok=False
    if obj:
        try:
            j=json.loads(obj)
            ok=(j.get("host")=="nas-01" and j.get("status")=="online" and j.get("latency_ms")==23)
        except Exception: ok=False
    pretty+=int(is_pretty); valid+=int(ok)
    rows.append({"round":i+1,"pretty":is_pretty,"fields_ok":ok,"chars":len(out),"raw":out[:160]})
    print(f"  #{i+1:2d} {'多行' if is_pretty else '單行'}  欄位{'正確' if ok else '不符'}  {len(out):4d} 字元  {out[:60]!r}",flush=True)

avg=statistics.mean(r["chars"] for r in rows)
print(f"  {LABEL}：多行 pretty-print {pretty}/{ROUNDS}、單行緊湊 {ROUNDS-pretty}/{ROUNDS}、"
      f"欄位正確 {valid}/{ROUNDS}、平均輸出 {avg:.0f} 字元（temp={TEMP} top_p={TOPP}）")
print(json.dumps({"label":LABEL,"rounds":ROUNDS,"pretty":pretty,"compact":ROUNDS-pretty,
                  "fields_ok":valid,"avg_chars":avg,"temp":TEMP,"top_p":TOPP,
                  "detail":rows},ensure_ascii=False))
