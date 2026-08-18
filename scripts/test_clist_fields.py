# -*- coding: utf-8 -*-
import os
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0"}
fields = "f2,f3,f6,f8,f9,f10,f12,f14,f20,f21,f23,f26,f37,f55,f62,f92,f100,f115,f126,f127,f128"
r = requests.get("https://push2delay.eastmoney.com/api/qt/clist/get", params={
    "pn": 1, "pz": 5, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f20",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23", "fields": fields}, headers=UA, timeout=20)
j = r.json()
print("rc:", j.get("rc"), "total:", (j.get("data") or {}).get("total"))
for it in (j.get("data") or {}).get("diff", [])[:5]:
    print(it)
