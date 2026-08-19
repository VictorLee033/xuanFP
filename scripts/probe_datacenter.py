# -*- coding: utf-8 -*-
"""实测东财数据中心补因子所需的 6 类数据接口"""
import os, json
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"

def dc(reportName, filter_str, pagesize=3):
    r = requests.get(DC, params={
        "reportName": reportName, "columns": "ALL",
        "filter": filter_str, "pageNumber": 1, "pageSize": pagesize,
        "source": "HSF10", "client": "PC",
        "sortColumns": "", "sortTypes": "-1"}, headers=UA, timeout=25)
    j = r.json()
    data = ((j or {}).get("result") or {}).get("data") or []
    return r.status_code, data

def show(label, status, data, max_keys=14):
    print(f"\n== {label}: status={status} rows={len(data)} ==")
    if data:
        print("   keys:", list(data[0].keys()))
        print("   row0:", {k: data[0][k] for k in list(data[0].keys())[:max_keys]})

# 1) 分红送配
show("分红送配 RPT_SHAREBONUS_DET", *dc("RPT_SHAREBONUS_DET", '(SECUCODE="600519.SH")'))
# 2) 北向持股（沪深港通）
show("北向持股 RPT_MUTUAL_STOCK_NORTHSTA", *dc("RPT_MUTUAL_STOCK_NORTHSTA", '(SECUCODE="600519.SH")'))
show("北向持股 RPT_MUTUAL_HOLDSTOCKNORTH_STA", *dc("RPT_MUTUAL_HOLDSTOCKNORTH_STA", '(SECUCODE="600519.SH")'))
# 3) 龙虎榜
show("龙虎榜 RPT_BILLBOARD_TRADEDETAIL", *dc("RPT_BILLBOARD_TRADEDETAIL", '(TRADE_DATE=\'2026-08-18\')'))
# 4) 股东户数
show("股东户数 RPT_HOLDERNUM_DET", *dc("RPT_HOLDERNUM_DET", '(SECUCODE="600519.SH")'))
show("股东户数 RPT_F10_EH_HOLDERNUM", *dc("RPT_F10_EH_HOLDERNUM", '(SECUCODE="600519.SH")'))
# 5) 两融
show("两融 RPT_MARGIN_DETAIL", *dc("RPT_MARGIN_DETAIL", '(SECUCODE="600519.SH")'))
