# -*- coding: utf-8 -*-
"""SQLite 存储：数据缓存 + 扫描历史 + LLM 报告"""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager

from ..config import ensure_data_dir, CACHE_DB

ensure_data_dir()

_conn = None
_lock = threading.RLock()


def get_conn() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(str(CACHE_DB), check_same_thread=False,
                                    isolation_level=None)  # autocommit，避免多线程读不到已提交数据
            _conn.row_factory = sqlite3.Row
            _init_schema(_conn)
        return _conn


def _init_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS data_cache (
        key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        created_at REAL NOT NULL,
        expire_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_cache_expire ON data_cache(expire_at);

    CREATE TABLE IF NOT EXISTS stocks (
        ts_code TEXT PRIMARY KEY,
        name TEXT,
        industry TEXT,
        list_date TEXT,
        market TEXT,
        updated_at REAL
    );

    CREATE TABLE IF NOT EXISTS scan_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at REAL NOT NULL,
        status TEXT NOT NULL,          -- running / done / failed
        universe_size INTEGER,
        passed_size INTEGER,
        top20 TEXT,                    -- JSON 列表
        summary TEXT,                  -- JSON {top3_logic, industry_stats}
        stats TEXT,                    -- JSON {duration, date}
        error TEXT
    );

    CREATE TABLE IF NOT EXISTS scan_results (
        run_id INTEGER NOT NULL,
        rank INTEGER,
        ts_code TEXT,
        name TEXT,
        price REAL,
        industry TEXT,
        sw_industry TEXT,
        score REAL,
        dimensions TEXT,               -- JSON 九维得分
        factors TEXT,                  -- JSON 因子明细
        flags TEXT,                    -- JSON ["强烈关注"] 等
        PRIMARY KEY (run_id, ts_code)
    );

    CREATE TABLE IF NOT EXISTS llm_reports (
        run_id INTEGER NOT NULL,
        ts_code TEXT NOT NULL,
        content TEXT,
        created_at REAL,
        PRIMARY KEY (run_id, ts_code)
    );
    """)
    # 迁移：为旧库补 sw_industry 列
    cols = [r[1] for r in conn.execute("PRAGMA table_info(scan_results)").fetchall()]
    if "sw_industry" not in cols:
        conn.execute("ALTER TABLE scan_results ADD COLUMN sw_industry TEXT")


@contextmanager
def tx():
    conn = get_conn()
    with _lock:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def now():
    return time.time()
