# -*- coding: utf-8 -*-
"""Top5 回测服务：从回测库取历史 Top5，补算「入选后 N 个交易日」前向收益并统计。

收益口径（按需求约定）：
- 前复权日K（东财优先、腾讯/新浪兜底），入选日收盘 → 入选后第 N 个交易日收盘。
- 只算绝对收益率（%），不算交易成本、不对比大盘。
- 尚未走满 N 个交易日的批次（数据不足）自动跳过。
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

logger = logging.getLogger(__name__)


class BacktestService:
    def __init__(self, top5_repo, tx):
        self.top5_repo = top5_repo
        self.tx = tx

    # ------------------------------------------------------------------
    def records(self) -> dict:
        """列出回测库全部记录（按日期升序）。"""
        return {"records": self.top5_repo.list_all()}

    def run(self, n: int = 5, mode: str = "normal") -> dict:
        records = self.top5_repo.list_all(mode)
        empty = {
            "n": n, "mode": mode,
            "summary": {"avg_ret": None, "win_rate": None,
                        "total_batches": 0, "total_records": 0, "skipped": 0},
            "batches": [], "timeline": [],
        }
        if not records:
            return empty

        codes = sorted({r["ts_code"] for r in records})
        days_needed = self._days_needed(records, n)

        kline = {}
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(self._fetch, c, days_needed): c for c in codes}
            for fut in as_completed(futs):
                c = futs[fut]
                try:
                    kline[c] = fut.result() or []
                except Exception as e:  # noqa: BLE001
                    logger.debug("回测K线失败 %s: %s", c, e)
                    kline[c] = []

        # 逐条计算前向收益 + 次日卖点（14:30 买入 / 次日卖出场景）
        batches_map = {}
        all_rets = []
        all_nd = {"open": [], "high": [], "close": []}
        skipped = 0
        for r in records:
            bars = kline.get(r["ts_code"]) or []
            ret = self._forward_return(bars, r["trade_date"], n)
            if ret is None:
                skipped += 1
                continue
            all_rets.append(ret)
            item = {
                "rank": r["rank"], "ts_code": r["ts_code"], "name": r["name"],
                "close_price": r.get("close_price"), "score": r.get("score"),
                "pct_chg": r.get("pct_chg"), "ret": ret,
            }
            # 次日卖点（基于日K，买入≈当日收盘；n=1 时才有意义）
            nd = self._next_day_metrics(bars, r["trade_date"])
            if nd:
                item.update(nd)
                for k in ("open", "high", "close"):
                    all_nd[k].append(nd[f"{k}_ret"])
            batches_map.setdefault(r["trade_date"], []).append(item)

        batches = []
        for td in sorted(batches_map):
            items = batches_map[td]
            if not items:
                continue
            avg = round(sum(i["ret"] for i in items) / len(items), 2)
            nd_avg = None
            highs = [i["high_ret"] for i in items if "high_ret" in i]
            if highs:
                nd_avg = round(sum(highs) / len(highs), 2)
            batches.append({"trade_date": td, "avg_ret": avg, "nd_avg_high": nd_avg,
                            "records": items})

        if not all_rets:
            empty["summary"]["skipped"] = skipped
            return empty

        avg_ret = round(sum(all_rets) / len(all_rets), 2)
        win_rate = round(sum(1 for x in all_rets if x > 0) / len(all_rets) * 100, 2)
        summary = {
            "avg_ret": avg_ret, "win_rate": win_rate,
            "total_batches": len(batches),
            "total_records": len(all_rets), "skipped": skipped,
        }
        # 次日卖点汇总（有数据才给）
        if all_nd["high"]:
            summary["nd"] = {
                "avg_high": round(sum(all_nd["high"]) / len(all_nd["high"]), 2),
                "avg_close": round(sum(all_nd["close"]) / len(all_nd["close"]), 2),
                "avg_open": round(sum(all_nd["open"]) / len(all_nd["open"]), 2),
                "win_high": round(sum(1 for x in all_nd["high"] if x > 0) / len(all_nd["high"]) * 100, 2),
                "win_close": round(sum(1 for x in all_nd["close"] if x > 0) / len(all_nd["close"]) * 100, 2),
            }

        return {
            "n": n,
            "mode": mode,
            "summary": summary,
            "batches": batches,
            "timeline": [{"date": b["trade_date"], "avg_ret": b["avg_ret"]}
                         for b in batches],
        }

    # ------------------------------------------------------------------
    def _fetch(self, ts_code, days):
        return self.tx.kline(ts_code, days=days)

    def _days_needed(self, records, n):
        """估算覆盖最旧记录到今日 + N 个交易日所需的K线数量。"""
        today = date.today()
        oldest = None
        for r in records:
            try:
                d = date.fromisoformat(r["trade_date"])
                oldest = d if oldest is None or d < oldest else oldest
            except (ValueError, TypeError):
                continue
        calendar_span = (today - oldest).days if oldest else 0
        days = int(calendar_span * 5 / 7) + n + 40
        return max(days, n + 80)

    def _forward_return(self, bars, trade_date, n):
        """前向 N 个交易日收益率（%）。bars 时间升序。数据不足返回 None。"""
        if not bars:
            return None
        entry_idx = None
        for i, b in enumerate(bars):
            if b["date"] >= trade_date:
                entry_idx = i
                break
        if entry_idx is None:
            return None
        exit_idx = entry_idx + n
        if exit_idx >= len(bars):
            return None
        entry_close = bars[entry_idx].get("close")
        exit_close = bars[exit_idx].get("close")
        if not entry_close:
            return None
        return round((exit_close / entry_close - 1) * 100, 2)

    def _next_day_metrics(self, bars, trade_date):
        """次日卖点三种口径（买入≈当日收盘）：次日开盘/最高/收盘收益率(%)。
        数据不足返回 None。"""
        if not bars:
            return None
        entry_idx = None
        for i, b in enumerate(bars):
            if b["date"] >= trade_date:
                entry_idx = i
                break
        if entry_idx is None or entry_idx + 1 >= len(bars):
            return None
        entry_close = bars[entry_idx].get("close")
        nd = bars[entry_idx + 1]
        if not entry_close:
            return None
        return {
            "open_ret": round((nd.get("open") / entry_close - 1) * 100, 2),
            "high_ret": round((nd.get("high") / entry_close - 1) * 100, 2),
            "close_ret": round((nd.get("close") / entry_close - 1) * 100, 2),
        }
