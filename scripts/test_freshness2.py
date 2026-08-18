# -*- coding: utf-8 -*-
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3, time
urllib3.disable_warnings()
PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
K = "tsr_1FjRkziz3M7m0aLcTk0ZgnK03__xO3EYq0ZdwQqdwSE"
for d in ["20250113", "20250630", "20260701", "20260814"]:
    t0 = time.time()
    try:
        r = requests.get(f"{PCD_URL}/daily", params={"trade_date": d},
                         headers={"X-API-Key": K}, verify=False, timeout=45)
        j = r.json()
        n = len((j.get("data") or {}).get("items") or [])
        print(f"daily {d}: code={j.get('code')} items={n} 耗时={time.time()-t0:.1f}s")
    except Exception as e:
        print(f"daily {d}: 异常 {type(e).__name__} {str(e)[:80]} 耗时={time.time()-t0:.1f}s")
    time.sleep(1)
