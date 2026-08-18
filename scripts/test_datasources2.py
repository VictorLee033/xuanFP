# -*- coding: utf-8 -*-
"""xuanFP 数据源测试 #2：RDS 原始返回 / PCD 重试与 stock_basic / 东财与备选行情源"""
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()

RDS_URL = "http://datahubco.com/app-api/openapi/v1/tushare"
RDS_KEY = "dba548a206a453c197f9175189b757374fa6db9554bb29e69efea127"
PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "tsr_1FjRkziz3M7m0aLcTk0ZgnK03__xO3EYq0ZdwQqdwSE"

print("== RDS 原始返回（看报错信息）==")
for api, p in [("daily", {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"}),
               ("daily", {"trade_date": "20250108"}),
               ("fina_indicator", {"ts_code": "000001.SZ", "period": "20240930"})]:
    try:
        r = requests.get(f"{RDS_URL}/{api}", params=p, headers={"X-API-Key": RDS_KEY}, timeout=25)
        print(f"  {api} {list(p.keys())}: status={r.status_code} body={r.text[:150]!r}")
    except Exception as e:
        print(f"  {api}: 异常 {type(e).__name__}: {str(e)[:120]}")

print("\n== PCD stock_basic 原始返回 ==")
try:
    r = requests.get(f"{PCD_URL}/stock_basic", params={"limit": "3"}, headers={"X-API-Key": PCD_KEY}, verify=False, timeout=30)
    print("  status:", r.status_code, "body:", r.text[:300])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD moneyflow 重试(60s) / daily_basic(60s) ==")
for api, p in [("moneyflow", {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"}),
               ("daily_basic", {"ts_code": "000001.SZ", "start_date": "20250108", "end_date": "20250110"})]:
    try:
        r = requests.get(f"{PCD_URL}/{api}", params=p, headers={"X-API-Key": PCD_KEY}, verify=False, timeout=60)
        j = r.json()
        items = (j.get("data") or {}).get("items") or []
        print(f"  {api}: code={j.get('code')} items={len(items)}")
        if items: print("    样例:", items[0])
    except Exception as e:
        print(f"  {api}: 异常 {type(e).__name__}: {str(e)[:120]}")

print("\n== 东财带 UA / http 协议 ==")
ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
for base in ["https://push2.eastmoney.com", "http://push2.eastmoney.com", "https://push2delay.eastmoney.com"]:
    try:
        r = requests.get(f"{base}/api/qt/clist/get", params={"pn": 1, "pz": 2, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f3", "fs": "m:0+t:6", "fields": "f2,f3,f12,f14"}, headers=ua, timeout=15)
        print(f"  {base}: status={r.status_code} body={r.text[:100]!r}")
    except Exception as e:
        print(f"  {base}: 异常 {type(e).__name__}: {str(e)[:100]}")

print("\n== 腾讯行情 qt.gtimg.cn（备选实时源）==")
try:
    r = requests.get("http://qt.gtimg.cn/q=sh600519,sz000001,sh000001", headers=ua, timeout=15)
    print("  status:", r.status_code)
    for line in r.text.strip().split(";")[:4]:
        print("   ", line[:160])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 新浪行情 hq.sinajs.cn（备选实时源）==")
try:
    r = requests.get("https://hq.sinajs.cn/list=sh600519,sz000001,sh000001", headers={**ua, "Referer": "https://finance.sina.com.cn"}, timeout=15)
    print("  status:", r.status_code)
    for line in r.text.strip().split("\n")[:4]:
        print("   ", line[:160])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 东财 K线带 UA ==")
try:
    r = requests.get("https://push2his.eastmoney.com/api/qt/stock/kline/get",
                     params={"secid": "0.000001", "klt": 101, "fqt": 1, "beg": "20241201", "end": "20250110",
                             "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"},
                     headers=ua, timeout=15)
    print("  status:", r.status_code, "body:", r.text[:150])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n完成")
