# -*- coding: utf-8 -*-
"""第五轮探测：两融用 securities/api/data/get 端点 + RPTA_WEB_RZRQ_* 类型"""
import os
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/rzrq/"}

def sec_api(type_, filter_str, ps=5):
    r = requests.get("https://datacenter.eastmoney.com/securities/api/data/get", params={
        "type": type_, "sty": "ALL", "filter": filter_str,
        "p": 1, "ps": ps, "sr": -1, "st": "date"}, headers=UA, timeout=25)
    try:
        j = r.json()
    except Exception:
        return r.status_code, r.text[:200]
    return r.status_code, (j.get("result") or {}).get("data") or j

for t in ["RPTA_WEB_RZRQ_GGMX", "RPTA_WEB_RZRQ_LSHJ", "RPTA_WEB_RZRQ_ZJMX"]:
    st, d = sec_api(t, '(scode="600519")')
    print(f"\n== {t}: status={st} ==")
    if isinstance(d, list) and d:
        print("  keys:", list(d[0].keys()))
        print("  row0:", dict(list(d[0].items())[:12]))
    elif isinstance(d, dict):
        print("  dict keys:", list(d.keys())[:20])
        print("  片段:", str(d)[:200])
    else:
        print("  data:", str(d)[:200])
