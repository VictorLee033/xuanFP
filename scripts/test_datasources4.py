# -*- coding: utf-8 -*-
"""xuanFP 数据源测试 #4：fina区间查询 / 全市场资金流 / 辅助接口 / 东财字段 / 美股映射"""
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3, time
urllib3.disable_warnings()

PCD_URL = "https://pcd.mobcvb.cn/tushare/pro"
PCD_KEY = "YOUR_PCD_KEY"
RDS_URL = "http://datahubco.com/app-api/openapi/v1/tushare"
RDS_KEY = "YOUR_RDS_KEY"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

def pcd(api, **p):
    return requests.get(f"{PCD_URL}/{api}", params=p, headers={"X-API-Key": PCD_KEY}, verify=False, timeout=90).json()

def show(j, label):
    items = (j.get("data") or {}).get("items") or []
    f = (j.get("data") or {}).get("fields") or []
    print(f"  {label}: code={j.get('code')} items={len(items)}")
    if items:
        print("    fields:", ",".join(f)[:200])
        print("    row0:", str(items[0])[:180])

print("== PCD fina_indicator 区间查询(20211231~20240930) ==")
try:
    j = pcd("fina_indicator", ts_code="000001.SZ", start_date="20211231", end_date="20240930")
    items = (j.get("data") or {}).get("items") or []
    f = (j.get("data") or {}).get("fields") or []
    print(f"  code={j.get('code')} items={len(items)} (期望≈12期)")
    if items:
        idx = {n: i for i, n in enumerate(f)}
        for row in items:
            print("   ", row[idx["end_date"]], "roe:", row[idx.get("roe")], "gr:", row[idx.get("grossprofit_margin")])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD moneyflow 全市场单日(trade_date) ==")
try:
    t0 = time.time()
    j = pcd("moneyflow", trade_date="20250108")
    items = (j.get("data") or {}).get("items") or []
    f = (j.get("data") or {}).get("fields") or []
    print(f"  code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
    if items:
        print("    fields:", ",".join(f)[:200])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== PCD 辅助接口单只 ==")
for api, p, label in [
    ("margin_detail", {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"}, "margin_detail(融资融券)"),
    ("hk_hold", {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"}, "hk_hold(北向持股)"),
    ("top_list", {"trade_date": "20250108"}, "top_list(龙虎榜)"),
    ("stk_holdernumber", {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": "20250110"}, "stk_holdernumber(股东户数)"),
    ("pledge_stat", {"ts_code": "000001.SZ"}, "pledge_stat(质押)"),
    ("daily", {"trade_date": "20250108"}, "daily全市场单日"),
]:
    try:
        t0 = time.time()
        j = pcd(api, **p)
        items = (j.get("data") or {}).get("items") or []
        print(f"  {label}: code={j.get('code')} items={len(items)} 耗时={time.time()-t0:.1f}s")
        if items:
            f = (j.get("data") or {}).get("fields") or []
            print("    fields:", ",".join(f)[:160])
            print("    row0:", str(items[0])[:150])
    except Exception as e:
        print(f"  {label}: 异常 {type(e).__name__}: {str(e)[:110]}")
    time.sleep(0.2)

print("\n== 东财 clist 上市日期等更多字段 ==")
try:
    r = requests.get("https://push2delay.eastmoney.com/api/qt/clist/get", params={
        "pn": 1, "pz": 2, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f3",
        "fs": "m:0+t:6", "fields": "f2,f3,f12,f14,f20,f21,f26,f37,f100,f115,f128,f136,f140,f141,f152",
    }, headers=UA, timeout=20)
    j = r.json()
    for it in (j.get("data") or {}).get("diff", []):
        print("   ", it)
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 新浪美股行情(外盘映射) ==")
try:
    r = requests.get("https://hq.sinajs.cn/list=gb_nvda,gb_lly,gb_aapl", headers={**UA, "Referer": "https://finance.sina.com.cn"}, timeout=15)
    print("  status:", r.status_code)
    for line in r.text.strip().split("\n")[:3]:
        print("   ", line[:130])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n== 东财 f26 验证：对比已知上市日期(000001.SZ=1991-04-03) ==")
try:
    r = requests.get("https://push2delay.eastmoney.com/api/qt/stock/get", params={
        "secid": "0.000001", "fltt": 2, "invt": 2, "fields": "f57,f58,f84,f85,f100,f26,f51,f152",
    }, headers=UA, timeout=20)
    print("   ", r.text[:250])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:120])

print("\n完成")
