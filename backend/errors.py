# -*- coding: utf-8 -*-
"""类型化异常体系：防御式编程的统一错误边界。

约定：
- 数据源/外部 IO 失败 → DataSourceError（上层可捕获做降级/重试）
- 配置错误 → ConfigurationError（启动即暴露，不该被吞掉）
- 数据不存在 → NotFoundError（业务层面可预期的空结果）
- 其余未预期异常照常抛出，由最外层统一记录并返回友好信息。
"""
import re


class XuanFPError(Exception):
    """xuanFP 所有业务异常的基类。"""


class DataSourceError(XuanFPError):
    """外部数据源请求失败（网络、限流、WAF、解析失败等）。"""


class ConfigurationError(XuanFPError):
    """配置缺失或非法。"""


class NotFoundError(XuanFPError):
    """请求的资源/记录不存在。"""


def friendly_message(exc: BaseException, max_len: int = 300) -> str:
    """把异常转成可读的友好信息：剥离 HTML/WAF 页面、压缩空白、截断。"""
    msg = str(exc)
    msg = re.sub(r"<!DOCTYPE.*", "<HTML拦截页…>", msg, flags=re.IGNORECASE | re.DOTALL)
    msg = msg.replace("\n", " ").replace("\r", " ")
    msg = re.sub(r"\s+", " ", msg)
    return msg[:max_len]
