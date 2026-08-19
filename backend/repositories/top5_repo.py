# -*- coding: utf-8 -*-
"""Top5 回测记录仓库：top5_records 的读写。

语义：每次扫描完成，把当次 Top5 快照写入；同一天多次扫描只保留最后一次
（replace_day 先删后插）。回测时从库里取出历史批次，再补算前向收益。
"""
import json
import logging
import time

from .database import Database

logger = logging.getLogger(__name__)

_JSON_FIELDS = ("tags", "dimensions")


class Top5Repository:
    def __init__(self, db: Database):
        self.db = db

    def replace_day(self, trade_date: str, records: list) -> None:
        """覆盖写入某天的 Top5（先删当天旧记录，再插新记录）。"""
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM top5_records WHERE trade_date=?", (trade_date,))
            for r in records:
                conn.execute(
                    "INSERT INTO top5_records "
                    "(trade_date, rank, ts_code, name, close_price, pct_chg, amount, "
                    " total_mv, score, industry, sw_industry, tags, dimensions, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        trade_date, r["rank"], r["ts_code"], r.get("name"),
                        r.get("close_price"), r.get("pct_chg"), r.get("amount"),
                        r.get("total_mv"), r.get("score"), r.get("industry"),
                        r.get("sw_industry"),
                        json.dumps(r.get("tags") or [], ensure_ascii=False),
                        json.dumps(r.get("dimensions") or {}, ensure_ascii=False),
                        time.time(),
                    ),
                )
        logger.info("已记录 Top5 回测快照 date=%s count=%s", trade_date, len(records))

    def _row_to_dict(self, row):
        d = dict(row)
        for k in _JSON_FIELDS:
            if d.get(k):
                try:
                    d[k] = json.loads(d[k])
                except (ValueError, TypeError):
                    d[k] = ([] if k == "tags" else {})
        return d

    def list_dates(self) -> list:
        """所有已记录的交易日（升序去重）。"""
        rows = self.db.query_all(
            "SELECT DISTINCT trade_date FROM top5_records ORDER BY trade_date ASC"
        )
        return [r["trade_date"] for r in rows]

    def get_by_date(self, trade_date: str) -> list:
        rows = self.db.query_all(
            "SELECT * FROM top5_records WHERE trade_date=? ORDER BY rank ASC",
            (trade_date,),
        )
        return [self._row_to_dict(r) for r in rows]

    def list_all(self) -> list:
        rows = self.db.query_all(
            "SELECT * FROM top5_records ORDER BY trade_date ASC, rank ASC"
        )
        return [self._row_to_dict(r) for r in rows]
