# -*- coding: utf-8 -*-
"""个股新闻数据源（东方财富 F10 新闻公告，GBK 编码）"""
import json
import logging

from .base import http_get

logger = logging.getLogger(__name__)

NEWS_URL = "https://emweb.securities.eastmoney.com/PC_HSF10/NewsBulletin/PageAjax"


def stock_news(ts_code, page_size=20):
    """个股近期新闻，返回 [{title, time_ms}]（按时间降序）"""
    code, market = ts_code.split(".")
    secu = ("SH" if market == "SH" else "SZ") + code
    try:
        resp = http_get(NEWS_URL, params={"code": secu, "pageSize": page_size},
                        timeout=20, retries=1)
        j = json.loads(resp.content.decode("gbk", errors="ignore"))
    except Exception as e:  # noqa: BLE001
        logger.debug("新闻获取失败 %s: %s", ts_code, e)
        return []
    items = ((j.get("gszx") or {}).get("data") or {}).get("items") or []
    out = []
    for it in items:
        title = (it.get("title") or "").strip()
        ts = it.get("showDateTime") or it.get("updateTime") or 0
        if title:
            out.append({"title": title, "time_ms": ts})
    return out
