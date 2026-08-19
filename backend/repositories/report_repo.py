# -*- coding: utf-8 -*-
"""LLM 报告仓库：llm_reports 表的读写。"""
import logging
import time

from .database import Database

logger = logging.getLogger(__name__)


class ReportRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, run_id: int, ts_code: str, content: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO llm_reports (run_id, ts_code, content, created_at) "
            "VALUES (?,?,?,?)",
            (run_id, ts_code, content, time.time()),
        )

    def get(self, run_id: int, ts_code: str):
        row = self.db.query_one(
            "SELECT content FROM llm_reports WHERE run_id=? AND ts_code=?",
            (run_id, ts_code),
        )
        return row["content"] if row else None
