# -*- coding: utf-8 -*-
"""第三轮探测：两融正确报告名 / 北向 HSF10 多期 / clist 大单字段（正常股票）"""
import os
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"

def dc(reportName, filter_str, pagesize=3, source="HSF10"):
    r = requests.get(DC, params={
        "reportName": reportName, "columns": "ALL",
        "filter": filter_str, "pageNumber": 1, "pageSize": pagesize,
        "source": source, "client": "PC"}, headers=UA, timeout=25)
    j = r.json()
    return ((j or {}).get("result") or {}).get("data") or []

def show(label, data, maxk=10):
    print(f"\n== {label}: rows={len(data)} ==")
    if data:
        print("   keys:", list(data[0].keys())[:25])
        print("   row0:", {k: data[0][k] for k in list(data[0].keys())[:maxk]})

# 两融：更多报告名（source 用 HSF10 和 WEB 都试）
for rn in ["RPT_MARGIN_DETAIL", "RPT_MARGIN_TRADING_DETAIL", "RPT_MARGIN_DAILYDETAILS",
           "RPTA_MARGIN_DETAIL", "RPT_RZRQ_DETAIL", "RPT_MARGIN_STOCK_DETAIL"]:
    d = dc(rn, '(SECUCODE="600519.SH")')
    if d:
        show(f"两融 {rn} [HSF10]", d)
        break
else:
    # 试 WEB source
    for rn in ["RPT_MARGIN_DETAIL", "RPT_MARGIN_TRADING_DETAIL", "RPT_MARGIN_DAILYDETAILS"]:
        d = dc(rn, '(SECUCODE="600519.SH")(TRADE_DATE>=\'2026-06-01\')', source="WEB")
        if d:
            show(f"两融 {rn} [WEB]", d)
            break
    else:
        print("\n两融：所有候选报告名均未返回数据")

# 北向：HSF10 多期
show("北向 HSF10 多期", dc("RPT_MUTUAL_HOLDSTOCKNORTH_STA", '(SECUCODE="600519.SH")', pagesize=6))

# clist 大单字段（正常大市值股，降序）
print("\n== clist 资金流字段（降序大市值） ==")
r = requests.get("https://push2delay.eastmoney.com/api/qt/clist/get", params={
    "pn": 1, "pz": 3, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f20",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
    "fields": "f2,f6,f12,f14,f62,f64,f66,f69,f72,f78"}, headers=UA, timeout=20)
j = r.json()
for it in (j.get("data") or {}).get("diff", [])[:3]:
    print("  ", it)
