# -*- coding: utf-8 -*-
"""推送任务仓库：push_jobs 表（单行语义，id 恒为 1）。"""
import logging
import time

from .database import Database

logger = logging.getLogger(__name__)


class PushRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, target_date: str, target_time: str, status: str = "pending") -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO push_jobs "
            "(id, target_date, target_time, status, created_at, last_send_at, last_error) "
            "VALUES (1,?,?,?,?,NULL,NULL)",
            (target_date, target_time, status, time.time()),
        )

    def get(self) -> dict | None:
        row = self.db.query_one("SELECT * FROM push_jobs WHERE id=1")
        return dict(row) if row else None

    def mark_sent(self, ok: bool, error: str = "") -> None:
        if ok:
            self.db.execute(
                "UPDATE push_jobs SET status='done', last_send_at=?, last_error=NULL WHERE id=1",
                (time.time(),),
            )
        else:
            self.db.execute(
                "UPDATE push_jobs SET status='failed', last_send_at=?, last_error=? WHERE id=1",
                (time.time(), error[:500]),
            )

    def mark_missed(self, error: str = "错过时间窗口") -> None:
        self.db.execute(
            "UPDATE push_jobs SET status='missed', last_error=? WHERE id=1", (error,)
        )

    def clear(self) -> None:
        self.db.execute("DELETE FROM push_jobs WHERE id=1")
