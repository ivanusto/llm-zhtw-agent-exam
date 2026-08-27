#!/usr/bin/env python3
"""原版 vs 後訓練版的同卷對決。評分一律用可機器判定的客觀標準，不用主觀印象。"""
import json,re,sys,time,urllib.request,statistics
B=sys.argv[1]; M=sys.argv[2]; LABEL=sys.argv[3]
def ask(msg,maxtok=300,temp=0.0):
    # 一定要關思考模式：開著的話每題要吐 150 token 以上，10 tok/s 下一題就一分鐘，
    # 而且思考內容會混進 content 欄位（這個容器沒開 reasoning-parser），
    # 模型思考時用簡體中文，會讓「繁體用字」這項判準失真。
    d=json.load(urllib.request.urlopen(urllib.request.Request(B+"/v1/chat/completions",method="POST",
      data=json.dumps({"model":M,"messages":[{"role":"user","content":msg}],
                       "max_tokens":maxtok,"temperature":temp,
                       "chat_template_kwargs":{"enable_thinking":False}}).encode(),
      headers={"Content-Type":"application/json"}),timeout=900))
    ch=d["choices"][0]["message"]
    return (ch.get("content") or "").strip(), d["usage"]

# 繁簡判準：用一份「簡體專用」字表數洩漏字數。
# 這台機器沒有 opencc/zhconv，所以是手工表，覆蓋率不是 100%。
# 但同一把尺同樣套在兩個模型上，相對比較仍然成立；報告時報「洩漏字數」而非只給二元通過。
# 刻意排除繁簡同形字（理、行、真）與兩邊通用的異體（復/复、確/确、錄/录、術/术、須/须、災/灾）。
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
SIMP = set(_S) - set(_T) - set("理行真复确录术须灾干后面")
def zh_leak(t): return len([c for c in t if c in SIMP])

# ---- 一、繁中十題（客觀判準：繁體、含關鍵字、遵守格式）----
ZH=[
 ("用繁體中文一句話說明什麼是投機解碼，句子必須包含「草稿」兩個字。",["草稿"]),
 ("用繁體中文列出三個 NVMe 比 SATA SSD 快的原因，每點一行，開頭用「1.」「2.」「3.」。",["1.","2.","3."]),
 ("用繁體中文解釋 KV cache 是什麼，回答必須少於五十個字。",["KV"]),
 ("台北捷運文湖線是哪一種系統？用繁體中文回答，答案要包含「膠輪」。",["膠輪"]),
 ("用繁體中文寫一句話說明為什麼量化會讓模型變快，必須提到「記憶體頻寬」。",["記憶體頻寬"]),
 ("用繁體中文回答：RAID 5 至少需要幾顆硬碟？只回答數字加單位。",["3","三"]),
 ("用繁體中文解釋什麼是 perplexity（困惑度），必須提到「越低越好」。",["越低越好"]),
 ("用繁體中文說明 FP8 與 INT8 的差別，必須提到「指數」。",["指數"]),
 ("用繁體中文一句話說明 mmap 載入模型的好處，必須包含「分頁」。",["分頁"]),
 ("用繁體中文回答：一個 27B 參數的模型用 4 位元量化後大約多大？只回答數字加 GB。",["GB","G"]),
]
# 這些題目的關鍵字是「任一命中即可」，不是全部都要出現。
ANY_OF={("3","三"),("GB","G")}

zh_score=0; zh_detail=[]
for q,keys in ZH:
    t,_=ask(q,250)
    # 判分修正 0827：原本的三元條件 len(keys)>1 or keys[0] not in ("3","三") 對
    # keys=["3","三"] 求值為 True，於是走 all() 分支，要求答案同時出現「3」與「三」，
    # any() 那個分支永遠到不了。三顆受測模型都答「3顆」，都被誤判為關鍵字未命中。
    # 改成用一張明確的「任一即可」題號表，不再靠關鍵字內容去猜判準。
    ok_k=(any(k.lower() in t.lower() for k in keys) if tuple(keys) in ANY_OF
          else all(k.lower() in t.lower() for k in keys))
    leak=zh_leak(t); ok_z = leak==0
    s=int(ok_k)+int(ok_z)
    zh_score+=s; zh_detail.append({"q":q[:26],"keyword":ok_k,"traditional":ok_z,"simp_leak":leak,"ans":t[:90]})
