# -*- coding: utf-8 -*-
import os
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0"}

print("== EM US kline 原始返回 ==")
for secid in ["106.NVDA", "105.NVDA", "107.NVDA"]:
    try:
        r = requests.get("https://push2delay.eastmoney.com/api/qt/stock/kline/get", params={
            "secid": secid, "klt": 101, "fqt": 1, "beg": "0", "end": "20500101",
            "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }, headers=UA, timeout=15)
        print(f"  {secid}: {r.status_code} body[:200]={r.text[:200]}")
    except Exception as e:
        print(f"  {secid}: 异常 {type(e).__name__} {str(e)[:80]}")

print("\n== 新浪美股K线 ==")
try:
    r = requests.get("https://quotes.sina.cn/us/api/jsonp_v2.php/var%20_=/US_MarketDataService.getKLineData",
                     params={"symbol": "NVDA", "scale": 240, "ma": "no", "datalen": 30},
                     headers={**UA, "Referer": "https://finance.sina.com.cn"}, timeout=20)
    print(f"  status={r.status_code} len={len(r.text)}")
    print(f"  body[:250]={r.text[:250]}")
except Exception as e:
    print(f"  异常: {type(e).__name__} {str(e)[:100]}")

print("\n== 腾讯美股K线 usfqkline ==")
try:
    r = requests.get("http://web.ifzq.gtimg.cn/appstock/app/usfqkline/get",
                     params={"param": "usNVDA.OQ,day,,,30,qfq"}, headers=UA, timeout=15)
    print(f"  status={r.status_code} body[:200]={r.text[:200]}")
except Exception as e:
    print(f"  异常: {type(e).__name__} {str(e)[:100]}")
