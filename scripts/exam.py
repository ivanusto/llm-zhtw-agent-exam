#!/usr/bin/env python3
"""繁中十題 + 工具呼叫十輪 + 多步 agent 三題 + 速度。評分一律用可機器判定的客觀標準，不用主觀印象。"""
import json,re,sys,time
from common import (AskError,Client,base_parser,emit,first_json,fmt_spread,load_bank,spread,
                    zh_leak,SIMP,ZH_RULER)

p=base_parser(__doc__)
p.add_argument("--repeats",type=int,default=1,
               help="整份考卷跑幾輪，報中位數與全距。vLLM 上 temperature=0 不保證可重現，正式比較建議 4")
p.add_argument("--no-speed",action="store_true",help="跳過速度量測")
a=p.parse_args()
# 一定要關思考模式：思考內容若混進 content 欄位，模型思考時用簡體中文，會讓「繁體用字」這項判準失真。
# 開關名稱各家不同，送錯會讓某些 chat template 丟例外，所以用 --ctk 換，或給 '{}' 改在伺服器端關。
C=Client(a,{"enable_thinking":False})
ZH=load_bank("zh10.json"); TOOLS=load_bank("tools.json"); AG=load_bank("agent.json")

def ask(q,maxtok=250):
    try: return C.ask(q,maxtok)[0],""
    except AskError as e: return "",f"請求失敗 {e}"

# ---- 一、繁中十題（客觀判準：繁體、含關鍵字、題目自己要求的格式）----
END="。！？!?"
def fmt_ok(t,chk):
    """題目裡寫明的格式要求。v1 只比關鍵字，「少於五十個字」「一句話」都沒驗。"""
    bare=re.sub(r"[*`]","",t).strip()
    if chk.get("one_sentence"):
        s=bare.rstrip(END)
        if "\n" in s or any(c in s for c in END): return False,"不是一句話"
    if "numbered_lines" in chk:
        nums=[m.group(1) for l in bare.splitlines() if (m:=re.match(r"\s*(\d+)\.",l))]
        if nums!=[str(i+1) for i in range(chk["numbered_lines"])]: return False,f"編號行 {nums}"
    if "max_chars" in chk:
        n=len(re.sub(r"\s","",bare))
        if n>chk["max_chars"]: return False,f"{n} 字超過上限 {chk['max_chars']}"
    if "fullmatch" in chk and not re.fullmatch(chk["fullmatch"],bare):
        return False,"多了數字與單位以外的內容"
    if "num_range" in chk:
        lo,hi=chk["num_range"]; xs=[float(x) for x in re.findall(r"\d+(?:\.\d+)?",bare)]
        if not xs or not all(lo<=x<=hi for x in xs): return False,f"數值 {xs} 不在 {lo}–{hi}"
    return True,""

def run_zh():
    det=[]
    for it in ZH:
        t,err=ask(it["q"])
        ks=[k.lower() in t.lower() for k in it["keywords"]]
        # 「任一即可」由題庫的 match 欄位明寫，不靠關鍵字內容去猜（v1 那個 bug 的教訓，見 results/day14.md）
        ok_k=bool(t) and (any(ks) if it.get("match")=="any" else all(ks))
        ok_f,why=fmt_ok(t,it.get("check",{})) if t else (False,err)
        leak=zh_leak(t)
        det.append({"q":it["q"][:26],"keyword":ok_k,"format":ok_f,"traditional":bool(t) and leak==0,
                    "simp_leak":leak,"leak_chars":"".join(c for c in t if c in SIMP),"why":why,"ans":t[:90]})
    # 每題兩分：關鍵字與格式都對得一分，全文無簡體字再得一分，滿分維持 20
    score=sum(int(d["keyword"] and d["format"])+int(d["traditional"]) for d in det)
    return score,det

# ---- 二、工具呼叫十輪（客觀判準：合法 JSON、欄位名、型別、值都要對）----
def run_tools():
    det=[]
    for it in TOOLS["tasks"]:
        out,err=ask(TOOLS["prefix"]+it["task"])
        ok=False; strict=False; why=err
        obj=first_json(out)
        if obj:
            try:
                j=json.loads(obj); args=j.get("arguments")
                if j.get("name")!="search_files": why=f"name={j.get('name')}"
                elif not isinstance(args,dict): why=f"沒有 arguments 物件，鍵為 {list(j)[:4]}"
                elif not {"dir","pattern","max_results"}<=set(args): why=f"欄位不全 {list(args)[:4]}"
                # type() 而非 isinstance()：bool 是 int 的子類別，v1 會讓 "max_results": true 通過
                elif type(args["max_results"]) is not int: why=f"max_results 型別 {type(args['max_results']).__name__}"
                elif args["max_results"]!=it["max_results"]: why=f"max_results={args['max_results']}"
                elif str(args["dir"]).rstrip("/") not in it["dir"]: why=f"dir={args['dir']}"
                else: ok=True
            except Exception as e: why=f"JSON 解析失敗 {type(e).__name__}"
        elif not err: why="找不到 JSON"
        if ok:
            # 提示要求不要有其他文字或 markdown 標記：整段回應本身就是那個 JSON 才算 strict
            try: strict=json.loads(out)==json.loads(obj)
            except Exception: strict=False
        det.append({"task":it["task"][:22],"ok":ok,"strict":strict,"why":why,"raw":out[:110]})
    return sum(d["ok"] for d in det),sum(d["strict"] for d in det),det

