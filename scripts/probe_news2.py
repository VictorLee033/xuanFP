# -*- coding: utf-8 -*-
import os, json
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
r = requests.get("https://emweb.securities.eastmoney.com/PC_HSF10/NewsBulletin/PageAjax",
                 params={"code": "SH600519", "pageSize": 8}, headers=UA, timeout=20)
j = r.json()
gszx = j.get("gszx") or {}
data = gszx.get("data") or {}
items = data.get("items") or []
print("count:", data.get("count"), "| 实际 items:", len(items))
for it in items[:4]:
    print("  ", {k: it.get(k) for k in ("title", "date", "showTime", "columns", "code") if it.get(k) is not None})
