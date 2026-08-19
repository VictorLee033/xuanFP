# -*- coding: utf-8 -*-
"""兼容占位：接口层已迁移到 backend/api/ 包（见 ARCHITECTURE.md）。

本文件为历史遗留的平级同名模块，Python 导入时以 `api/` 包为准。
保留此占位仅为避免旧引用报错，请勿在此新增代码。
"""
from .api.router import router  # noqa: F401  (转发到新路由)
