# -*- coding: utf-8 -*-
"""数据缓存读写（data_cache 表）"""
import json

from .db import get_conn


def cache_get(key):
    conn = get_conn()
    row = conn.execute(
        "SELECT payload FROM data_cache WHERE key=? AND expire_at > ?",
        (key, __import__("time").time()),
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row["payload"])
    except Exception:
        return None


def cache_set(key, value, ttl_seconds=86400):
    import time
    conn = get_conn()
    payload = json.dumps(value, ensure_ascii=False, default=str)
    conn.execute(
        "INSERT OR REPLACE INTO data_cache (key, payload, created_at, expire_at) VALUES (?,?,?,?)",
        (key, payload, time.time(), time.time() + ttl_seconds),
    )
    conn.commit()


def cache_delete_prefix(prefix):
    conn = get_conn()
    conn.execute("DELETE FROM data_cache WHERE key LIKE ?", (prefix + "%",))
    conn.commit()


def cache_stats():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS n FROM data_cache").fetchone()
    return {"entries": row["n"] if row else 0}
