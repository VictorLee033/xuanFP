# -*- coding: utf-8 -*-
"""实测东方财富个股新闻/公告接口"""
import os, json
os.environ["NO_PROXY"] = "*"
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}

def probe(label, url, params=None):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=20)
        print(f"\n== {label}: status={r.status_code} len={len(r.text)} ==")
        print("  ", r.text[:250])
    except Exception as e:
        print(f"\n== {label}: 异常 {type(e).__name__} {str(e)[:100]} ==")

# 1) F10 新闻公告
probe("F10 NewsBulletin", "https://emweb.securities.eastmoney.com/PC_HSF10/NewsBulletin/PageAjax",
      {"code": "SH600519", "pageSize": 5})

# 2) 公告
probe("公告 np-anotice", "https://np-anotice-stock.eastmoney.com/api/security/ann",
      {"sr": -1, "page_size": 5, "page_index": 1, "ann_type": "A", "client_source": "web", "stock_list": "600519"})

# 3) 搜索新闻
probe("搜索新闻", "https://search-api-web.eastmoney.com/search/jsonp",
      {"cb": "x", "param": json.dumps({"uid": "", "keyword": "贵州茅台", "type": ["cmsArticleWebOld"], "client": "web", "clientType": "web", "clientVersion": "curr", "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default", "pageIndex": 1, "pageSize": 5, "preTag": "<em>", "postTag": "</em>"}}})})
