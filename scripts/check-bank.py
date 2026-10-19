#!/usr/bin/env python3
"""檢查題庫 JSON 與 exam/*.md 說明文件是否一致：每道題的提示詞都必須逐字出現在對應的 md 裡。"""
import sys
from common import BANK,load_bank

def md(name): return (BANK/name).read_text(encoding="utf-8")
miss=[]
def need(text,name):
    if text not in md(name): miss.append((name,text[:40]))
for it in load_bank("zh10.json"): need(it["q"],"zh10.md")
t=load_bank("tools.json"); need(t["prefix"],"tools.md")
for it in t["tasks"]: need(it["task"],"tools.md")
for it in load_bank("agent.json"): need(it["q"],"agent.md")
need(load_bank("json-compact.json")["prompt"],"json-compact.md")
for name,text in miss: print(f"  {name} 缺少：{text}")
print("題庫與文件一致" if not miss else f"共 {len(miss)} 處不一致")
sys.exit(1 if miss else 0)
