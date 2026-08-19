# -*- coding: utf-8 -*-
"""第四轮探测：两融数据（按交易日过滤 / 换数据中心域名 / 两融专用接口）"""
import os
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}

def dc(base, reportName, filter_str, pagesize=3, source="WEB"):
    r = requests.get(f"{base}/api/data/v1/get", params={
        "reportName": reportName, "columns": "ALL",
        "filter": filter_str, "pageNumber": 1, "pageSize": pagesize,
        "source": source, "client": "WEB"}, headers=UA, timeout=25)
    j = r.json()
    return ((j or {}).get("result") or {}).get("data") or []

def show(label, data, maxk=10):
    print(f"\n== {label}: rows={len(data)} ==")
    if data:
        print("   keys:", list(data[0].keys())[:25])
        print("   row0:", {k: data[0][k] for k in list(data[0].keys())[:maxk]})

# 按交易日过滤（全市场两融当日）
for base in ["https://datacenter-web.eastmoney.com", "https://datacenter.eastmoney.com"]:
    for rn in ["RPT_MARGIN_DETAIL", "RPT_MARGIN_TRADING", "RPTA_MARGIN_DETAIL"]:
        d = dc(base, rn, "(TRADE_DATE='2026-08-18')", pagesize=3)
        if d:
            show(f"两融 {base.split('//')[1]} {rn} [by date]", d)
            raise SystemExit

# 两融专用旧接口
print("\n== 两融专用接口 ==")
for u in [
    "https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_MARGIN_DETAIL&columns=ALL&filter=(TRADE_DATE='2026-08-18')&pageNumber=1&pageSize=3&source=WEB&client=WEB",
]:
    r = requests.get(u, headers=UA, timeout=25)
    print("  ", u.split('?')[0], r.status_code, r.text[:150])

# 融资融券汇总（两市）
print("\n== 两融汇总报告 ==")
for rn in ["RPT_MARGIN_TOTAL", "RPT_RZRQ_TOTAL", "RPT_MARGIN_SUMMARY"]:
    d = dc("https://datacenter-web.eastmoney.com", rn, "", pagesize=3)
    show(f"两融汇总 {rn}", d)
