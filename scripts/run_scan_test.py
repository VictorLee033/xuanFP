# -*- coding: utf-8 -*-
"""端到端扫描测试：触发扫描并轮询进度"""
import os, time, json
os.environ["NO_PROXY"] = "*"
import requests

BASE = "http://127.0.0.1:8710"

r = requests.post(f"{BASE}/api/scan", timeout=15)
print("scan started:", r.json())

t0 = time.time()
while True:
    time.sleep(5)
    p = requests.get(f"{BASE}/api/scan/progress", timeout=15).json()
    print(f"[{p['phase']}] {p['done']}/{p['total']} - {p['message']}")
    if p["phase"] in ("done", "failed") and not p["running"]:
        break
    if time.time() - t0 > 1500:
        print("超时")
        break

print("FINAL:", p["phase"], p.get("message"))
if p["phase"] == "done":
    d = requests.get(f"{BASE}/api/scan/latest", timeout=20).json()
    run = d.get("run") or {}
    print("run stats:", json.dumps(run.get("stats", {}), ensure_ascii=False))
    res = d.get("results", [])
    print("top20 count:", len(res))
    for r in res[:10]:
        print("  ", r["rank"], r["ts_code"], r["name"], r["score"], r.get("sw_industry"))
    s = run.get("summary") or {}
    print("top3_logic:")
    for line in s.get("top3_logic", []):
        print("  -", line)
