# -*- coding: utf-8 -*-
"""结构化日志：统一格式、同时输出到控制台与文件，便于排障。

用法：各模块 `import logging; logger = logging.getLogger(__name__)`，
在 main.py 组合根调用 `setup_logging()` 一次即可。
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import PROJECT_ROOT, DATA_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level=logging.INFO) -> None:
    """初始化日志（幂等，可重复调用）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if getattr(root, "_xuanfp_configured", False):
        return
    root.setLevel(level)

    fmt = logging.Formatter(_LOG_FORMAT)

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 滚动文件（单文件 5MB，保留 3 份）
    try:
        file_handler = RotatingFileHandler(
            Path(DATA_DIR) / "xuanfp.log",
            maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except Exception:  # 文件日志失败不影响程序运行
        pass

    # 降低第三方库噪音
    for noisy in ("urllib3", "requests", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root._xuanfp_configured = True  # type: ignore[attr-defined]
    logging.getLogger(__name__).info("日志系统初始化完成")