kw=sum(d["keyword"] for d in zh_detail); tr=sum(d["traditional"] for d in zh_detail)
leaks=sum(d["simp_leak"] for d in zh_detail)
print(f"  繁中十題：{zh_score}/20（關鍵字 {kw}/10、純繁體 {tr}/10），簡體字洩漏共 {leaks} 個")

# ---- 二、工具呼叫十輪（客觀判準：能不能 parse 成合法 JSON 且欄位正確）----
SCHEMA=('你可以呼叫這個工具：\n'
 '{"name":"search_files","parameters":{"dir":"string","pattern":"string","max_results":"integer"}}\n'
 '請只輸出一個 JSON 物件，格式為 {"name":..., "arguments":{...}}，不要有任何其他文字或 markdown 標記。\n\n任務：')
TASKS=["在 /var/log 找出所有 .err 檔，最多 20 筆",
 "在 /home/user/docs 搜尋含 invoice 的檔案，最多 5 筆",
 "列出 /etc 底下的 .conf 檔，最多 100 筆",
 "在 /tmp 找 core dump，最多 3 筆",
 "在 /srv/www 找 index.html，只要 1 筆",
 "在 /opt 搜尋 *.tar.gz，最多 50 筆",
 "在 /data 找出 2026 開頭的 csv，最多 10 筆",
 "在 /mnt/backup 找 .sql 檔，最多 25 筆",
 "在 /usr/share 搜尋 licence 相關檔案，最多 15 筆",
 "在 /root 找 .ssh 設定檔，最多 2 筆"]
tool_ok=0; tool_detail=[]
for t in TASKS:
    out,_=ask(SCHEMA+t,250)
    raw=out
    m=re.search(r'\{.*\}', out, re.S)
    ok=False; why=""
    if m:
        try:
            j=json.loads(m.group(0))
            args=j.get("arguments") or j.get("parameters") or {}
            ok = (j.get("name")=="search_files" and isinstance(args,dict)
                  and "dir" in args and "pattern" in args and "max_results" in args
                  and isinstance(args["max_results"],int))
            why="" if ok else f"欄位不全 {list(args)[:4]} name={j.get('name')}"
        except Exception as e: why=f"JSON 解析失敗 {type(e).__name__}"
    else: why="找不到 JSON"
    tool_ok+=int(ok); tool_detail.append({"task":t[:22],"ok":ok,"why":why,"raw":raw[:110]})
print(f"  工具呼叫十輪：{tool_ok}/10 合法")

# ---- 三、多步 agent 情境三題（客觀判準：三個步驟都出現且順序正確）----
AG=[
 ("你有 list_dir、read_file、write_file 三個工具。任務：找出 /project 底下最大的 .log 檔，讀它的最後 100 行，把摘要寫進 /project/summary.txt。"
  "請只列出你會依序呼叫的工具名稱，一行一個，不要解釋。",["list_dir","read_file","write_file"]),
 ("你有 http_get、parse_json、write_file 三個工具。任務：抓 https://example.invalid/api/stats，取出 total 欄位，存成 /tmp/total.txt。"
  "請只列出你會依序呼叫的工具名稱，一行一個，不要解釋。",["http_get","parse_json","write_file"]),
 ("你有 run_sql、format_table、send_email 三個工具。任務：查上季營收前十名客戶，排版成表格，寄給 finance@example.invalid。"
  "請只列出你會依序呼叫的工具名稱，一行一個，不要解釋。",["run_sql","format_table","send_email"]),
]
ag_ok=0; ag_detail=[]
for q,seq in AG:
    out,_=ask(q,250)
    low=out.lower()
    pos=[low.find(s) for s in seq]
    ok=all(p>=0 for p in pos) and pos==sorted(pos)
    ag_ok+=int(ok); ag_detail.append({"ok":ok,"out":out[:130]})
print(f"  多步 agent 三題：{ag_ok}/3 順序正確")

# ---- 四、decode ----
tps=[]
for i in range(3):
    p=f"Explain memory bandwidth limits in LLM inference. (id {i}-{time.time_ns()})"
    t0=time.perf_counter(); _,u=ask(p,300); t1=time.perf_counter()
    tps.append(u["completion_tokens"]/(t1-t0))
dec=statistics.median(tps)
print(f"  decode：{dec:.2f} tok/s")
print(json.dumps({"label":LABEL,"zh":zh_score,"zh_detail":zh_detail,"tool":tool_ok,
                  "tool_detail":tool_detail,"agent":ag_ok,"agent_detail":ag_detail,
                  "decode":dec},ensure_ascii=False))
