# -*- coding: utf-8 -*-
"""xuanFP 数据源测试 #3：全市场批量能力 / 东财全字段 / K线备选"""
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3, time
urllib3.disable_warnings()

RDS_URL = "http://datahubco.com/app-api/openapi/v1/tushare"
RDS_KEY = "dba548a206a453c197f9175189b757374fa6db9554bb29e69efea127"
PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "tsr_1FjRkziz3M7m0aLcTk0ZgnK03__xO3EYq0ZdwQqdwSE"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

def pcd(api, **p):
    return requests.get(f"{PCD_URL}/{api}", params=p, headers={"X-API-Key": PCD_KEY}, verify=False, timeout=90).json()

print("== RDS stock_basic 全量(limit=7000) ==")
try:
    r = requests.get(f"{RDS_URL}/stock_basic", params={"limit": "7000"}, headers={"X-API-Key": RDS_KEY}, timeout=60)
    j = r.json()
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)}")
    if items:
        print("  末条:", items[-1])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD fina_indicator 全市场(period=20240930, 不带ts_code) ==")
try:
    t0 = time.time()
    j = pcd("fina_indicator", period="20240930")
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
    if items:
        f = (j.get("data") or {}).get("fields") or []
        idx = {name: i for i, name in enumerate(f)}
        print("  样例:", {k: items[0][idx[k]] for k in ("ts_code", "roe", "grossprofit_margin", "netprofit_yoy", "or_yoy", "debt_to_assets", "q_sales_yoy", "q_profit_yoy", "rd_exp", "rd_exp_ratio") if k in idx})
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD daily_basic trade_date 全市场(不带ts_code) ==")
try:
    t0 = time.time()
    j = pcd("daily_basic", trade_date="20250108")
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
    if items:
        f = (j.get("data") or {}).get("fields") or []
        print("  fields:", ",".join(f))
        print("  样例:", items[0])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD income 全市场(period=20240930) ==")
try:
    t0 = time.time()
    j = pcd("income", period="20240930")
    items = (j.get("data") or {}).get("items") or []
    print(f"  code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 东财 push2delay clist 全字段 ==")
try:
    r = requests.get("https://push2delay.eastmoney.com/api/qt/clist/get", params={
        "pn": 1, "pz": 3, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f3",
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": "f2,f3,f5,f6,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f62,f100,f115,f124,f128,f136",
    }, headers=UA, timeout=20)
    j = r.json()
    print("  rc:", j.get("rc"), "total:", (j.get("data") or {}).get("total"))
    for it in (j.get("data") or {}).get("diff", [])[:3]:
        print("   ", it)
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 东财 push2delay 个股快照 stock/get ==")
try:
    r = requests.get("https://push2delay.eastmoney.com/api/qt/stock/get", params={
        "secid": "0.000001", "fltt": 2, "invt": 2,
        "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f107,f116,f117,f162,f167,f168,f169,f170,f171",
    }, headers=UA, timeout=20)
    print("  status:", r.status_code, "body:", r.text[:200])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 腾讯K线 web.ifzq.gtimg.cn ==")
try:
    r = requests.get("http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                     params={"param": "sh600519,day,,,20,qfq"}, headers=UA, timeout=20)
    print("  status:", r.status_code, "body:", r.text[:200])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 东财 push2his delay 变体 ==")
for host in ["http://push2his.eastmoney.com", "https://push2his.eastmoney.com"]:
    try:
        r = requests.get(f"{host}/api/qt/stock/kline/get", params={
            "secid": "0.000001", "klt": 101, "fqt": 1, "beg": "20241201", "end": "20250110",
            "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"}, headers=UA, timeout=15)
        print(f"  {host}: status={r.status_code} body={r.text[:120]!r}")
    except Exception as e:
        print(f"  {host}: 异常 {type(e).__name__}: {str(e)[:100]}")

print("\n完成")
