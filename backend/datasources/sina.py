# -*- coding: utf-8 -*-
"""新浪行情客户端：美股实时行情（外盘映射因子）"""
from ..config import get_config
from .base import http_get


class SinaClient:
    def __init__(self):
        self._cfg = None

    def _get_cfg(self):
        if self._cfg is None:
            self._cfg = get_config()["sina"]
        return self._cfg

    def invalidate(self):
        self._cfg = None

    def us_realtime(self, symbols):
        """symbols: ["NVDA","LLY",...] -> {symbol: dict}"""
        cfg = self._get_cfg()
        if not symbols:
            return {}
        q = ",".join(f"gb_{s.lower()}" for s in symbols)
        resp = http_get(cfg["quote_url"] + q,
                        headers={"Referer": "https://finance.sina.com.cn"},
                        timeout=20, retries=2)
        text = resp.content.decode("gbk", errors="ignore")
        out = {}
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("var hq_str_gb_"):
                continue
            symbol = line[len("var hq_str_gb_"):line.index("=")]
            body = line.split('="', 1)[-1].rstrip('";')
            parts = body.split(",")
            if len(parts) < 8:
                continue
            try:
                out[symbol.upper()] = {
                    "name": parts[0],
                    "price": float(parts[1]),
                    "pct_chg": float(parts[2]),
                    "datetime": parts[3],
                    "change": float(parts[4]),
                    "open": float(parts[5]),
                    "high": float(parts[6]),
                    "low": float(parts[7]),
                    "high_52w": float(parts[8]) if len(parts) > 8 else None,
                    "low_52w": float(parts[9]) if len(parts) > 9 else None,
                    "volume": float(parts[10]) if len(parts) > 10 else None,
                    "amount": float(parts[11]) if len(parts) > 11 else None,
                }
            except (ValueError, IndexError):
                continue
        return out
