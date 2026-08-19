# -*- coding: utf-8 -*-
import os
os.environ["NO_PROXY"] = "*"
import requests
B = "http://127.0.0.1:8710"
d = requests.get(B + "/api/scan/latest", timeout=15).json()
run = d.get("run") or {}
res = d.get("results") or []
code = res[0]["ts_code"] if res else "603444.SH"
det = requests.get(f"{B}/api/stocks/{code}/detail?run_id={run.get('id')}", timeout=30).json()
rep = det.get("report") or ""
print("报告字数:", len(rep))
print("报告前300字:", rep[:300].replace("\n", " "))
