# -*- coding: utf-8 -*-
"""因子引擎冒烟测试：用真实数据对 4 只股票计算九维 37 因子"""
import os
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")

from backend.datasources import TushareClient, TencentClient  # noqa: E402
from backend.scanner import factors, scoring  # noqa: E402

STOCKS = ["000001.SZ", "600519.SH", "300750.SZ", "002415.SZ", "688981.SH"]


def main():
    ts = TushareClient()
    tx = TencentClient()
    cfg_weights = {"value": 12, "quality": 18, "growth": 15, "trend": 13,
                   "momentum": 12, "capital": 13, "chip": 8, "safety": 5, "macro": 4}

    today = date.today()
    y3 = (today - timedelta(days=365 * 3 + 60)).strftime("%Y%m%d")
    y4 = (today - timedelta(days=365 * 4 + 60)).strftime("%Y%m%d")
    d30 = (today - timedelta(days=40)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    bench = tx.kline("000300.SH", days=120)
    us_mom = {}
    for sw, sym in factors.US_MAP.items():
        try:
            bars = tx.kline_us(sym, days=30)
            if len(bars) >= 21:
                us_mom[sym] = bars[-1]["close"] / bars[-21]["close"] - 1
        except Exception:
            pass
    print("bench bars:", len(bench), "| us_momentum:", {k: round(v, 3) for k, v in us_mom.items()})

    for code in STOCKS:
        print(f"\n{'='*70}\n{code}")
        try:
            kline = tx.kline(code, days=320)
        except Exception as e:
            print("  kline FAIL:", e)
            continue
        db_rows = ts.daily_basic(ts_code=code, start_date=d30, end_date=end)
        db = db_rows[-1] if db_rows else {}
        fina = ts.fina_indicator(ts_code=code, start_date=y3, end_date=end)
        income = ts.income(ts_code=code, start_date=y4, end_date=end)
        bs = ts.balancesheet(ts_code=code, start_date=y4, end_date=end)
        cf = ts.cashflow(ts_code=code, start_date=y3, end_date=end)
        mf = ts.moneyflow(ts_code=code, start_date=d30, end_date=end)
        margin = ts.margin_detail(ts_code=code, start_date=d30, end_date=end)
        holders = ts.stk_holdernumber(ts_code=code, start_date=y3, end_date=end)

        b = {
            "ts_code": code, "name": code, "industry": "测试",
            "snapshot": {}, "kline": kline, "daily_basic": db, "daily_by_date": {},
            "fina": fina, "income": income, "bs": bs, "cf": cf,
            "moneyflow": mf, "margin": margin, "holders": holders,
            "top_inst": [], "bench": bench, "us_momentum": us_mom,
        }
        b["sw_industry"] = factors.SW_MAP.get(b["industry"], b["industry"])
        fr = factors.compute_factors(b)
        combined, dims, missing = scoring.aggregate(fr, cfg_weights)
        print(f"  综合得分: {combined:.2f}")
        for dim, d in dims.items():
            print(f"    {d['name']}: {d['score']} 分 (可得 {d['available']}/{d['total']}, 权重 {d['weight_effective']:.1f})")
        for k, v in fr.items():
            s = f"{v['score']:.0f}" if v["score"] is not None else "--"
            print(f"    {k} {v['name']}: {s} | {v['value']} | {v['note']}")
        print(f"  缺失因子: {len(missing)} 个 ->", [m["key"] for m in missing])


if __name__ == "__main__":
    main()
