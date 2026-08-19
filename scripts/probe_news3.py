# -*- coding: utf-8 -*-
import os, json
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
r = requests.get("https://emweb.securities.eastmoney.com/PC_HSF10/NewsBulletin/PageAjax",
                 params={"code": "SH600519", "pageSize": 5}, headers=UA, timeout=20)
print("apparent_encoding:", r.apparent_encoding, "| header encoding:", r.encoding)
# 尝试 utf-8 解码
r.encoding = "utf-8"
j = r.json()
items = ((j.get("gszx") or {}).get("data") or {}).get("items") or []
print("items:", len(items))
if items:
    print("完整字段:", list(items[0].keys()))
    print("第一条:", json.dumps(items[0], ensure_ascii=False)[:400])
