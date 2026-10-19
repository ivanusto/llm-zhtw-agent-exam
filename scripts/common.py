"""兩支腳本共用的端點呼叫、參數與判準工具。只用標準函式庫。"""
import argparse,json,os,re,sys,time,urllib.error,urllib.request
from pathlib import Path

BANK=Path(__file__).resolve().parent.parent/"exam"
def load_bank(name): return json.loads((BANK/name).read_text(encoding="utf-8"))

class AskError(Exception): pass

def base_parser(desc):
    p=argparse.ArgumentParser(description=desc)
    p.add_argument("base",help="端點根網址，例如 http://127.0.0.1:8000（結尾的 /v1 可有可無）")
    p.add_argument("model"); p.add_argument("label")
    p.add_argument("--api-key",default=os.environ.get("OPENAI_API_KEY",""),
                   help="Bearer 金鑰，預設讀 OPENAI_API_KEY")
    p.add_argument("--ctk",default=None,
                   help="chat_template_kwargs 的 JSON 字串；給 '{}' 就完全不送這個欄位（雲端 API 要這樣）")
    p.add_argument("--timeout",type=float,default=900)
    p.add_argument("--retries",type=int,default=3,help="逾時、連線錯誤、5xx 的重試次數")
    p.add_argument("--out",help="另把最後的 JSON 寫進這個檔案")
    return p

class Client:
    def __init__(self,a,ctk_default):
        b=a.base.rstrip("/")
        self.url=(b[:-3] if b.endswith("/v1") else b)+"/v1/chat/completions"
        self.model=a.model; self.key=a.api_key; self.timeout=a.timeout; self.retries=a.retries
        self.ctk=json.loads(a.ctk) if a.ctk is not None else ctk_default

    def _req(self,body):
        h={"Content-Type":"application/json"}
        if self.key: h["Authorization"]="Bearer "+self.key
        return urllib.request.Request(self.url,method="POST",headers=h,
                                      data=json.dumps(body).encode())

    def body(self,msg,maxtok,temp,**extra):
        # 非必要欄位一律不送：OpenAI 等官方 API 會把 top_k、chat_template_kwargs 當未知參數拒絕。
        d={"model":self.model,"messages":[{"role":"user","content":msg}],
           "max_tokens":maxtok,"temperature":temp}
        if self.ctk: d["chat_template_kwargs"]=self.ctk
        d.update({k:v for k,v in extra.items() if v is not None})
        return d

    def ask(self,msg,maxtok=300,temp=0.0,**extra):
        """回傳 (content, usage)。重試用盡才丟 AskError，由呼叫端記成該題失敗。"""
        err=None
        for i in range(self.retries+1):
            try:
                with urllib.request.urlopen(self._req(self.body(msg,maxtok,temp,**extra)),
                                            timeout=self.timeout) as r:
                    d=json.load(r)
                ch=d["choices"][0]["message"]
                return (ch.get("content") or "").strip(), d.get("usage") or {}
            except urllib.error.HTTPError as e:
                err=f"HTTP {e.code} {e.read()[:200].decode(errors='replace')}"
                if e.code<500 and e.code!=429: break      # 4xx 是請求本身有問題，重試沒用
            except (urllib.error.URLError,TimeoutError,OSError,ValueError,KeyError,IndexError) as e:
                err=f"{type(e).__name__}: {e}"
            if i<self.retries: time.sleep(2**i)
        raise AskError(err)

    def speed(self,msg,maxtok=300):
        """串流量測，拆開 TTFT 與純解碼速率。非串流的 tokens/總時間 會把 prefill 算進去。"""
        body=self.body(msg,maxtok,0.0,stream=True,stream_options={"include_usage":True})
        t0=time.perf_counter(); first=last=None; chunks=0; usage=None
        with urllib.request.urlopen(self._req(body),timeout=self.timeout) as r:
            for line in r:
                line=line.strip()
                if not line.startswith(b"data:"): continue
                data=line[5:].strip()
                if data==b"[DONE]": break
                ev=json.loads(data)
                if ev.get("usage"): usage=ev["usage"]
                for c in ev.get("choices") or []:
                    if (c.get("delta") or {}).get("content"):
                        now=time.perf_counter(); first=first or now; last=now; chunks+=1
        if first is None: raise AskError("串流沒有任何 content")
        n=(usage or {}).get("completion_tokens") or chunks
        dec=(n-1)/(last-first) if last>first and n>1 else 0.0
        return {"ttft_s":first-t0,"decode_tps":dec,"e2e_tps":n/(last-t0),"tokens":n,
                "token_count":"usage" if usage else "chunks"}

