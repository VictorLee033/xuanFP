# -*- coding: utf-8 -*-
"""FastAPI 路由：扫描 / 行情 / 详情 / 历史对比 / 配置"""
import re
import threading
import time
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import config as cfg
from .datasources import TushareClient, EastMoneyClient, TencentClient, SinaClient
from .llm import reporter
from .scanner.engine import ScanEngine
from .storage import history as hist

router = APIRouter(prefix="/api")


def _clean_error(e):
    """把异常信息整理成可读文本（去掉 HTML/WAF 页面内容）"""
    msg = str(e)
    msg = re.sub(r"<!DOCTYPE.*", "<HTML拦截页…>", msg, flags=re.IGNORECASE | re.DOTALL)
    msg = msg.replace("\n", " ").replace("\r", "")
    return msg[:300]

# ---------------- 扫描状态管理 ----------------
_scan_state = {"running": False, "run_id": None,
               "phase": "idle", "done": 0, "total": 0, "message": "",
               "last_error": None, "finished_at": None}
_state_lock = threading.Lock()


def _set_progress(phase, done, total, message):
    with _state_lock:
        _scan_state.update(phase=phase, done=done, total=total, message=message)


def _run_scan_async():
    with _state_lock:
        if _scan_state["running"]:
            return _scan_state["run_id"]
        _scan_state.update(running=True, phase="start", done=0, total=1,
                           message="初始化…", last_error=None)
    engine = ScanEngine(progress=_set_progress)

    def worker():
        try:
            result = engine.run()
            with _state_lock:
                _scan_state.update(running=False, run_id=result["run_id"], phase="done",
                                   done=1, total=1, message="扫描完成",
                                   finished_at=time.time())
            # 后台生成 LLM 报告（Top N）
            threading.Thread(target=_gen_reports, args=(result["run_id"],),
                             daemon=True).start()
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            with _state_lock:
                _scan_state.update(running=False, phase="failed",
                                   message=f"扫描失败: {_clean_error(e)}",
                                   last_error=_clean_error(e),
                                   finished_at=time.time())

    threading.Thread(target=worker, daemon=True).start()
    return None


def _gen_reports(run_id):
    top_n = cfg.get_config()["llm"].get("top_n_reports", 10)
    results = hist.get_results(run_id)[:top_n]
    summary = (hist.get_run(run_id) or {}).get("summary") or {}
    market_text = reporter.generate_market_summary(summary)
    for r in results:
        try:
            if hist.get_report(run_id, r["ts_code"]):
                continue
            report = reporter.generate_report(r, market_text)
            hist.save_report(run_id, r["ts_code"], report)
        except Exception:
            continue


# ---------------- 扫描 ----------------
@router.post("/scan")
def start_scan():
    run_id = _run_scan_async()
    return {"ok": True, "run_id": run_id}


@router.get("/scan/progress")
def scan_progress():
    with _state_lock:
        return dict(_scan_state)


@router.get("/scan/latest")
def latest_scan():
    run_id = hist.get_latest_run_id()
    if not run_id:
        return {"run": None, "results": []}
    run = hist.get_run(run_id)
    results = hist.get_results(run_id)[:20]
    return {"run": run, "results": results}


@router.get("/scan/{run_id}")
def scan_result(run_id: int):
    run = hist.get_run(run_id)
    if not run:
        raise HTTPException(404, "扫描记录不存在")
    results = hist.get_results(run_id)
    return {"run": run, "results": results[:100]}


# ---------------- 行情 ----------------
@router.get("/market/overview")
def market_overview():
    em = EastMoneyClient()
    tx = TencentClient()
    try:
        snaps = em.market_snapshot()
        snaps.sort(key=lambda s: (s.get("pct_chg") or 0), reverse=True)
        top_gainers = [{"ts_code": s["ts_code"], "name": s["name"], "price": s["price"],
                        "pct_chg": s["pct_chg"], "industry": s["industry"],
                        "amount": s["amount"], "turnover_rate": s["turnover_rate"]}
                       for s in snaps[:10] if s.get("pct_chg") is not None]
        top_losers = [{"ts_code": s["ts_code"], "name": s["name"], "price": s["price"],
                       "pct_chg": s["pct_chg"], "industry": s["industry"]}
                      for s in snaps[-10:] if s.get("pct_chg") is not None]
    except Exception:
        top_gainers, top_losers = [], []
    # 指数
    indices = {}
    try:
        q = tx.realtime(["000001.SH", "399001.SZ", "399006.SZ", "000300.SH"])
        for code, v in q.items():
            indices[code] = {"name": v["name"], "price": v["price"],
                             "pct_chg": v["pct_chg"]}
    except Exception:
        pass
    return {"indices": indices, "top_gainers": top_gainers, "top_losers": top_losers,
            "total": len(top_gainers) and 0}


