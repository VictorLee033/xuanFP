# -*- coding: utf-8 -*-
"""发现东财 clist 财务字段含义 + 测试东财数据中心接口"""
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0"}

# 1) clist 全字段 dump（对茅台/平安/宁德）
print("== EM clist 全字段（600519/000001/300750）==")
fields = ",".join(f"f{i}" for i in range(1, 130))
for code in ["600519", "000001", "300750"]:
    try:
        r = requests.get("https://push2delay.eastmoney.com/api/qt/stock/get",
                         params={"secid": ("1." if code.startswith("6") else "0.") + code,
                                 "fltt": 2, "invt": 2, "fields": fields}, headers=UA, timeout=20)
        d = (r.json() or {}).get("data") or {}
        nonempty = {k: v for k, v in d.items() if v not in (None, "-", "")}
        print(f"\n{code}: {len(nonempty)} 个非空字段")
        for k, v in nonempty.items():
            print(f"  {k} = {v}")
    except Exception as e:
        print(f"{code}: 异常 {type(e).__name__} {str(e)[:80]}")

# 2) 数据中心接口
print("\n== EM datacenter 财务主要指标 ==")
for base in ["https://datacenter-web.eastmoney.com", "https://datacenter.eastmoney.com"]:
    try:
        r = requests.get(f"{base}/api/data/v1/get", params={
            "reportName": "RPT_F10_FINANCE_MAINFINADATA", "columns": "ALL",
            "filter": '(SECUCODE="600519.SH")', "pageNumber": 1, "pageSize": 2,
            "source": "HSF10", "client": "PC"}, headers=UA, timeout=20)
        j = r.json()
        ok = j.get("success") if isinstance(j, dict) else None
        result = j.get("result") or {} if isinstance(j, dict) else {}
        data = result.get("data") or []
        print(f"  {base}: status={r.status_code} success={ok} rows={len(data)}")
        if data:
            print("   keys:", list(data[0].keys()))
            print("   样例:", {k: data[0][k] for k in list(data[0].keys())[:12]})
    except Exception as e:
        print(f"  {base}: 异常 {type(e).__name__} {str(e)[:80]}")
