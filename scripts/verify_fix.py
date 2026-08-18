# -*- coding: utf-8 -*-
import os
os.environ["NO_PROXY"] = "*"
import requests
B = "http://127.0.0.1:8710"
d = requests.get(B + "/api/scan/latest", timeout=15).json()
res = d.get("results") or []
run_id = (d.get("run") or {}).get("id")
code = res[0]["ts_code"] if res else "603129.SH"
det = requests.get(f"{B}/api/stocks/{code}/detail?run_id={run_id}", timeout=30).json()
s = det.get("stock") or {}
print("详情:", s.get("name"), s.get("ts_code"), "| sw:", s.get("sw_industry"), "| 得分:", s.get("score"))
print("K线:", len(det.get("kline") or []), "根 | 报告:", len(det.get("report") or ""), "字")
f = requests.get(B + "/", timeout=10)
print("前端首页:", f.status_code)
