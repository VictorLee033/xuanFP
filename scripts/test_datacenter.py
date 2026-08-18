# -*- coding: utf-8 -*-
import os, json
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0"}

def fin(code, pagesize=8):
    r = requests.get("https://datacenter-web.eastmoney.com/api/data/v1/get", params={
        "reportName": "RPT_F10_FINANCE_MAINFINADATA", "columns": "ALL",
        "filter": f'(SECUCODE="{code}")', "pageNumber": 1, "pageSize": pagesize,
        "source": "HSF10", "client": "PC", "sortColumns": "REPORT_DATE", "sortTypes": "-1"}, headers=UA, timeout=25)
    j = r.json()
    return (j.get("result") or {}).get("data") or []

rows = fin("600519.SH", 8)
print(f"茅台 财务期数: {len(rows)}")
keys = ["REPORT_DATE","REPORT_TYPE","EPSJB","BPS","TOTALOPERATEREVE","MLR","ROEJQ","ROEKCJQ",
        "TOTALOPERATEREVETZ","PARENTNETPROFITTZ","KCFJCXSYJLRTZ","ZCFZL","CHZZL","YSZKZZL",
        "INVENTORY_TR_YOY","JYXJLYYSR","XJLLB","FCFF_FORWARD","NCO_NETPROFIT","RDEXPEND","PRATIO",
        "DJD_DPNP_QOQ","DJD_TOI_YOY","XSMLL","XSJLL","KCFJCXSYJLR"]
for r in rows[:4]:
    print("\n", r.get("REPORT_DATE"), r.get("REPORT_TYPE"))
    for k in keys:
        v = r.get(k)
        if v is not None:
            print(f"   {k} = {v}")
