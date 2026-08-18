# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")
from backend.datasources import TushareClient

ts = TushareClient()
code = "000001.SZ"

def show(label, rows):
    if not rows:
        print(f"  {label}: 空")
        return
    dates = sorted({str(r.get('end_date')) for r in rows})
    print(f"  {label}: {len(rows)} 行, end_dates={dates[-6:]}")

print("== period 精确查询 ==")
for p in ["20231231", "20240930", "20241231", "20250630", "20260331"]:
    try:
        t0 = time.time()
        rows = ts.fina_indicator(ts_code=code, period=p)
        show(f"period={p} ({time.time()-t0:.1f}s)", rows)
    except Exception as e:
        print(f"  period={p}: 异常 {type(e).__name__} {str(e)[:80]}")

print("== 区间查询 ==")
for s, e in [("20240101", "20241231"), ("20240101", "20260818"), ("20250601", "20260818")]:
    try:
        t0 = time.time()
        rows = ts.fina_indicator(ts_code=code, start_date=s, end_date=e)
        show(f"range {s}~{e} ({time.time()-t0:.1f}s)", rows)
    except Exception as ex:
        print(f"  range {s}~{e}: 异常 {type(ex).__name__} {str(ex)[:80]}")
