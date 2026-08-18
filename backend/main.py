# -*- coding: utf-8 -*-
"""xuanFP FastAPI 入口"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config as cfg
from .api import router as api_router
from .storage import db

FRONTEND_STATIC = Path(__file__).resolve().parent.parent / "frontend" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.get_conn()
    yield


app = FastAPI(title="xuanFP 智能股票工作台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/ping")
def ping():
    return {"service": "xuanFP", "docs": "/docs"}


if FRONTEND_STATIC.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_STATIC), html=True), name="frontend")


def main():
    import uvicorn
    c = cfg.get_config()["app"]
    uvicorn.run("backend.main:app", host=c["host"], port=c["port"], reload=False)


if __name__ == "__main__":
    main()
