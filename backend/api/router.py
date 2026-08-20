# -*- coding: utf-8 -*-
"""HTTP 接口层（薄）：只做参数校验与调用服务，不含业务逻辑。"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import config as cfg
from ..errors import DataSourceError, NotFoundError
from ..llm import reporter
from .schemas import ConfigBody, ScanBody

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def get_container(request: Request):
    return request.app.state.container


# ---------------- 扫描 ----------------
@router.post("/scan")
def start_scan(body: ScanBody | None = None, request: Request = None):
    mode = (body.mode if body else None) or "normal"
    started = request.app.state.container.scan.start(mode)
    return {"ok": True, "started": started, "mode": mode}


@router.get("/scan/progress")
def scan_progress(request: Request):
    return request.app.state.container.scan.get_progress()


@router.get("/scan/latest")
def latest_scan(request: Request):
    return request.app.state.container.history.latest()


@router.get("/scan/{run_id}")
def scan_result(run_id: int, request: Request):
    try:
        return request.app.state.container.history.get(run_id)
    except NotFoundError as e:
        raise HTTPException(404, str(e))


# ---------------- 行情 ----------------
@router.get("/market/overview")
def market_overview(request: Request):
    return request.app.state.container.market.overview()


@router.get("/kline/{ts_code}")
def kline(ts_code: str, days: int = Query(250, ge=20, le=1000), request: Request = None):
    try:
        return request.app.state.container.market.kline(ts_code, days)
    except DataSourceError as e:
        raise HTTPException(502, str(e))


@router.get("/stocks/{ts_code}/detail")
def stock_detail(ts_code: str, run_id: int | None = None, request: Request = None):
    try:
        return request.app.state.container.market.stock_detail(ts_code, run_id)
    except NotFoundError as e:
        raise HTTPException(404, str(e))
    except DataSourceError as e:
        raise HTTPException(502, str(e))


# ---------------- 历史 ----------------
@router.get("/history")
def history(limit: int = Query(50, ge=1, le=200), request: Request = None):
    return request.app.state.container.history.list_runs(limit)


@router.get("/history/compare")
def history_compare(a: int, b: int, request: Request = None):
    try:
        return request.app.state.container.history.compare(a, b)
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@router.delete("/history/{run_id}")
def history_delete(run_id: int, request: Request = None):
    try:
        return request.app.state.container.history.delete(run_id)
    except NotFoundError as e:
        raise HTTPException(404, str(e))


# ---------------- Top5 回测 ----------------
@router.get("/backtest/records")
def backtest_records(request: Request = None):
    return request.app.state.container.backtest.records()


@router.get("/backtest")
def backtest(n: int = Query(5, ge=1, le=60),
             mode: str = Query("normal", pattern="^(normal|short)$"),
             request: Request = None):
    return request.app.state.container.backtest.run(n, mode)


# ---------------- 14:25 邮件推送 ----------------
@router.post("/push/schedule")
def push_schedule(request: Request = None):
    return request.app.state.container.push.schedule()


@router.post("/push/cancel")
def push_cancel(request: Request = None):
    return request.app.state.container.push.cancel()


@router.post("/push/preview")
def push_preview(request: Request = None):
    return request.app.state.container.push.preview()


@router.get("/push/status")
def push_status(request: Request = None):
    return request.app.state.container.push.status()


# ---------------- 配置 ----------------
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
        "mail": {"smtp_host": c["mail"]["smtp_host"], "smtp_port": c["mail"]["smtp_port"],
                 "sender": c["mail"]["sender"], "auth_code": c["mail"]["auth_code"],
                 "recipient": c["mail"]["recipient"]},
        "llm_available": reporter.llm_available(),
    }


@router.put("/config")
def put_api_config(body: ConfigBody, request: Request):
    public, secrets = {}, {}
    # ---- LLM：公共字段进 yaml，api_key 只进 local ----
    if body.llm is not None:
        pub = {k: v for k, v in body.llm.items() if v is not None and k != "api_key"}
        if pub:
            public["llm"] = pub
        if body.llm.get("api_key") is not None:
            secrets.setdefault("llm", {})["api_key"] = body.llm["api_key"]
    # ---- Tushare：base_url 进 yaml，api_key 只进 local ----
    if body.tushare is not None:
        t_pub, t_sec = {}, {}
        if body.tushare.get("pcd_base_url") is not None:
            t_pub.setdefault("pcd", {})["base_url"] = body.tushare["pcd_base_url"]
        if body.tushare.get("rds_base_url") is not None:
            t_pub.setdefault("rds", {})["base_url"] = body.tushare["rds_base_url"]
        if body.tushare.get("pcd_api_key") is not None:
            t_sec.setdefault("pcd", {})["api_key"] = body.tushare["pcd_api_key"]
        if body.tushare.get("rds_api_key") is not None:
            t_sec.setdefault("rds", {})["api_key"] = body.tushare["rds_api_key"]
        if t_pub:
            public["tushare"] = t_pub
        if t_sec:
            secrets["tushare"] = t_sec
    # ---- 邮件：全部含授权码，只进 local ----
    if body.mail is not None:
        m = {k: v for k, v in body.mail.items() if v is not None}
        if m:
            secrets["mail"] = m
    if public:
        cfg.update_config(public)
    if secrets:
        cfg.update_local_config(secrets)
    request.app.state.container.reload_datasources()
    return {"ok": True, "llm_available": reporter.llm_available()}


# ---------------- 健康检查 ----------------
@router.get("/health")
def health(request: Request):
    db_ok = True
    try:
        request.app.state.container.db.query_one("SELECT 1")
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "time": time.time(),
        "scan_running": request.app.state.container.scan.get_progress()["running"],
    }


@router.get("/ping")
def ping():
    return {"service": "xuanFP", "docs": "/docs"}
