# -*- coding: utf-8 -*-
"""xuanFP 数据源覆盖度测试：Tushare 双代理通道 + 东方财富实时行情"""
import os, sys, json, time
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()

RDS_URL = "http://datahubco.com/app-api/openapi/v1/tushare"
RDS_KEY = "dba548a206a453c197f9175189b757374fa6db9554bb29e69efea127"
PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "tsr_1FjRkziz3M7m0aLcTk0ZgnK03__xO3EYq0ZdwQqdwSE"

def rds(api, **p):
    r = requests.get(f"{RDS_URL}/{api}", params=p, headers={"X-API-Key": RDS_KEY}, timeout=25)
    return r.json()

def pcd(api, **p):
    r = requests.get(f"{PCD_URL}/{api}", params=p, headers={"X-API-Key": PCD_KEY}, verify=False, timeout=30)
    return r.json()

def brief(d, label):
    if not isinstance(d, dict):
        print(f"  {label}: 非JSON -> {str(d)[:120]}"); return
    code = d.get("code")
    data = d.get("data") or {}
    items = data.get("items") if isinstance(data, dict) else None
    n = len(items) if isinstance(items, list) else "?"
    print(f"  {label}: code={code} items={n}" + (f" fields={','.join(data.get('fields', []))}" if isinstance(data, dict) and data.get("fields") else ""))

# ---------- 通道1: RDS 覆盖度 ----------
print("== [RDS] datahubco.com 接口覆盖度 ==")
rds_cases = {
    "stock_basic": {"limit": 3},
    "daily": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "daily_basic": {"ts_code": "000001.SZ", "start_date": "20250108", "end_date": "20250110"},
    "fina_indicator": {"ts_code": "000001.SZ", "period": "20240930"},
    "income": {"ts_code": "000001.SZ", "period": "20240930"},
    "balancesheet": {"ts_code": "000001.SZ", "period": "20240930"},
    "cashflow": {"ts_code": "000001.SZ", "period": "20240930"},
    "moneyflow": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "hk_hold": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "top_list": {"trade_date": "20250108"},
    "margin_detail": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "stk_holdernumber": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "express": {"ts_code": "000001.SZ", "period": "20241231"},
    "forecast": {"ts_code": "000001.SZ", "period": "20241231"},
    "adj_factor": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "pledge_stat": {"ts_code": "000001.SZ"},
    "index_daily": {"ts_code": "000300.SH", "start_date": "20250101", "end_date": "20250110"},
}
for api, p in rds_cases.items():
    try:
        brief(rds(api, **p), api)
    except Exception as e:
        print(f"  {api}: 异常 {type(e).__name__}: {str(e)[:100]}")
    time.sleep(0.15)

# ---------- 通道2: PCD 覆盖度 ----------
print("\n== [PCD] pcd.mobcvb.cn pro 接口覆盖度 ==")
pcd_cases = {
    "daily": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "daily_basic": {"ts_code": "000001.SZ", "start_date": "20250108", "end_date": "20250110"},
    "fina_indicator": {"ts_code": "000001.SZ", "period": "20240930"},
    "income": {"ts_code": "000001.SZ", "period": "20240930"},
    "balancesheet": {"ts_code": "000001.SZ", "period": "20240930"},
    "cashflow": {"ts_code": "000001.SZ", "period": "20240930"},
    "moneyflow": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"},
    "stock_basic": {"limit": 3},
}
for api, p in pcd_cases.items():
    try:
        brief(pcd(api, **p), api)
    except Exception as e:
        print(f"  {api}: 异常 {type(e).__name__}: {str(e)[:100]}")
    time.sleep(0.15)

# ---------- 东方财富: 实时行情 ----------
print("\n== [EM] push2 实时行情 ==")
try:
    u = "https://push2.eastmoney.com/api/qt/clist/get"
    r = requests.get(u, params={
        "pn": 1, "pz": 3, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f3",
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": "f2,f3,f12,f14",
    }, timeout=25)
    print("  clist status:", r.status_code)
    j = r.json()
    print("  rc:", j.get("rc"), "total:", (j.get("data") or {}).get("total"))
    for item in (j.get("data") or {}).get("diff", [])[:3]:
        print(f"    {item.get('f12')} {item.get('f14')} 价={item.get('f2')} 涨跌={item.get('f3')}%")
except Exception as e:
    print("  clist 异常:", type(e).__name__, str(e)[:150])

# 东财 K线 (push2his)
print("\n== [EM] push2his K线 ==")
try:
    u = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    r = requests.get(u, params={
        "secid": "0.000001", "klt": 101, "fqt": 1, "beg": "20241201", "end": "20250110",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }, timeout=25)
    print("  kline status:", r.status_code)
    j = r.json()
    kl = (j.get("data") or {}).get("klines") or []
    print("  klines:", len(kl), "| 最新一根:", kl[-1] if kl else "无")
except Exception as e:
    print("  kline 异常:", type(e).__name__, str(e)[:150])

print("\n完成")
