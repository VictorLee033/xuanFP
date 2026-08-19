# -*- coding: utf-8 -*-
"""扫描历史仓库：scan_runs / scan_results 的读写。"""
import json
import logging
import time

from .database import Database

logger = logging.getLogger(__name__)

_JSON_FIELDS = ("top20", "summary", "stats")


class ScanRepository:
    def __init__(self, db: Database):
        self.db = db

    # ---------- 运行记录 ----------
    def create_run(self, status: str = "running", universe_size: int | None = None) -> int:
        return self.db.execute(
            "INSERT INTO scan_runs (created_at, status, universe_size) VALUES (?,?,?)",
            (time.time(), status, universe_size),
        )

    def update_run(self, run_id: int, **fields) -> None:
        if not fields:
            return
        sets, vals = [], []
        for k, v in fields.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False, default=str)
            sets.append(f"{k}=?")
            vals.append(v)
        vals.append(run_id)
        self.db.execute(f"UPDATE scan_runs SET {', '.join(sets)} WHERE id=?", vals)

    def _row_to_dict(self, row):
        if row is None:
            return None
        d = dict(row)
        for k in _JSON_FIELDS:
            if d.get(k):
                try:
                    d[k] = json.loads(d[k])
                except (ValueError, TypeError):
                    pass
        return d

    def get_run(self, run_id: int):
        return self._row_to_dict(
            self.db.query_one("SELECT * FROM scan_runs WHERE id=?", (run_id,))
        )

    def list_runs(self, limit: int = 50):
        rows = self.db.query_all(
            "SELECT id, created_at, status, universe_size, passed_size, summary, stats "
            "FROM scan_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_dict(r) for r in rows]

    def get_latest_run_id(self):
        row = self.db.query_one(
            "SELECT MAX(id) AS m FROM scan_runs WHERE status='done'"
        )
        return row["m"] if row else None

    def delete_run(self, run_id: int) -> bool:
        """级联删除某次扫描：运行记录 + 全部结果 + LLM 报告。返回是否删除成功。"""
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM scan_runs WHERE id=?", (run_id,))
            if cur.rowcount == 0:
                return False
            conn.execute("DELETE FROM scan_results WHERE run_id=?", (run_id,))
            conn.execute("DELETE FROM llm_reports WHERE run_id=?", (run_id,))
        return True

    # ---------- 结果 ----------
    def save_result(self, run_id, rank, ts_code, name, price, industry,
                    sw_industry, score, dimensions, factors, flags) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO scan_results "
            "(run_id, rank, ts_code, name, price, industry, sw_industry, score, "
            " dimensions, factors, flags) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, rank, ts_code, name, price, industry, sw_industry, score,
             json.dumps(dimensions, ensure_ascii=False),
             json.dumps(factors, ensure_ascii=False),
             json.dumps(flags, ensure_ascii=False)),
        )

    def get_results(self, run_id: int):
        rows = self.db.query_all(
            "SELECT * FROM scan_results WHERE run_id=? ORDER BY rank ASC", (run_id,)
        )
        out = []
        for r in rows:
            d = dict(r)
            for k in ("dimensions", "factors", "flags"):
                if d.get(k):
                    try:
                        d[k] = json.loads(d[k])
                    except (ValueError, TypeError):
                        pass
            out.append(d)
        return out