@router.get("/kline/{ts_code}")
def kline(ts_code: str, days: int = 250):
    tx = TencentClient()
    try:
        bars = tx.kline(ts_code, days=days)
    except Exception as e:
        raise HTTPException(502, f"K线获取失败: {e}")
    return {"ts_code": ts_code, "bars": bars}


# ---------------- 个股详情 ----------------
@router.get("/stocks/{ts_code}/detail")
def stock_detail(ts_code: str, run_id: int = None):
    if run_id is None:
        run_id = hist.get_latest_run_id()
    if not run_id:
        raise HTTPException(404, "暂无扫描记录，请先运行扫描")
    results = hist.get_results(run_id)
    stock = next((r for r in results if r["ts_code"] == ts_code), None)
    if not stock:
        raise HTTPException(404, "该股票不在最近扫描结果中")
    report = hist.get_report(run_id, ts_code)
    tx = TencentClient()
    try:
        bars = tx.kline(ts_code, days=250)
    except Exception:
        bars = []
    return {"stock": stock, "report": report, "kline": bars}


# ---------------- 历史 ----------------
@router.get("/history")
def history(limit: int = 50):
    runs = hist.list_runs(limit)
    return {"runs": runs}


@router.get("/history/compare")
def history_compare(a: int, b: int):
    ra = hist.get_run(a)
    rb = hist.get_run(b)
    if not ra or not rb:
        raise HTTPException(404, "扫描记录不存在")
    res_a = hist.get_results(a)
    res_b = hist.get_results(b)
    map_a = {r["ts_code"]: r for r in res_a}
    map_b = {r["ts_code"]: r for r in res_b}
    up, down, new_in, dropped = [], [], [], []
    for r in res_b:
        prev = map_a.get(r["ts_code"])
        if not prev:
            new_in.append(r["ts_code"])
        else:
            diff = r["score"] - prev["score"]
            (up if diff >= 0 else down).append(
                {"ts_code": r["ts_code"], "name": r["name"], "score_b": r["score"],
                 "score_a": prev["score"], "diff": round(diff, 2),
                 "rank_b": r["rank"], "rank_a": prev["rank"]})
    for r in res_a:
        if r["ts_code"] not in map_b:
            dropped.append(r["ts_code"])
    up.sort(key=lambda x: -x["diff"])
    down.sort(key=lambda x: x["diff"])
    return {"run_a": {"id": a, "date": ra.get("stats", {}).get("date")},
            "run_b": {"id": b, "date": rb.get("stats", {}).get("date")},
            "up": up[:20], "down": down[:20],
            "new_in": new_in[:20], "dropped": dropped[:20]}


# ---------------- 配置 ----------------
class ConfigBody(BaseModel):
    llm: dict | None = None
    tushare: dict | None = None


@router.get("/config")
def get_api_config():
    c = cfg.get_config()
    return {
        "llm": {"base_url": c["llm"]["base_url"], "api_key": c["llm"]["api_key"],
                "model": c["llm"]["model"], "top_n_reports": c["llm"]["top_n_reports"]},
        "tushare": {"pcd_base_url": c["tushare"]["pcd"]["base_url"],
                    "pcd_api_key": c["tushare"]["pcd"]["api_key"],
                    "rds_base_url": c["tushare"]["rds"]["base_url"],
                    "rds_api_key": c["tushare"]["rds"]["api_key"]},
        "llm_available": reporter.llm_available(),
    }


@router.put("/config")
def put_api_config(body: ConfigBody):
    partial = {}
    if body.llm is not None:
        partial["llm"] = {k: v for k, v in body.llm.items() if v is not None}
    if body.tushare is not None:
        t = {}
        if body.tushare.get("pcd_api_key") is not None:
            t.setdefault("pcd", {})["api_key"] = body.tushare["pcd_api_key"]
        if body.tushare.get("pcd_base_url") is not None:
            t.setdefault("pcd", {})["base_url"] = body.tushare["pcd_base_url"]
        if body.tushare.get("rds_api_key") is not None:
            t.setdefault("rds", {})["api_key"] = body.tushare["rds_api_key"]
        if body.tushare.get("rds_base_url") is not None:
            t.setdefault("rds", {})["base_url"] = body.tushare["rds_base_url"]
        if t:
            partial["tushare"] = t
    new_cfg = cfg.update_config(partial)
    # 失效数据源客户端缓存
    TushareClient().invalidate_channels()
    EastMoneyClient().invalidate()
    TencentClient().invalidate()
    SinaClient().invalidate()
    return {"ok": True, "llm_available": reporter.llm_available()}


@router.get("/health")
def health():
    return {"status": "ok", "time": time.time()}
