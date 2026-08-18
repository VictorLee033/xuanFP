# -*- coding: utf-8 -*-
import os, json
os.environ["NO_PROXY"] = "*"
import requests
BASE = "http://127.0.0.1:8710"

d = requests.get(f"{BASE}/api/scan/latest", timeout=15).json()
run = d.get("run") or {}
print("latest run id:", run.get("id"), "| stats:", json.dumps(run.get("stats", {}), ensure_ascii=False))
res = d.get("results") or []
print("results:", len(res))
for r in res[:8]:
    print("  ", r["rank"], r["ts_code"], r["name"], r["score"], r.get("sw_industry"))

# 详情接口
if res:
    code = res[0]["ts_code"]
    det = requests.get(f"{BASE}/api/stocks/{code}/detail?run_id={run.get('id')}", timeout=20).json()
    s = det.get("stock") or {}
    print("\n详情:", code, s.get("name"), "score", s.get("score"))
    dims = s.get("dimensions") or {}
    print("九维:")
    for k, v in dims.items():
        print(f"   {v['name']}: {v['score']} (可得{v['available']}/{v['total']})")
    print("K线根数:", len(det.get("kline") or []))
    print("LLM报告(前120字):", (det.get("report") or "")[:120])
