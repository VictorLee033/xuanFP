# -*- coding: utf-8 -*-
"""SQLite 数据访问基础设施。

设计要点（防御型 / 正确使用 SQLite）：
- WAL 模式 + busy_timeout：读写并发更稳，避免 "database is locked"
- 线程本地连接：每个工作线程持有一条独立连接，避免跨线程共享连接导致的
  事务快照/可见性不一致（此前踩过的坑）
- autocommit(isolation_level=None)：单条语句即提交，读取永远看到最新已提交数据
- 版本化迁移：schema_migrations 表 + 有序迁移列表，后续加字段/表只增不改
"""
import logging
import sqlite3
import threading
from pathlib import Path

from ..errors import ConfigurationError

logger = logging.getLogger(__name__)

# 有序迁移：(版本号, [SQL 语句列表])，只允许追加，不允许修改历史条目
MIGRATIONS = [
    (
        "0001_initial",
        [
            """
            CREATE TABLE IF NOT EXISTS data_cache (
                key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                expire_at REAL NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_cache_expire ON data_cache(expire_at)",
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                status TEXT NOT NULL,
                universe_size INTEGER,
                passed_size INTEGER,
                top20 TEXT,
                summary TEXT,
                stats TEXT,
                error TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scan_results (
                run_id INTEGER NOT NULL,
                rank INTEGER,
                ts_code TEXT NOT NULL,
                name TEXT,
                price REAL,
                industry TEXT,
                sw_industry TEXT,
                score REAL,
                dimensions TEXT,
                factors TEXT,
                flags TEXT,
                PRIMARY KEY (run_id, ts_code)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_results_run ON scan_results(run_id)",
            """
            CREATE TABLE IF NOT EXISTS llm_reports (
                run_id INTEGER NOT NULL,
                ts_code TEXT NOT NULL,
                content TEXT,
                created_at REAL,
                PRIMARY KEY (run_id, ts_code)
            )
            """,
        ],
    ),
    (
        "0002_top5_records",
        [
            """
            CREATE TABLE IF NOT EXISTS top5_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                rank INTEGER NOT NULL,
                ts_code TEXT NOT NULL,
                name TEXT,
                close_price REAL,
                pct_chg REAL,
                amount REAL,
                total_mv REAL,
                score REAL,
                industry TEXT,
                sw_industry TEXT,
                tags TEXT,
                dimensions TEXT,
                created_at REAL NOT NULL,
                UNIQUE(trade_date, rank)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_top5_date ON top5_records(trade_date)",
        ],
    ),
]


class Database:
    """SQLite 连接与迁移管理。"""

    def __init__(self, path: str | Path):
        self.path = str(path)
        parent = Path(self.path).parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ConfigurationError(f"无法创建数据目录 {parent}: {e}") from e
        self._local = threading.local()
        self._migrate_lock = threading.Lock()
        self._migrate()
        logger.info("SQLite 数据库就绪: %s", self.path)

    # ------------------------------------------------------------------
    def _new_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0,
                               isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def conn(self) -> sqlite3.Connection:
        """返回当前线程的独占连接（懒创建）。"""
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self._new_conn()
            self._local.conn = c
        return c

    def close(self) -> None:
        c = getattr(self._local, "conn", None)
        if c is not None:
            try:
                c.close()
            except Exception:
                pass
            self._local.conn = None

    # ------------------------------------------------------------------
    def _migrate(self) -> None:
        with self._migrate_lock:
            conn = self._new_conn()
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS schema_migrations "
                    "(version TEXT PRIMARY KEY, applied_at REAL NOT NULL)"
                )
                applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
                for version, statements in MIGRATIONS:
                    if version in applied:
                        continue
                    conn.execute("BEGIN IMMEDIATE")
                    try:
                        for sql in statements:
                            conn.execute(sql)
                        conn.execute(
                            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                            (version, __import__("time").time()),
                        )
                        conn.execute("COMMIT")
                        logger.info("应用迁移 %s", version)
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # 便捷查询（autocommit 下每次都是独立事务，读取最新已提交数据）
    def execute(self, sql: str, params=()) -> int:
        """执行写语句，返回 lastrowid。"""
        cur = self.conn().execute(sql, params)
        return cur.lastrowid

    def query_one(self, sql: str, params=()):
        return self.conn().execute(sql, params).fetchone()

    def query_all(self, sql: str, params=()):
        return self.conn().execute(sql, params).fetchall()

    def transaction(self):
        """多语句事务上下文：with db.transaction(): ...（异常自动回滚）"""
        return _Tx(self.conn())


class _Tx:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.execute("COMMIT")
        else:
            self.conn.execute("ROLLBACK")
        return False
