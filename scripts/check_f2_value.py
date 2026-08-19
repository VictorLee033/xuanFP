# -*- coding: utf-8 -*-
import os
os.environ["NO_PROXY"] = "*"
import requests
B = "http://127.0.0.1:8710"
d = requests.get(B + "/api/scan/latest", timeout=15).json()
run = d.get("run") or {}
res = d.get("results") or []
for code in ["603444.SH", "600519.SH", "601398.SH"]:
    det = requests.get(f"{B}/api/stocks/{code}/detail?run_id={run.get('id')}", timeout=60).json()
    st = det.get("stock") or {}
    fac = st.get("factors") or {}
    f2 = fac.get("f2") or {}
    print(f"{code} {st.get('name')}: f2股息率 = {f2.get('score')} | {f2.get('note')}")
