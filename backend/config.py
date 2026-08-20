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
# 数据库路径可用环境变量覆盖（默认 data/xuanfp_data.db）
# 注：旧版本使用的 xuanfp.db 因历史 ACL 锁定已废弃，改用新文件名避免只读问题
CACHE_DB = Path(os.environ.get("XUANFP_DB", DATA_DIR / "xuanfp_data.db"))

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
    "presets": {"short": {"label": "短线", "pe_max": 300,
                          "weights": {"value": 5, "quality": 8, "growth": 8, "trend": 18,
                                      "momentum": 16, "capital": 16, "chip": 16,
                                      "safety": 8, "macro": 5}}},
    "mail": {"smtp_host": "smtp.qq.com", "smtp_port": 465,
             "sender": "", "auth_code": "", "recipient": ""},
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


_SECRET_KEYS = {"api_key", "auth_code"}


def _strip_secrets(node):
    """递归剔除密钥字段值（置空），防止真实密钥被写回公共 config.yaml。"""
    if isinstance(node, dict):
        return {k: ("" if k in _SECRET_KEYS else _strip_secrets(v)) for k, v in node.items()}
    if isinstance(node, list):
        return [_strip_secrets(x) for x in node]
    return node


def update_config(partial: dict) -> dict:
    """更新**公共配置**并落盘到 config.yaml（自动剔除密钥字段，密钥只进 local 文件）。"""
    global _mem_cfg
    with _lock:
        file_cfg = {}
        if CONFIG_PATH.exists():
            try:
                file_cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
            except Exception:
                file_cfg = {}
        merged = _deep_merge(_strip_secrets(file_cfg), partial)
        CONFIG_PATH.write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False),
                               encoding="utf-8")
        _mem_cfg = None
        return load_config()


def update_local_config(partial: dict) -> dict:
    """更新**本地私有配置**（config.local.yaml，含密钥，不入库），返回新配置。"""
    global _mem_cfg
    with _lock:
        local = {}
        if LOCAL_CONFIG_PATH.exists():
            try:
                local = yaml.safe_load(LOCAL_CONFIG_PATH.read_text(encoding="utf-8")) or {}
            except Exception:
                local = {}
        local = _deep_merge(local, partial)
        LOCAL_CONFIG_PATH.write_text(yaml.safe_dump(local, allow_unicode=True, sort_keys=False),
                                     encoding="utf-8")
        _mem_cfg = None
        return load_config()


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