def emit(obj,out=None):
    s=json.dumps(obj,ensure_ascii=False)
    print(s)
    if out: Path(out).write_text(s+"\n",encoding="utf-8")

def spread(xs):
    """中位數與全距。Day 15 起多輪結果一律這樣報。"""
    s=sorted(xs); n=len(s)
    med=s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
    return {"median":med,"min":s[0],"max":s[-1],"runs":list(xs)}

def fmt_spread(sp):
    m=sp["median"]; m=int(m) if m==int(m) else m
    return f"{m}" if sp["min"]==sp["max"] else f"{m}（{sp['min']}–{sp['max']}）"

# ---- 繁簡判準 ----
# 用一份「簡體專用」字表數洩漏字數。沒有 opencc/zhconv 時的手工表，覆蓋率不是 100%，
# 但同一把尺套在所有受測模型上，相對比較仍然成立；報告時報「洩漏字數」而非只給二元通過。
# 刻意排除繁簡同形字（理、行、真）與兩邊通用的異體（復/复、確/确、錄/录、術/术、須/须、災/灾）。
# 不接 opencc：逐字做 s2t 比對會把「余→餘」「涂→塗」這種繁體本來就有的字算成簡體，
# 等於把下面那張排除表的問題原樣帶回來。
_S = ("门问间闻这个们说时对为发学实现观点会来给东车马鸟长风书见电话语汉体产权双卫医开关闭"
      "杂网络认识应该记执验证测试爱备毕币标称迟担党导敌读断队际继艰简讲经旧据课况乐历练两灵"
      "龙楼虑轮罗买卖满梦灭恼脑齐启气迁签枪劝让荣扫伤设胜师势兽属树帅顺丝随态叹图团湾万务显"
      "宪县线响协写谢兴选压严颜样业页仪义艺阴阳营优邮鱼与园远愿约跃运赞脏则责战郑织职纸质钟"
      "种众专转装状资总组过宽减内带层单价击剂节结紧进举壳块矿库垒类丽励连联恋粮疗辽临邻岭陆"
      "乱轮麦迈脉贸么闷弥觅绵悯闽谬谋亩闹馁拟酿疟盘辔骗飘频贫凭苹凄谦钱潜浅墙抢桥窍窃亲寝庆"
      "穷琼颂讼诵苏诉肃虽孙缩琐锁挞摊贪烫涛腾条铁厅听统头涂颓弯维伟纬谓稳误锡袭铣戏细虾吓纤"
      "鲜险乡详项泻锌许绪续悬旋勋哑亚烟盐厌砚鸦养谣钥药爷叶铱议异译银饮萤蝇颖铀余渔语郁誉预"
      "驭渊员圆缘韵赃凿枣灶泽贼赠轧铡闸诈斋毡盏辗绽张涨帐胀浙贞针侦诊镇挣睁挚掷终诌轴皱昼骤"
      "诸猪嘱瞩贮铸筑砖赚妆锥渍踪纵邹诅钻")
_T = ("門問間聞這個們說時對為發學實現觀點會來給東車馬鳥長風書見電話語漢體產權雙衛醫開關閉"
      "雜網絡認識應該記執驗證測試愛備畢幣標稱遲擔黨導敵讀斷隊際繼艱簡講經舊據課況樂歷練兩靈"
      "龍樓慮輪羅買賣滿夢滅惱腦齊啟氣遷簽槍勸讓榮掃傷設勝師勢獸屬樹帥順絲隨態嘆圖團灣萬務顯"
      "憲縣線響協寫謝興選壓嚴顏樣業頁儀義藝陰陽營優郵魚與園遠願約躍運贊髒則責戰鄭織職紙質鐘")
# v2 新增排除（1020）：旋、浙繁簡同字；余涂叶种据郁 繁體本來就有（含姓氏、拮据、濃郁）；
# 凄脉猪踪烟韵灶弥 是台灣常見或教育部認可的異體。v1 會把這些算成洩漏。
_SHARED = "理行真复确录术须灾干后面" + "旋浙余涂叶种据郁凄脉猪踪烟韵灶弥"
SIMP = set(_S) - set(_T) - set(_SHARED)
ZH_RULER = "manual-v2"
def zh_leak(t): return len([c for c in t if c in SIMP])

def first_json(out):
    m=re.search(r'\{.*\}', out, re.S)
    return m.group(0) if m else ""
