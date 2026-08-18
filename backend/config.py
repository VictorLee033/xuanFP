# -*- coding: utf-8 -*-
"""配置加载：config.yaml + 运行时更新（设置页写入）"""
import os
import threading
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("XUANFP_CONFIG", PROJECT_ROOT / "config.yaml"))
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config.local.yaml"   # 本地私有配置（含密钥，不入库）
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DB = DATA_DIR / "xuanfp.db"

_lock = threading.RLock()
_mem_cfg = None  # 内存缓存：设置页更新后即时生效
_defaults = {
    "app": {"host": "127.0.0.1", "port": 8710, "debug": False},
    "tushare": {
        "pcd": {"base_url": "https://pcd.mobcvb.cn/tushare/pro", "api_key": ""},
        "rds": {"base_url": "http://datahubco.com/app-api/openapi/v1/tushare", "api_key": ""},
    },
    "eastmoney": {"clist_url": "https://push2delay.eastmoney.com/api/qt/clist/get",
                  "stock_url": "https://push2delay.eastmoney.com/api/qt/stock/get",
                  "page_size": 100},
    "tencent": {"kline_url": "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                "quote_url": "http://qt.gtimg.cn/q="},
    "sina": {"quote_url": "https://hq.sinajs.cn/list="},
    "llm": {"base_url": "https://api.deepseek.com/v1", "api_key": "", "model": "deepseek-chat",
            "timeout": 90, "top_n_reports": 10},
    "scanner": {"max_workers": 24, "universe_limit": 0, "kline_days": 320, "moneyflow_days": 5,
                "top_list_days": 10, "margin_days": 30,
                "weights": {"value": 12, "quality": 18, "growth": 15, "trend": 13,
                            "momentum": 12, "capital": 13, "chip": 8, "safety": 5, "macro": 4}},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    global _mem_cfg
    with _lock:
        if _mem_cfg is not None:
            return _mem_cfg
        cfg = _deep_merge(_defaults, {})
        if CONFIG_PATH.exists():
            try:
                loaded = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
                cfg = _deep_merge(cfg, loaded)
            except Exception:
                pass
        # 本地私有配置最后合并（含密钥，可覆盖 config.yaml 的空占位）
        if LOCAL_CONFIG_PATH.exists():
            try:
                local = yaml.safe_load(LOCAL_CONFIG_PATH.read_text(encoding="utf-8")) or {}
                cfg = _deep_merge(cfg, local)
            except Exception:
                pass
        _mem_cfg = cfg
        return cfg


def save_config(cfg: dict) -> None:
    with _lock:
        CONFIG_PATH.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                               encoding="utf-8")


def get_config() -> dict:
    return load_config()


def update_config(partial: dict) -> dict:
    """部分更新配置并落盘，返回新配置"""
    global _mem_cfg
    with _lock:
        cfg = load_config()
        cfg = _deep_merge(cfg, partial)
        save_config(cfg)
        _mem_cfg = cfg
        return cfg


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
