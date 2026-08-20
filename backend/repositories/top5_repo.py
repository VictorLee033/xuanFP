# -*- coding: utf-8 -*-
"""回测库仓库：top5_records 的读写（记录每批 Top10，普通/短线按 mode 区分）。

语义：
- 每次标准时点扫描（短线14:25 / 标准15:00）完成，把当次 Top10 快照写入；
- 同一天同一模式只保留一份（replace 先删后插）；不同模式各存一份；
- 时点窗口外/历史回放由引擎控制，本仓库只负责按 (trade_date, mode) 覆盖写入。
"""
import json
import logging
import time

from .database import Database

logger = logging.getLogger(__name__)

_JSON_FIELDS = ("tags", "dimensions")


class Top10Repository:
    def __init__(self, db: Database):
        self.db = db

    def replace(self, trade_date: str, mode: str, records: list) -> None:
        """覆盖写入某天某模式的 Top10（先删同天同模式旧记录，再插新记录）。"""
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM top5_records WHERE trade_date=? AND mode=?",
                (trade_date, mode),
            )
            for r in records:
                conn.execute(
                    "INSERT INTO top5_records "
                    "(trade_date, rank, ts_code, name, close_price, pct_chg, amount, "
                    " total_mv, score, industry, sw_industry, tags, dimensions, mode, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        trade_date, r["rank"], r["ts_code"], r.get("name"),
                        r.get("close_price"), r.get("pct_chg"), r.get("amount"),
                        r.get("total_mv"), r.get("score"), r.get("industry"),
                        r.get("sw_industry"),
                        json.dumps(r.get("tags") or [], ensure_ascii=False),
                        json.dumps(r.get("dimensions") or {}, ensure_ascii=False),
                        mode, time.time(),
                    ),
                )
        logger.info("已记录回测库 Top10 date=%s mode=%s count=%s",
                    trade_date, mode, len(records))

    def _row_to_dict(self, row):
        d = dict(row)
        for k in _JSON_FIELDS:
            if d.get(k):
                try:
                    d[k] = json.loads(d[k])
                except (ValueError, TypeError):
                    d[k] = ([] if k == "tags" else {})
        return d

    def list_dates(self, mode: str = "") -> list:
        """某模式的交易日（升序去重）；mode 为空则全部。"""
        if mode:
            rows = self.db.query_all(
                "SELECT DISTINCT trade_date FROM top5_records WHERE mode=? ORDER BY trade_date ASC",
                (mode,),
            )
        else:
            rows = self.db.query_all(
                "SELECT DISTINCT trade_date FROM top5_records ORDER BY trade_date ASC"
            )
        return [r["trade_date"] for r in rows]

    def get_by_date(self, trade_date: str, mode: str = "") -> list:
        if mode:
            rows = self.db.query_all(
                "SELECT * FROM top5_records WHERE trade_date=? AND mode=? ORDER BY rank ASC",
                (trade_date, mode),
            )
        else:
            rows = self.db.query_all(
                "SELECT * FROM top5_records WHERE trade_date=? ORDER BY rank ASC",
                (trade_date,),
            )
        return [self._row_to_dict(r) for r in rows]

    def list_all(self, mode: str = "") -> list:
        """某模式的全部记录（升序）；mode 为空则全部。"""
        if mode:
            rows = self.db.query_all(
                "SELECT * FROM top5_records WHERE mode=? ORDER BY trade_date ASC, rank ASC",
                (mode,),
            )
        else:
            rows = self.db.query_all(
                "SELECT * FROM top5_records ORDER BY trade_date ASC, rank ASC"
            )
        return [self._row_to_dict(r) for r in rows]
