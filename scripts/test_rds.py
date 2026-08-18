# -*- coding: utf-8 -*-
import os, time
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()

RDS_URL = "http://datahubco.com/app-api/openapi/v1/tushare"
RDS_KEY = "dba548a206a453c197f9175189b757374fa6db9554bb29e69efea127"
PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "tsr_1FjRkziz3M7m0aLcTk0ZgnK03__xO3EYq0ZdwQqdwSE"

print("== RDS 接口重测 ==")
for api, p in [
    ("daily", {"trade_date": "20250108"}),
    ("daily_basic", {"trade_date": "20250108"}),
    ("fina_indicator", {"ts_code": "000001.SZ", "period": "20240930"}),
    ("moneyflow", {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"}),
    ("trade_cal", {"start_date": "20260801", "end_date": "20260831", "is_open": "1"}),
]:
    t0 = time.time()
    try:
        r = requests.get(f"{RDS_URL}/{api}", params=p, headers={"X-API-Key": RDS_KEY}, timeout=40)
        body = r.text[:80].replace("\n", " ")
        try:
            j = r.json()
            n = len((j.get("data") or {}).get("items") or [])
            print(f"  {api}: status={r.status_code} code={j.get('code')} items={n} 耗时={time.time()-t0:.1f}s")
        except Exception:
            print(f"  {api}: status={r.status_code} body={body!r} 耗时={time.time()-t0:.1f}s")
    except Exception as e:
        print(f"  {api}: 异常 {type(e).__name__} {str(e)[:80]} 耗时={time.time()-t0:.1f}s")
    time.sleep(0.5)

print("\n== PCD 重试（等待后） ==")
time.sleep(20)
try:
    t0 = time.time()
    r = requests.get(f"{PCD_URL}/daily", params={"trade_date": "20250108"},
                     headers={"X-API-Key": PCD_KEY}, verify=False, timeout=60)
    j = r.json()
    items = (j.get("data") or {}).get("items") or []
    print(f"  daily 20250108: code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
    if items:
        print("  row0:", items[0])
except Exception as e:
    print(f"  PCD 异常 {type(e).__name__} {str(e)[:80]}")
