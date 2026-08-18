# -*- coding: utf-8 -*-
"""行情客户端：K线（东财 push2delay → 新浪 → 腾讯 三级回退）+ 实时行情"""
import json
import re

from ..config import get_config
from .base import http_get_json, http_get, http_get_fallback, http_get_json_fallback

KLINE_EM_URLS = [
    "https://push2delay.eastmoney.com/api/qt/stock/kline/get",
    "https://push2.eastmoney.com/api/qt/stock/kline/get",
]
KLINE_SINA_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_=/CN_MarketDataService.getKLineData"
KLINE_TENCENT_URLS = [
    "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
]
QUOTE_URLS = [
    "http://qt.gtimg.cn/q=",
    "https://qt.gtimg.cn/q=",
]


def _secid(ts_code):
    code, market = ts_code.split(".")
    return ("sh" if market == "SH" else "sz") + code


def _em_secid(ts_code):
    code, market = ts_code.split(".")
    return ("1." if market == "SH" else "0.") + code


class TencentClient:
    def __init__(self):
        self._cfg = None

    def _get_cfg(self):
        if self._cfg is None:
            self._cfg = get_config()["tencent"]
        return self._cfg

    def invalidate(self):
        self._cfg = None

    # ------------------------------------------------------------------
    def kline(self, ts_code, days=320, fq="qfq"):
        """前复权日K，返回 [{"date","open","close","high","low","volume"}...]（时间升序）
        三级回退：东财 push2delay → 新浪 → 腾讯"""
        errs = []
        for fn in (self._kline_em, self._kline_sina, self._kline_tencent):
            try:
                bars = fn(ts_code, days, fq)
                if bars:
                    return bars
            except Exception as e:  # noqa: BLE001
                errs.append(f"{fn.__name__}: {str(e)[:80]}")
        raise RuntimeError("K线获取失败: " + " | ".join(errs))

    def _kline_em(self, ts_code, days, fq):
        j = http_get_json_fallback(KLINE_EM_URLS, params={
            "secid": _em_secid(ts_code), "klt": 101, "fqt": 1,
            "beg": "0", "end": "20500101",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }, timeout=25, retries=1)
        data = (j or {}).get("data") or {}
        klines = data.get("klines") or []
        out = []
        for line in klines:
            p = str(line).split(",")
            if len(p) < 6:
                continue
            try:
                out.append({"date": p[0], "open": float(p[1]), "close": float(p[2]),
                            "high": float(p[3]), "low": float(p[4]),
                            "volume": float(p[5]) if p[5] not in ("", "-") else 0.0})
            except (ValueError, IndexError):
                continue
        return out

    def _kline_sina(self, ts_code, days, fq):
        param = f"{_secid(ts_code)}"
        r = http_get_fallback([KLINE_SINA_URL], params={
            "symbol": param, "scale": 240, "ma": "no", "datalen": max(days, 60),
        }, headers={"Referer": "https://finance.sina.com.cn"}, timeout=20, retries=1)
        text = r.content.decode("utf-8", errors="ignore")
        m = re.search(r"\((\[.*\])\)", text, re.DOTALL)
        if not m:
            return []
        try:
            arr = json.loads(m.group(1))
        except Exception:
            return []
        out = []
        for d in arr:
            try:
                out.append({"date": d["day"], "open": float(d["open"]), "close": float(d["close"]),
                            "high": float(d["high"]), "low": float(d["low"]),
                            "volume": float(d.get("volume") or 0)})
            except (ValueError, KeyError, TypeError):
                continue
        return out

    def _kline_tencent(self, ts_code, days, fq):
        param = f"{_secid(ts_code)},day,,,{days},{fq}"
        j = http_get_json_fallback(KLINE_TENCENT_URLS, params={"param": param}, timeout=25, retries=1)
        data = (j or {}).get("data") or {}
        node = data.get(_secid(ts_code)) or {}
        bars = node.get(f"{fq}day") or node.get("day") or []
        out = []
        for b in bars:
            try:
                out.append({"date": b[0], "open": float(b[1]), "close": float(b[2]),
                            "high": float(b[3]), "low": float(b[4]),
                            "volume": float(b[5]) if b[5] not in ("", None) else 0.0})
            except (ValueError, IndexError, TypeError):
                continue
        return out

    def kline_us(self, symbol, days=40):
        """美股K线（外盘映射用）。优先腾讯 usfqkline，再试东财(105/106/107.xxx)"""
        # 1) 腾讯美股专用K线（usfqkline 路径未被 WAF 拦截）
        try:
            j = http_get_json_fallback(
                [u.replace("/appstock/app/fqkline/get", "/appstock/app/usfqkline/get")
                 for u in KLINE_TENCENT_URLS],
                params={"param": f"us{symbol}.OQ,day,,,{days},qfq"}, timeout=20, retries=1)
            data = (j or {}).get("data") or {}
            node = data.get(f"us{symbol}.OQ") or {}
            bars = node.get("qfqday") or node.get("day") or []
            out = []
            for b in bars:
                try:
                    out.append({"date": b[0], "open": float(b[1]), "close": float(b[2]),
                                "high": float(b[3]), "low": float(b[4]),
                                "volume": float(b[5]) if b[5] not in ("", None) else 0.0})
                except (ValueError, IndexError, TypeError):
                    continue
            if out:
                return out
        except Exception:
            pass
        # 2) 东财美股K线（105/106/107 市场）
        for mkt in ("105", "106", "107"):
            try:
                j = http_get_json_fallback(KLINE_EM_URLS, params={
                    "secid": f"{mkt}.{symbol}", "klt": 101, "fqt": 1,
                    "beg": "0", "end": "20500101",
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                }, timeout=15, retries=1)
                data = (j or {}).get("data") or {}
                klines = data.get("klines") or []
                out = []
                for line in klines[-days:]:
                    p = str(line).split(",")
                    if len(p) < 6:
                        continue
                    try:
                        out.append({"date": p[0], "open": float(p[1]), "close": float(p[2]),
                                    "high": float(p[3]), "low": float(p[4]),
                                    "volume": float(p[5]) if p[5] not in ("", "-") else 0.0})
                    except (ValueError, IndexError):
                        continue
                if out:
                    return out
            except Exception:
                continue
        return []

    def realtime(self, ts_codes):
        """批量实时行情，返回 {ts_code: dict}"""
        if not ts_codes:
            return {}
        q = ",".join(_secid(c) for c in ts_codes)
        resp = http_get_fallback([u + q for u in QUOTE_URLS], timeout=20, retries=1)
        text = resp.content.decode("gbk", errors="ignore")
        out = {}
        for line in text.split(";"):
            line = line.strip()
            if not line.startswith("v_"):
                continue
            body = line.split('="', 1)[-1].rstrip('"')
            parts = body.split("~")
            if len(parts) < 50:
                continue
            sec = line[2:line.index("=")]
            market = "SH" if sec.startswith("sh") else "SZ"
            code = sec[2:]
            ts_code = f"{code}.{market}"

            def f(idx):
                try:
                    v = parts[idx]
                    return float(v) if v not in ("", "-") else None
                except (ValueError, IndexError):
                    return None

            out[ts_code] = {
                "name": parts[1],
                "code": code,
                "price": f(3), "pre_close": f(4), "open": f(5),
                "volume": f(6), "high": f(33), "low": f(34),
                "amount_wan": f(37), "turnover_rate": f(38),
                "pe_ttm": f(39), "pb": f(46), "circ_mv_yi": f(44),
                "total_mv_yi": f(45), "volume_ratio": f(49),
                "pct_chg": f(32), "change": f(31),
            }
        return out
