# -*- coding: utf-8 -*-
"""历史服务：扫描记录列表、最近扫描、两次对比。"""
import logging

from ..errors import NotFoundError

logger = logging.getLogger(__name__)


class HistoryService:
    def __init__(self, scan_repo):
        self.scan_repo = scan_repo

    def latest(self) -> dict:
        run_id = self.scan_repo.get_latest_run_id()
        if not run_id:
            return {"run": None, "results": []}
        run = self.scan_repo.get_run(run_id)
        results = self.scan_repo.get_results(run_id)[:20]
        return {"run": run, "results": results}

    def get(self, run_id: int) -> dict:
        run = self.scan_repo.get_run(run_id)
        if run is None:
            raise NotFoundError("扫描记录不存在")
        return {"run": run, "results": self.scan_repo.get_results(run_id)[:100]}

    def list_runs(self, limit: int = 50) -> dict:
        return {"runs": self.scan_repo.list_runs(limit)}

    def delete(self, run_id: int) -> dict:
        """删除某次扫描记录（级联删除结果与报告）。"""
        if not self.scan_repo.delete_run(run_id):
            raise NotFoundError(f"扫描记录不存在: {run_id}")
        logger.info("已删除扫描记录 run=%s", run_id)
        return {"ok": True, "deleted": run_id}

    def compare(self, a: int, b: int) -> dict:
        ra = self.scan_repo.get_run(a)
        rb = self.scan_repo.get_run(b)
        if ra is None or rb is None:
            raise NotFoundError("扫描记录不存在")
        map_a = {r["ts_code"]: r for r in self.scan_repo.get_results(a)}
        map_b = {r["ts_code"]: r for r in self.scan_repo.get_results(b)}
        up, down, new_in, dropped = [], [], [], []
        for r in self.scan_repo.get_results(b):
            prev = map_a.get(r["ts_code"])
            if prev is None:
                new_in.append(r["ts_code"])
            else:
                diff = r["score"] - prev["score"]
                (up if diff >= 0 else down).append({
                    "ts_code": r["ts_code"], "name": r["name"],
                    "score_b": r["score"], "score_a": prev["score"],
                    "diff": round(diff, 2), "rank_b": r["rank"], "rank_a": prev["rank"],
                })
        for r in self.scan_repo.get_results(a):
            if r["ts_code"] not in map_b:
                dropped.append(r["ts_code"])
        up.sort(key=lambda x: -x["diff"])
        down.sort(key=lambda x: x["diff"])
        return {
            "run_a": {"id": a, "date": (ra.get("stats") or {}).get("date")},
            "run_b": {"id": b, "date": (rb.get("stats") or {}).get("date")},
            "up": up[:20], "down": down[:20],
            "new_in": new_in[:20], "dropped": dropped[:20],
        }
