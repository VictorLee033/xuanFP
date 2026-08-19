# -*- coding: utf-8 -*-
"""行情/详情服务：市场概览、K线、个股详情。"""
import logging

from ..errors import DataSourceError, NotFoundError, friendly_message

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self, em, tx, scan_repo, report_repo):
        self.em = em
        self.tx = tx
        self.scan_repo = scan_repo
        self.report_repo = report_repo

    def overview(self) -> dict:
        """市场概览：指数 + 涨跌幅榜（数据源失败时优雅降级为空）。"""
        top_gainers, top_losers = [], []
        try:
            snaps = self.em.market_snapshot()
            snaps = [s for s in snaps if s.get("pct_chg") is not None]
            snaps.sort(key=lambda s: s["pct_chg"], reverse=True)
            top_gainers = [{"ts_code": s["ts_code"], "name": s["name"], "price": s["price"],
                            "pct_chg": s["pct_chg"], "industry": s["industry"],
                            "amount": s["amount"], "turnover_rate": s["turnover_rate"]}
                           for s in snaps[:10]]
            top_losers = [{"ts_code": s["ts_code"], "name": s["name"], "price": s["price"],
                           "pct_chg": s["pct_chg"], "industry": s["industry"]}
                          for s in snaps[-10:]]
        except Exception as e:  # noqa: BLE001
            logger.warning("市场快照获取失败: %s", e)

        indices = {}
        try:
            q = self.tx.realtime(["000001.SH", "399001.SZ", "399006.SZ", "000300.SH"])
            for code, v in q.items():
                indices[code] = {"name": v["name"], "price": v["price"], "pct_chg": v["pct_chg"]}
        except Exception as e:  # noqa: BLE001
            logger.warning("指数行情获取失败: %s", e)

        return {"indices": indices, "top_gainers": top_gainers, "top_losers": top_losers}

    def kline(self, ts_code: str, days: int = 250) -> dict:
        try:
            bars = self.tx.kline(ts_code, days=days)
        except Exception as e:  # noqa: BLE001
            logger.error("K线获取失败 %s: %s", ts_code, e)
            raise DataSourceError(f"K线获取失败: {friendly_message(e)}") from e
        return {"ts_code": ts_code, "bars": bars}

    def stock_detail(self, ts_code: str, run_id: int | None) -> dict:
        if run_id is None:
            run_id = self.scan_repo.get_latest_run_id()
        if not run_id:
            raise NotFoundError("暂无扫描记录，请先运行扫描")
        results = self.scan_repo.get_results(run_id)
        stock = next((r for r in results if r["ts_code"] == ts_code), None)
        if stock is None:
            raise NotFoundError(f"该股票不在最近扫描结果中: {ts_code}")
        report = self.report_repo.get(run_id, ts_code)
        try:
            bars = self.tx.kline(ts_code, days=250)
        except Exception as e:  # noqa: BLE001
            logger.warning("详情K线获取失败 %s: %s", ts_code, e)
            bars = []
        return {"stock": stock, "report": report, "kline": bars}
