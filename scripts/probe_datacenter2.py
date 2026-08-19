# -*- coding: utf-8 -*-
"""第二轮探测：龙虎榜/两融的替代报告名、北向多期、东财快照大单字段"""
import os
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"

def dc(reportName, filter_str, pagesize=3, source="WEB"):
    r = requests.get(DC, params={
        "reportName": reportName, "columns": "ALL",
        "filter": filter_str, "pageNumber": 1, "pageSize": pagesize,
        "source": source, "client": "WEB"}, headers=UA, timeout=25)
    j = r.json()
    data = ((j or {}).get("result") or {}).get("data") or []
    return r.status_code, data

def show(label, status, data, maxk=12):
    print(f"\n== {label}: status={status} rows={len(data)} ==")
    if data:
        print("   keys:", list(data[0].keys()))
        print("   row0:", {k: data[0][k] for k in list(data[0].keys())[:maxk]})

# 龙虎榜候选报告名
for rn in ["RPT_BILLBOARD_TRADEDETAIL", "RPT_BILLBOARD_DAILYDETAILSBUY",
           "RPT_BILLBOARD_DAILYDETAILSSELL", "RPT_BILLBOARD_TRADEACTIVITY"]:
    show(f"龙虎榜 {rn}", *dc(rn, "(TRADE_DATE='2026-08-18')"))

# 两融候选
for rn in ["RPT_MARGIN_DETAIL", "RPT_MARGIN_TRADING", "RPT_MARGIN_DAILY",
           "RPTA_MARGIN_DETAIL", "RPT_MARGIN_STA"]:
    show(f"两融 {rn}", *dc(rn, "(SECUCODE='600519.SH')"))

# 北向多期（近12期，看能否算月度变动）
show("北向多期", *dc("RPT_MUTUAL_HOLDSTOCKNORTH_STA", "(SECUCODE='600519.SH')", pagesize=6))

# 东财 clist 大单/超大单字段
print("\n== 东财 clist 资金流字段 ==")
r = requests.get("https://push2delay.eastmoney.com/api/qt/clist/get", params={
    "pn": 1, "pz": 3, "po": 0, "np": 1, "fltt": 2, "invt": 2, "fid": "f20",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
    "fields": "f2,f6,f12,f14,f62,f64,f66,f69,f72,f78,f84,f184"}, headers=UA, timeout=20)
j = r.json()
for it in (j.get("data") or {}).get("diff", [])[:3]:
    print("  ", it)
