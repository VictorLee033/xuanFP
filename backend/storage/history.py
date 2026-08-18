# -*- coding: utf-8 -*-
"""扫描历史存档：scan_runs / scan_results / llm_reports"""
import json
import time

from .db import tx, get_conn


def create_run(status="running", universe_size=None):
    with tx() as cur:
        cur.execute(
            "INSERT INTO scan_runs (created_at, status, universe_size) VALUES (?,?,?)",
            (time.time(), status, universe_size),
        )
        return cur.lastrowid


def update_run(run_id, **fields):
    sets = []
    vals = []
    for k, v in fields.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k}=?")
        vals.append(v)
    if not sets:
        return
    vals.append(run_id)
    with tx() as cur:
        cur.execute(f"UPDATE scan_runs SET {', '.join(sets)} WHERE id=?", vals)


def get_run(run_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM scan_runs WHERE id=?", (run_id,)).fetchone()
    return _run_row(row) if row else None


def _run_row(row):
    d = dict(row)
    for k in ("top20", "summary", "stats"):
        if d.get(k):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d


def list_runs(limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, created_at, status, universe_size, passed_size, summary, stats FROM scan_runs "
        "ORDER BY id DESC LIMIT ?", (limit,),
    ).fetchall()
    return [_run_row(r) for r in rows]


def save_result(run_id, rank, ts_code, name, price, industry, sw_industry, score, dimensions, factors, flags):
    with tx() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO scan_results "
            "(run_id, rank, ts_code, name, price, industry, sw_industry, score, dimensions, factors, flags) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, rank, ts_code, name, price, industry, sw_industry, score,
             json.dumps(dimensions, ensure_ascii=False),
             json.dumps(factors, ensure_ascii=False),
             json.dumps(flags, ensure_ascii=False)),
        )


def get_results(run_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM scan_results WHERE run_id=? ORDER BY rank ASC", (run_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("dimensions", "factors", "flags"):
            if d.get(k):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        out.append(d)
    return out


def save_report(run_id, ts_code, content):
    with tx() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO llm_reports (run_id, ts_code, content, created_at) VALUES (?,?,?,?)",
            (run_id, ts_code, content, time.time()),
        )


def get_report(run_id, ts_code):
    conn = get_conn()
    row = conn.execute(
        "SELECT content FROM llm_reports WHERE run_id=? AND ts_code=?", (run_id, ts_code),
    ).fetchone()
    return row["content"] if row else None


def get_latest_run_id():
    conn = get_conn()
    row = conn.execute("SELECT MAX(id) AS m FROM scan_runs WHERE status='done'").fetchone()
    return row["m"] if row else None