# ---- 三、多步 agent 三題（客觀判準：三個步驟都出現且順序正確）----
# v2：題目列出工具的順序刻意打亂。v1 列出順序就是正確答案，照抄題目即可滿分。
def run_agent():
    det=[]
    for it in AG:
        out,err=ask(it["q"]); seq=it["seq"]; low=out.lower()
        pos=[low.find(s) for s in seq]
        ok=bool(out) and all(p>=0 for p in pos) and pos==sorted(pos)
        # strict：題目要求「一行一個，不要解釋」，去掉編號與符號後每一行都只能是工具名稱
        lines=[re.sub(r"^\s*(?:\d+[.)、]|[-*•])?\s*|[`*\s]","",l) for l in out.splitlines()]
        strict=ok and [l for l in lines if l]==seq
        det.append({"ok":ok,"strict":strict,"why":err,"out":out[:130]})
    return sum(d["ok"] for d in det),sum(d["strict"] for d in det),det

runs=[]
for r in range(a.repeats):
    if a.repeats>1: print(f"== 第 {r+1}/{a.repeats} 輪",flush=True)
    zs,zd=run_zh()
    kw=sum(d["keyword"] for d in zd); fm=sum(d["format"] for d in zd)
    tr=sum(d["traditional"] for d in zd); lk=sum(d["simp_leak"] for d in zd)
    print(f"  繁中十題：{zs}/20（關鍵字 {kw}/10、格式 {fm}/10、純繁體 {tr}/10），簡體字洩漏共 {lk} 個",flush=True)
    to,ts,td=run_tools()
    print(f"  工具呼叫十輪：{to}/10 正確，其中 {ts}/10 是不帶任何包裝的裸 JSON",flush=True)
    ao,ast,ad=run_agent()
    print(f"  多步 agent 三題：{ao}/3 順序正確，其中 {ast}/3 只列工具名稱",flush=True)
    nerr=sum(d["why"].startswith("請求失敗") for d in zd+td+ad)
    if nerr: print(f"  另有 {nerr} 題請求失敗，以 0 分計；分數不代表模型能力，請先檢查端點",flush=True)
    runs.append({"zh":zs,"zh_format":fm,"simp_leak":lk,"tool":to,"tool_strict":ts,"agent":ao,
                 "agent_strict":ast,"zh_detail":zd,"tool_detail":td,"agent_detail":ad})

summary={k:spread([x[k] for x in runs]) for k in
         ("zh","zh_format","simp_leak","tool","tool_strict","agent","agent_strict")}
if a.repeats>1:
    s=summary
    print(f"  {a.repeats} 輪中位數（最小–最大）：繁中 {fmt_spread(s['zh'])}/20、洩漏 {fmt_spread(s['simp_leak'])}、"
          f"工具 {fmt_spread(s['tool'])}/10、agent {fmt_spread(s['agent'])}/3")

speed=None
if not a.no_speed:
    sp=[]
    for i in range(3):
        try: sp.append(C.speed(f"Explain memory bandwidth limits in LLM inference. (id {i}-{time.time_ns()})"))
        except Exception as e: print(f"  速度量測失敗：{type(e).__name__}: {e}"); break
    if sp:
        speed={k:spread([x[k] for x in sp])["median"] for k in ("ttft_s","decode_tps","e2e_tps")}
        speed["token_count"]=sp[0]["token_count"]
        print(f"  速度（三次中位數）：decode {speed['decode_tps']:.2f} tok/s、"
              f"TTFT {speed['ttft_s']*1000:.0f} ms、端到端 {speed['e2e_tps']:.2f} tok/s")

emit({"label":a.label,"model":a.model,"scoring":"v2","zh_ruler":ZH_RULER,"ctk":C.ctk,
      "repeats":a.repeats,"summary":summary,"speed":speed,"runs":runs},a.out)
