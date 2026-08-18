# -*- coding: utf-8 -*-
import os, time
os.environ["NO_PROXY"] = "*"
import requests, urllib3
urllib3.disable_warnings()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
      "Referer": "https://finance.sina.com.cn"}

print("== 新浪 K线 (quotes.sina.cn) ==")
try:
    r = requests.get("https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_=/CN_MarketDataService.getKLineData",
                     params={"symbol": "sh600519", "scale": 240, "ma": "no", "datalen": 30},
                     headers=UA, timeout=20)
    print("  status:", r.status_code, "len:", len(r.text))
    print("  body[:300]:", r.text[:300])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:100])

print("\n== 新浪K线域名2 (quotes.sina.com) ==")
try:
    r = requests.get("https://quotes.sina.com/cn/api/jsonp_v2.php/var%20_=/CN_MarketDataService.getKLineData",
                     params={"symbol": "sh600519", "scale": 240, "ma": "no", "datalen": 30},
                     headers=UA, timeout=20)
    print("  status:", r.status_code, "len:", len(r.text), "body[:150]:", r.text[:150])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:100])

print("\n== 东财 push2his 各域名 ==")
for host in ["https://push2his.eastmoney.com", "http://push2his.eastmoney.com",
             "https://push2his2.eastmoney.com", "https://push2delay.eastmoney.com"]:
    try:
        r = requests.get(f"{host}/api/qt/stock/kline/get", params={
            "secid": "1.600519", "klt": 101, "fqt": 1, "beg": "20260101", "end": "20260818",
            "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"},
            headers=UA, timeout=15)
        ok = '"klines"' in r.text
        print(f"  {host}: status={r.status_code} klines={ok} body[:80]={r.text[:80]!r}")
    except Exception as e:
        print(f"  {host}: 异常 {type(e).__name__} {str(e)[:80]}")

print("\n== 腾讯实时行情 qt.gtimg.cn（是否也被拦） ==")
try:
    r = requests.get("http://qt.gtimg.cn/q=sh600519", headers=UA, timeout=15)
    print("  status:", r.status_code, "body[:100]:", r.text[:100])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:100])

print("\n== 新浪实时行情 hq.sinajs.cn ==")
try:
    r = requests.get("https://hq.sinajs.cn/list=sh600519,sz000001",
                     headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}, timeout=15)
    print("  status:", r.status_code, "body[:150]:", r.text[:150])
except Exception as e:
    print("  异常:", type(e).__name__, str(e)[:100])
