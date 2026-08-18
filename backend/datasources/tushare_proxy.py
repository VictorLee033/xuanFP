# -*- coding: utf-8 -*-
"""Tushare 双代理客户端（PCD 主通道 + RDS 备通道，自动故障切换）

响应格式统一为 {"code": 0, "data": {"fields": [...], "items": [[...], ...]}}
调用方拿到的是 [{"字段": 值}, ...] 的字典列表。
"""
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import get_config
from ..storage.cache import cache_get, cache_set
from .base import http_get_json

# 各接口缓存 TTL（秒）
TTL = {
    "stock_basic": 86400,
    "daily": 86400,
    "daily_basic": 86400,
    "fina_indicator": 14 * 86400,
    "income": 14 * 86400,
    "balancesheet": 14 * 86400,
    "cashflow": 14 * 86400,
    "moneyflow": 86400,
    "margin_detail": 86400,
    "top_list": 86400,
    "top_inst": 86400,
    "stk_holdernumber": 14 * 86400,
    "trade_cal": 86400,
}


def _rows_to_dicts(fields, items):
    return [dict(zip(fields, row)) for row in (items or [])]


class TushareClient:
    """双通道 Tushare 代理客户端"""

    def __init__(self):
        self._channels = None
        self._lock = threading.Lock()

    def _get_channels(self):
        with self._lock:
            if self._channels is None:
                cfg = get_config()["tushare"]
                self._channels = [
                    {"name": "pcd", "base_url": cfg["pcd"]["base_url"],
                     "api_key": cfg["pcd"]["api_key"], "verify": False, "timeout": 120},
                    {"name": "rds", "base_url": cfg["rds"]["base_url"],
                     "api_key": cfg["rds"]["api_key"], "verify": True, "timeout": 60},
                ]
            return self._channels

    def invalidate_channels(self):
        with self._lock:
            self._channels = None

    # ------------------------------------------------------------------
    def _call_channel(self, ch, api, params):
        resp = http_get_json(
            f"{ch['base_url']}/{api}",
            params=params,
            headers={"X-API-Key": ch["api_key"]},
            timeout=ch["timeout"],
            verify=ch["verify"],
            retries=1,
            backoff=0.5,
        )
        if not isinstance(resp, dict):
            raise RuntimeError(f"非JSON响应: {str(resp)[:100]}")
        code = resp.get("code")
        data = resp.get("data") or {}
        if code is None and isinstance(data, dict) and data.get("items") is not None:
            code = 0  # 部分实现不返回 code
        if code != 0:
            raise RuntimeError(f"接口错误 code={code} msg={resp.get('msg') or resp.get('message')}")
        if not isinstance(data, dict) or not data.get("fields"):
            return []
        return _rows_to_dicts(data.get("fields") or [], data.get("items") or [])

    def _call(self, api, params):
        """主通道优先，失败自动切换备通道"""
        errors = []
        for ch in self._get_channels():
            try:
                return self._call_channel(ch, api, params)
            except Exception as e:  # noqa: BLE001
                errors.append(f"[{ch['name']}] {e}")
        raise RuntimeError("Tushare 双通道均失败: " + " | ".join(errors))

    def _cached(self, api, params, ttl=None):
        key = "ts:" + api + ":" + hashlib.md5(
            json.dumps(params, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        hit = cache_get(key)
        if hit is not None:
            return hit
        rows = self._call(api, params)
        cache_set(key, rows, ttl or TTL.get(api, 86400))
        return rows

    # ------------------------------------------------------------------
    # 基础信息
    def stock_basic(self, limit=8000):
        return self._cached("stock_basic", {"limit": limit}, TTL["stock_basic"])

    # 日线
    def daily(self, ts_code=None, trade_date=None, start_date=None, end_date=None):
        p = {}
        if ts_code:
            p["ts_code"] = ts_code
        if trade_date:
            p["trade_date"] = trade_date
        if start_date:
            p["start_date"] = start_date
        if end_date:
            p["end_date"] = end_date
        return self._cached("daily", p, TTL["daily"])

    # 每日指标（PE/PB/股息率/市值/换手）
    def daily_basic(self, ts_code=None, trade_date=None, start_date=None, end_date=None):
        p = {}
        if ts_code:
            p["ts_code"] = ts_code
        if trade_date:
            p["trade_date"] = trade_date
        if start_date:
            p["start_date"] = start_date
        if end_date:
            p["end_date"] = end_date
        return self._cached("daily_basic", p, TTL["daily_basic"])

    # 财务指标（支持区间，一次拿多个报告期）
    def fina_indicator(self, ts_code, start_date=None, end_date=None, period=None):
        p = {"ts_code": ts_code}
        if start_date:
            p["start_date"] = start_date
        if end_date:
            p["end_date"] = end_date
        if period:
            p["period"] = period
        return self._cached("fina_indicator", p, TTL["fina_indicator"])

    # 利润表
    def income(self, ts_code, start_date=None, end_date=None, period=None):
        p = {"ts_code": ts_code}
        if start_date:
            p["start_date"] = start_date
        if end_date:
            p["end_date"] = end_date
        if period:
            p["period"] = period
        return self._cached("income", p, TTL["income"])

    # 资产负债表
    def balancesheet(self, ts_code, start_date=None, end_date=None, period=None):
        p = {"ts_code": ts_code}
        if start_date:
            p["start_date"] = start_date
        if end_date:
            p["end_date"] = end_date
        if period:
            p["period"] = period
        return self._cached("balancesheet", p, TTL["balancesheet"])

    # 现金流量表
    def cashflow(self, ts_code, start_date=None, end_date=None, period=None):
        p = {"ts_code": ts_code}
        if start_date:
            p["start_date"] = start_date
        if end_date:
            p["end_date"] = end_date
        if period:
            p["period"] = period
        return self._cached("cashflow", p, TTL["cashflow"])

    # 个股资金流
    def moneyflow(self, ts_code, start_date, end_date):
        return self._cached("moneyflow", {"ts_code": ts_code, "start_date": start_date,
                                          "end_date": end_date}, TTL["moneyflow"])

    # 融资融券明细
    def margin_detail(self, ts_code, start_date, end_date):
        return self._cached("margin_detail", {"ts_code": ts_code, "start_date": start_date,
                                              "end_date": end_date}, TTL["margin_detail"])

    # 龙虎榜（按交易日）
    def top_list(self, trade_date):
        return self._cached("top_list", {"trade_date": trade_date}, TTL["top_list"])

    # 龙虎榜机构席位明细（按交易日）
    def top_inst(self, trade_date):
        return self._cached("top_inst", {"trade_date": trade_date}, TTL["top_list"])

    # 股东户数
    def stk_holdernumber(self, ts_code, start_date, end_date):
        return self._cached("stk_holdernumber", {"ts_code": ts_code, "start_date": start_date,
                                                 "end_date": end_date}, TTL["stk_holdernumber"])

    # 交易日历
    def trade_cal(self, start_date, end_date):
        return self._cached("trade_cal", {"start_date": start_date, "end_date": end_date,
                                          "is_open": "1"}, TTL["trade_cal"])

    # ------------------------------------------------------------------
    # 批量并发拉取（按股票），带进度回调
    def batch_fetch(self, items, fetch_fn, max_workers=None, progress=None):
        """items: [(key, kwargs_dict), ...]; fetch_fn(key, kwargs) -> rows
        返回 {key: rows}; progress(done, total)"""
        cfg = get_config()["scanner"]
        workers = max_workers or cfg.get("max_workers", 24)
        results = {}
        total = len(items)
        done = 0
        lock = threading.Lock()

        def run(item):
            key, kwargs = item
            try:
                return key, fetch_fn(**kwargs)
            except Exception as e:  # noqa: BLE001
                return key, None

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(run, it) for it in items]
            for fut in as_completed(futures):
                key, rows = fut.result()
                results[key] = rows
                done += 1
                if progress:
                    try:
                        progress(done, total)
                    except Exception:
                        pass
        return results
