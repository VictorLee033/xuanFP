# -*- coding: utf-8 -*-
"""验证 PCD 数据新鲜度：最新交易日到底到哪一天"""
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3, time
urllib3.disable_warnings()

PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "YOUR_PCD_KEY"

def pcd(api, **p):
    r = requests.get(f"{PCD_URL}/{api}", params=p, headers={"X-API-Key": PCD_KEY}, verify=False, timeout=60)
    return r.json()

for d in ["20250113", "20250630", "20260701", "20260814", "20260817"]:
    try:
        j = pcd("daily", trade_date=d)
        items = (j.get("data") or {}).get("items") or []
        print(f"daily {d}: code={j.get('code')} items={len(items)}")
    except Exception as e:
        print(f"daily {d}: 异常 {type(e).__name__} {str(e)[:80]}")
    time.sleep(0.3)

print("\n-- trade_cal 最近日期 --")
try:
    j = pcd("trade_cal", start_date="20260801", end_date="20260831", is_open="1")
    items = (j.get("data") or {}).get("items") or []
    print("  code:", j.get("code"), "items:", len(items))
    if items:
        f = (j.get("data") or {}).get("fields") or []
        print("  fields:", f)
        for row in items[-5:]:
            print("  ", row)
except Exception as e:
    print("  trade_cal 异常:", type(e).__name__, str(e)[:100])

print("\n-- daily_basic 20260701 --")
try:
    j = pcd("daily_basic", trade_date="20260701")
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)}")
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:100])

print("\n-- fina_indicator 最新报告期 --")
try:
    j = pcd("fina_indicator", ts_code="000001.SZ", start_date="20240101", end_date="20260818")
    items = (j.get("data") or {}).get("items") or []
    f = (j.get("data") or {}).get("fields") or []
    idx = f.index("end_date")
    dates = sorted({r[idx] for r in items})
    print("  报告期:", dates)
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:100])
