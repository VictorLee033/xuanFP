# -*- coding: utf-8 -*-
"""验证 f2 股息率 与 f23 龙虎榜 对吉比特的取数情况"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")
from backend.datasources.fundamentals import FundamentalsClient
from backend.datasources import EastMoneyClient

fc = FundamentalsClient()
em = EastMoneyClient()

# 吉比特 与 茅台 的分红
for code in ["603444.SH", "600519.SH", "000001.SZ"]:
    divs = fc.dividend_report(code)
    print(f"{code}: 分红记录 {len(divs)} 条", divs[:3] if divs else "（空）")

# 吉比特快照价格
snap = em.market_snapshot()
m = {s["ts_code"]: s for s in snap}
if "603444.SH" in m:
    print("吉比特价格:", m["603444.SH"].get("price"))

# 龙虎榜：吉比特 603444 是否在最近机构龙虎榜
for d in ["2026-08-18", "2026-08-14", "2026-08-13"]:
    net = fc.top_list_inst_net(d)
    print(f"龙虎榜 {d}: 机构席位 {len(net)} 只股票, 含603444? {'603444' in net}")
