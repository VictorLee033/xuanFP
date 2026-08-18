# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")
from datetime import date, timedelta
from backend.datasources import TushareClient
from backend.scanner import filters

ts = TushareClient()
y3 = (date.today() - timedelta(days=365*3+60)).strftime("%Y%m%d")
end = date.today().strftime("%Y%m%d")
for code in ["600519.SH", "601398.SH", "000001.SZ"]:
    t0 = time.time()
    try:
        rows = ts.fina_indicator(ts_code=code, start_date=y3, end_date=end)
        print(f"{code}: fina rows={len(rows)} 耗时={time.time()-t0:.1f}s")
        if rows:
            r = rows[-1]
            print("   last end_date:", r.get("end_date"), "roe:", r.get("roe"), "or_yoy:", r.get("or_yoy"), "debt:", r.get("debt_to_assets"))
        passed, reason, ws = filters.check_financial_gate(rows, pe_ttm=20.0)
        print("   gate:", passed, reason, ws)
    except Exception as e:
        print(f"{code}: 异常 {type(e).__name__} {str(e)[:120]} 耗时={time.time()-t0:.1f}s")
