# -*- coding: utf-8 -*-
"""验证 top_inst / 腾讯指数K线 / 腾讯美股K线"""
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()

PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "YOUR_PCD_KEY"
UA = {"User-Agent": "Mozilla/5.0"}

print("== PCD top_inst(机构席位) ==")
try:
    r = requests.get(f"{PCD_URL}/top_inst", params={"trade_date": "20250108"},
                     headers={"X-API-Key": PCD_KEY}, verify=False, timeout=60)
    j = r.json()
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)}")
    if items:
        f = (j.get("data") or {}).get("fields") or []
        print("  fields:", ",".join(f)[:200])
        print("  row0:", str(items[0])[:180])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 腾讯沪深300 K线 ==")
try:
    r = requests.get("http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                     params={"param": "sh000300,day,,,10,qfq"}, headers=UA, timeout=20)
    j = r.json()
    node = (j.get("data") or {}).get("sh000300") or {}
    bars = node.get("qfqday") or node.get("day") or []
    print("  code:", j.get("code"), "bars:", len(bars), "| last:", bars[-1] if bars else None)
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 腾讯美股K线 NVDA ==")
try:
    r = requests.get("http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                     params={"param": "usNVDA.OQ,day,,,30,qfq"}, headers=UA, timeout=20)
    j = r.json()
    node = (j.get("data") or {}).get("usNVDA.OQ") or {}
    bars = node.get("qfqday") or node.get("day") or []
    print("  code:", j.get("code"), "bars:", len(bars), "| last:", bars[-1] if bars else None)
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD daily 最近5个交易日全市场(采样 20250106~20250110) ==")
import time
t0 = time.time()
try:
    r = requests.get(f"{PCD_URL}/daily", params={"trade_date": "20250106"},
                     headers={"X-API-Key": PCD_KEY}, verify=False, timeout=120)
    j = r.json()
    items = (j.get("data") or {}).get("items") or []
    print(f"  20250106: code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])
print("完成")
