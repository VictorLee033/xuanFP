# -*- coding: utf-8 -*-
"""验证 fundamentals.py 的 6 个取数方法（真实数据）"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")

from backend.datasources.fundamentals import FundamentalsClient

fc = FundamentalsClient()

print("== 1) 股息率（分红送配）600519 茅台 ==")
for code in ["600519.SH", "000001.SZ"]:
    rows = fc.dividend_report(code)
    print(f"  {code}: {len(rows)} 条分红记录")
    for r in rows[:3]:
        print(f"    {r['ex_date']} 每10股派 {r['pretax_bonus_10']} 元")

print("\n== 2) 北向持股 ==")
for code in ["600519.SH", "000001.SZ"]:
    d = fc.northbound_hold(code)
    print(f"  {code}: {d}")

print("\n== 3) 机构龙虎榜（2026-08-18）==")
net = fc.top_list_inst_net("2026-08-18")
print(f"  机构专用席位涉及的股票数: {len(net)}")
for code, v in list(net.items())[:5]:
    print(f"    {code}: 净额 {v/1e4:.0f} 万元")

print("\n== 4) 股东户数变化 ==")
for code in ["600519.SH", "000001.SZ"]:
    rows = fc.holder_number(code)
    print(f"  {code}: {len(rows)} 期")
    for r in rows[:2]:
        print(f"    {r['end_date']} 户数={r['holder_num']} 环比={r['ratio']}%")

print("\n== 5) 两融明细 ==")
for code in ["600519.SH", "000001.SZ"]:
    t0 = time.time()
    rows = fc.margin_data(code, days=10)
    print(f"  {code}: {len(rows)} 天 ({time.time()-t0:.1f}s)")
    for r in rows[:3]:
        rzye, rqye = r["rzye"], r["rqye"]
        print(f"    {r['date']} 融资余额={rzye/1e8:.2f}亿 融券余额={rqye/1e6:.0f}万 比值={rqye/rzye:.4f}")
