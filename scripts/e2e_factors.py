# -*- coding: utf-8 -*-
"""端到端验证：扫描 + 因子明细无硬编码缺失 + 两层权重生效"""
import os, time
os.environ["NO_PROXY"] = "*"
import requests
B = "http://127.0.0.1:8710"

# 健康
h = requests.get(B + "/api/health", timeout=15).json()
print("健康:", h)

# 触发扫描
requests.post(B + "/api/scan", timeout=10)
t0 = time.time()
while True:
    time.sleep(8)
    p = requests.get(B + "/api/scan/progress", timeout=15).json()
    print(f"  [{p['phase']}] {p['done']}/{p['total']} - {p['message']}")
    if p["phase"] in ("done", "failed") and not p["running"]:
        break
    if time.time() - t0 > 600:
        print("超时")
        break
print("最终:", p["phase"], p.get("message"))

# 最新结果
d = requests.get(B + "/api/scan/latest", timeout=15).json()
run = d.get("run") or {}
res = d.get("results") or []
print("\nstats:", run.get("stats") or {})
print("Top5:", [(r["ts_code"], r["name"], r["score"]) for r in res[:5]])

# 详情：检查因子明细是否有硬编码"缺失（降权）"
if res:
    code = res[0]["ts_code"]
    det = requests.get(f"{B}/api/stocks/{code}/detail?run_id={run.get('id')}", timeout=60).json()
    st = det.get("stock") or {}
    factors = st.get("factors") or {}
    total = len(factors)
    missing = [k for k, v in factors.items() if v.get("score") is None]
    hardcoded = [k for k, v in factors.items() if v.get("note", "").startswith(("缺失", "数据缺失", "降权"))]
    print(f"\n详情 {code} {st.get('name')}: 因子数={total}, score=None 的={len(missing)}, note含'缺失'的={len(hardcoded)}")
    print("缺失因子:", missing if missing else "无（该股数据齐全）")
    dims = st.get("dimensions") or {}
    print("九维得分:")
    for k, v in dims.items():
        print(f"   {v['name']}: {v['score']} (可得 {v['available']}/{v['total']})")
