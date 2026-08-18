# -*- coding: utf-8 -*-
import os, time
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()
PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
K = "tsr_1FjRkziz3M7m0aLcTk0ZgnK03__xO3EYq0ZdwQqdwSE"

def pcd(api, **p):
    r = requests.get(f"{PCD_URL}/{api}", params=p, headers={"X-API-Key": K}, verify=False, timeout=90)
    return r.json()

# 1) trade_cal 最新日期
print("== trade_cal 2026-08 ==")
try:
    j = pcd("trade_cal", start_date="20260801", end_date="20260831", is_open="1")
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)}")
    if items:
        f = (j.get("data") or {}).get("fields") or []
        print("  fields:", f)
        for row in items[-6:]:
            print("  ", row)
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:90])
time.sleep(12)

# 2) 试探最近交易日的 daily（2026年）
print("\n== daily 最近日期试探 ==")
for d in ["20260814", "20260813", "20250113"]:
    try:
        j = pcd("daily", trade_date=d)
        n = len((j.get("data") or {}).get("items") or [])
        print(f"  {d}: code={j.get('code')} items={n}")
        if n:
            break
    except Exception as e:
        print(f"  {d}: 异常 {type(e).__name__} {str(e)[:70]}")
    time.sleep(12)
