#!/usr/bin/env python3
"""JSON 緊湊度測試。

判準：把回應裡第一個 JSON 物件抓出來，物件本身含換行就算 pretty-print，
否則算單行緊湊。另記平均輸出字元數（去掉前後空白，含 markdown 圍籬才算數，
因為在 agent 迴圈裡那些字元一樣要付 token）。

取樣不能用 temperature=0：貪婪解碼下每輪必然一模一樣，比數只會是全有或全無。
所以這裡用各家 instruct 模式的建議取樣，並把設定一起寫進結果，
引用比數時必須連取樣設定一起報。

輪數預設 50（每 10 輪一組）：Day 15 量到每十輪的散布可達 2–7，十輪分得開 0 與 5，分不開 5 與 7。
"""
import json,statistics
from common import AskError,Client,base_parser,emit,first_json,load_bank,spread

p=base_parser(__doc__.splitlines()[0])
p.add_argument("temp",nargs="?",type=float,default=0.7)
p.add_argument("top_p",nargs="?",type=float,default=0.80)
p.add_argument("--top-k",type=int,default=20)
p.add_argument("--no-top-k",action="store_true",help="不送 top_k（OpenAI 等官方 API 不接受這個參數）")
p.add_argument("--rounds",type=int,default=50)
p.add_argument("--block",type=int,default=10,help="每幾輪算一組，報每組多行數的全距")
a=p.parse_args()
TOPK=None if a.no_top_k else a.top_k
# 預設不送 chat_template_kwargs：有些模板只認特定的 reasoning_effort 值，送錯直接丟 Jinja 例外，
# 關思考改在伺服器層級（例如 llama-server 的 -rea off）。需要時用 --ctk 指定。
C=Client(a,{})
BANK=load_bank("json-compact.json")

rows=[]
for i in range(a.rounds):
    try: out=C.ask(BANK["prompt"],300,a.temp,top_p=a.top_p,top_k=TOPK)[0]; err=""
    except AskError as e: out=""; err=str(e)
    obj=first_json(out)
    is_pretty=("\n" in obj)
    ok=False
    if obj:
        try: ok=json.loads(obj)==BANK["expect"]
        except Exception: ok=False
    rows.append({"round":i+1,"pretty":is_pretty,"fields_ok":ok,"chars":len(out),"error":err,"raw":out[:160]})
    print(f"  #{i+1:2d} {'多行' if is_pretty else '單行'}  欄位{'正確' if ok else '不符'}  {len(out):4d} 字元  "
          f"{(out[:60] if out else err[:60])!r}",flush=True)

ok_rows=[r for r in rows if not r["error"]]
pretty=sum(r["pretty"] for r in rows); valid=sum(r["fields_ok"] for r in rows)
fails=len(rows)-len(ok_rows)
avg=statistics.mean(r["chars"] for r in ok_rows) if ok_rows else 0
blocks=[sum(r["pretty"] for r in rows[j:j+a.block]) for j in range(0,a.rounds,a.block)]
bs=spread(blocks)
topk=f" top_k={TOPK}" if TOPK is not None else ""
print(f"  {a.label}：多行 pretty-print {pretty}/{a.rounds}、單行緊湊 {a.rounds-pretty-fails}/{a.rounds}、"
      f"欄位正確 {valid}/{a.rounds}、平均輸出 {avg:.0f} 字元（temp={a.temp} top_p={a.top_p}{topk}）")
if len(blocks)>1: print(f"  每 {a.block} 輪多行數：{blocks}，全距 {bs['min']}–{bs['max']}")
if fails: print(f"  另有 {fails} 輪請求失敗，不計入緊湊或多行")

emit({"label":a.label,"model":a.model,"scoring":"v2","rounds":a.rounds,"block":a.block,"pretty":pretty,
      "compact":a.rounds-pretty-fails,"failed":fails,"fields_ok":valid,"avg_chars":avg,
      "per_block":blocks,"block_min":bs["min"],"block_max":bs["max"],
      "temp":a.temp,"top_p":a.top_p,"top_k":TOPK,"ctk":C.ctk,"detail":rows},a.out)
