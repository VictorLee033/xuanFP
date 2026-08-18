# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")
from backend.datasources import TencentClient

tx = TencentClient()
for code, label in [("000001.SZ", "A股K线"), ("600519.SH", "茅台K线")]:
    try:
        t0 = time.time()
        bars = tx.kline(code, 320)
        last = bars[-1] if bars else None
        print(f"{label}: OK {len(bars)} 根 | 最新 {last.get('date') if last else '无'} 收{last.get('close') if last else '无'} | {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"{label}: FAIL {str(e)[:150]}")
try:
    t0 = time.time()
    ub = tx.kline_us("NVDA", 30)
    print(f"美股NVDA: OK {len(ub)} 根 | 最新 {ub[-1]['date'] if ub else '无'} | {time.time()-t0:.1f}s")
except Exception as e:
    print("美股NVDA FAIL:", str(e)[:150])
try:
    q = tx.realtime(["000001.SH"])
    print("指数实时: OK", q.get("000001.SH", {}).get("price"))
except Exception as e:
    print("实时 FAIL:", str(e)[:100])
