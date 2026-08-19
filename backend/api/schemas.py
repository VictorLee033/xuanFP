# -*- coding: utf-8 -*-
"""接口层请求/响应模型。"""
from pydantic import BaseModel


class ConfigBody(BaseModel):
    llm: dict | None = None
    tushare: dict | None = None
