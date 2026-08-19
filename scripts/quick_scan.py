# -*- coding: utf-8 -*-
import os, time, requests
os.environ["NO_PROXY"] = "*"
B = "http://127.0.0.1:8710"
requests.post(B + "/api/scan", timeout=10)
t0 = time.time()
while True:
    time.sleep(5)
    p = requests.get(B + "/api/scan/progress", timeout=10).json()
    print(f"  [{p['phase']}] {p['done']}/{p['total']} - {p['message']}")
    if p["phase"] in ("done", "failed") and not p["running"]:
        break
    if time.time() - t0 > 300:
        print("超时")
        break
d = requests.get(B + "/api/scan/latest", timeout=15).json()
run = d.get("run") or {}
print("扫描结果:", p["phase"], "| stats:", run.get("stats") or {})
print("Top3:", [r["name"] for r in (d.get("results") or [])[:3]])
