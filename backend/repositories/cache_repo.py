# -*- coding: utf-8 -*-
"""数据缓存仓库：data_cache 表的读写（供数据源层做 TTL 缓存）"""
import json
import logging
import time

from .database import Database

logger = logging.getLogger(__name__)


class CacheRepository:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str):
        row = self.db.query_one(
            "SELECT payload FROM data_cache WHERE key=? AND expire_at > ?",
            (key, time.time()),
        )
        if row is None:
            return None
        try:
            return json.loads(row["payload"])
        except (ValueError, TypeError):
            return None

    def set(self, key: str, value, ttl_seconds: int = 86400) -> None:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        self.db.execute(
            "INSERT OR REPLACE INTO data_cache (key, payload, created_at, expire_at) "
            "VALUES (?,?,?,?)",
            (key, payload, time.time(), time.time() + ttl_seconds),
        )

    def delete_prefix(self, prefix: str) -> None:
        self.db.execute("DELETE FROM data_cache WHERE key LIKE ?", (prefix + "%",))
