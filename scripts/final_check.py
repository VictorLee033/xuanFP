# -*- coding: utf-8 -*-
import os, json
os.environ["NO_PROXY"] = "*"
import requests
B = "http://127.0.0.1:8710"

# 最新扫描
d = requests.get(f"{B}/api/scan/latest", timeout=15).json()
run = d.get("run") or {}
res = d.get("results") or []
print("run id:", run.get("id"), "| stats:", json.dumps(run.get("stats", {}), ensure_ascii=False))
print("top20:", len(res), "只")
print("首名详情:")
if res:
    code = res[0]["ts_code"]
    det = requests.get(f"{B}/api/stocks/{code}/detail?run_id={run.get('id')}", timeout=30).json()
    s = det.get("stock") or {}
    print("  ", s.get("ts_code"), s.get("name"), "| industry:", s.get("industry"), "| sw:", s.get("sw_industry"), "| score:", s.get("score"))
    print("  K线:", len(det.get("kline") or []), "根 | 报告字数:", len(det.get("report") or ""))
    print("  报告前 200 字:", (det.get("report") or "")[:200].replace("\n", " "))

# 历史对比
h = requests.get(f"{B}/api/history", timeout=15).json()
runs = h.get("runs") or []
print("\n历史记录:", [(r["id"], r.get("stats", {}).get("date")) for r in runs[:5]])
if len(runs) >= 2:
    cmp = requests.get(f"{B}/api/history/compare?a={runs[1]['id']}&b={runs[0]['id']}", timeout=15).json()
    print("对比: 上升", len(cmp.get("up", [])), "下降", len(cmp.get("down", [])), "新进", len(cmp.get("new_in", [])), "掉榜", len(cmp.get("dropped", [])))

# 前端
for u in ["/", "/vendor/vue.global.prod.js", "/vendor/element-plus.full.min.js", "/vendor/echarts.min.js", "/vendor/element-plus.css"]:
    r = requests.get(B + u, timeout=15)
    print(f"GET {u}: {r.status_code} ({len(r.content)} bytes)")
