# -*- coding: utf-8 -*-
"""xuanFP 入口（组合根）：装配依赖、注册路由、挂载静态前端。"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config as cfg
from .api import router
from .container import build_container
from .errors import (ConfigurationError, DataSourceError, NotFoundError,
                     XuanFPError, friendly_message)
from .logging_config import setup_logging

logger = logging.getLogger(__name__)

FRONTEND_STATIC = Path(__file__).resolve().parent.parent / "frontend" / "static"

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = build_container()
    app.state.container = container
    logger.info("xuanFP 启动完成")
    yield
    container.close()


app = FastAPI(title="xuanFP 智能股票工作台", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# 全局异常兜底：类型化异常统一转友好 JSON（未被路由捕获的也安全）
@app.exception_handler(XuanFPError)
async def xuanfp_error_handler(request, exc: XuanFPError):
    status = 500
    if isinstance(exc, NotFoundError):
        status = 404
    elif isinstance(exc, DataSourceError):
        status = 502
    elif isinstance(exc, ConfigurationError):
        status = 500
    logger.warning("请求异常 [%s] %s: %s", getattr(request, "url", "?"), type(exc).__name__, exc)
    return JSONResponse(status_code=status, content={"detail": friendly_message(exc)})


app.include_router(router)

if FRONTEND_STATIC.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_STATIC), html=True), name="frontend")


def main():
    import uvicorn
    c = cfg.get_config()["app"]
    uvicorn.run("backend.main:app", host=c["host"], port=c["port"], reload=False)


if __name__ == "__main__":
    main()
