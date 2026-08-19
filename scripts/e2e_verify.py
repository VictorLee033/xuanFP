# -*- coding: utf-8 -*-
"""端到端验证：健康检查 + 全市场扫描 + 详情 + 历史对比"""
import os, time, json
os.environ["NO_PROXY"] = "*"
import requests

B = "http://127.0.0.1:8710"

def get(path, **kw):
    r = requests.get(B + path, timeout=kw.pop("timeout", 30), **kw)
    return r.status_code, r.json() if "json" in r.headers.get("content-type", "") else r.text

# 1) 健康检查
s, h = get("/api/health")
print("健康检查:", s, h)

# 2) 触发扫描并轮询
s, r = requests.post(B + "/api/scan", timeout=10).status_code, requests.post(B + "/api/scan", timeout=10).json()
print("触发扫描:", r)
t0 = time.time()
while True:
    time.sleep(5)
    _, p = get("/api/scan/progress")
    print(f"  [{p['phase']}] {p['done']}/{p['total']} - {p['message']}")
    if p["phase"] in ("done", "failed") and not p["running"]:
        break
    if time.time() - t0 > 600:
        print("超时"); break
print("最终状态:", p["phase"], p.get("message"))

# 3) 最新扫描结果
s, d = get("/api/scan/latest")
run = d.get("run") or {}
print("\n最新扫描:", s, "| stats:", json.dumps(run.get("stats", {}), ensure_ascii=False))
res = d.get("results") or []
for r in res[:5]:
    print("  ", r["rank"], r["ts_code"], r["name"], r["score"], r.get("sw_industry"))

# 4) 详情
if res:
    code = res[0]["ts_code"]
    s, det = get(f"/api/stocks/{code}/detail?run_id={run.get('id')}")
    st = det.get("stock") or {}
    print("\n详情:", s, st.get("name"), "| sw:", st.get("sw_industry"), "| 得分:", st.get("score"))
    print("  K线:", len(det.get("kline") or []), "根 | 报告:", len(det.get("report") or ""), "字")

# 5) 历史 + 对比
s, hd = get("/api/history")
runs = hd.get("runs") or []
print("\n历史:", s, "记录数", len(runs))
if len(runs) >= 2:
    s, cmp = get(f"/api/history/compare?a={runs[1]['id']}&b={runs[0]['id']}")
    print("对比:", s, "| 上升", len(cmp.get("up", [])), "下降", len(cmp.get("down", [])), "新进", len(cmp.get("new_in", [])))

# 6) 前端
s, _ = get("/")
print("\n前端首页:", s)
