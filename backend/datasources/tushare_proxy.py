# -*- coding: utf-8 -*-
"""兼容占位：Tushare 代理数据源已停用（数据陈旧、限流严重）。

当前数据源为东方财富快照+数据中心 + 腾讯/新浪行情，见 datasources/eastmoney.py、
tencent.py、sina.py。本文件仅为避免旧引用报错而保留，请勿再使用。
"""


class TushareClient:
    """已废弃的占位类，调用会直接报错。"""

    def __init__(self):
        raise RuntimeError("TushareClient 已停用，请使用 EastMoneyClient / TencentClient / SinaClient")

    def invalidate_channels(self):
        pass
