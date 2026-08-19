# -*- coding: utf-8 -*-
"""技术指标计算库（纯 numpy，输入为 K线 dict 列表 / OHLCV 数组）。

本模块只负责「计算指标原始值」，返回数值/数组；打分逻辑在 factors.py。
K线格式：bars = [{date, open, close, high, low, volume}, ...]（时间升序）。
"""
import numpy as np


def _arr(bars, key):
    return np.array([b[key] for b in bars], dtype=float)


def closes(bars):
    return _arr(bars, "close")


def highs(bars):
    return _arr(bars, "high")


def lows(bars):
    return _arr(bars, "low")


def volumes(bars):
    return _arr(bars, "volume")


def opens(bars):
    return _arr(bars, "open")


# ----------------------------------------------------------------------
# 均线类
# ----------------------------------------------------------------------
def sma(arr, n):
    """简单移动平均（末尾值）"""
    if len(arr) < n:
        return None
    return float(arr[-n:].mean())


def ema(arr, n):
    """指数移动平均（返回完整序列，前端 nan）"""
    if len(arr) < n:
        return None
    k = 2.0 / (n + 1)
    out = np.empty(len(arr))
    out[:] = np.nan
    out[n - 1] = arr[:n].mean()
    for i in range(n, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def ema_last(arr, n):
    e = ema(arr, n)
    return float(e[-1]) if e is not None else None


# ----------------------------------------------------------------------
# MACD
# ----------------------------------------------------------------------
def macd(arr, fast=12, slow=26, signal=9):
    """返回 (dif, dea, hist) 完整序列（前端 nan）"""
    if len(arr) < slow + signal:
        return None, None, None
    e_fast = ema(arr, fast)
    e_slow = ema(arr, slow)
    dif = e_fast - e_slow
    dea = np.empty(len(arr))
    dea[:] = np.nan
    k = 2.0 / (signal + 1)
    start = slow - 1
    dea[start] = np.nanmean(dif[start:start + signal]) if start + signal <= len(arr) else dif[start]
    for i in range(start + 1, len(arr)):
        if np.isnan(dif[i]):
            dea[i] = np.nan
        else:
            dea[i] = dif[i] * k + dea[i - 1] * (1 - k)
    hist = (dif - dea) * 2
    return dif, dea, hist


# ----------------------------------------------------------------------
# DMI（方向指标）
# ----------------------------------------------------------------------
def dmi(bars, n=14):
    """返回 (pdi, mdi, adx) 末尾值"""
    if len(bars) < n + 1:
        return None, None, None
    high = highs(bars)
    low = lows(bars)
    close = closes(bars)
    tr = np.empty(len(bars))
    tr[0] = high[0] - low[0]
    plus_dm = np.empty(len(bars))
    minus_dm = np.empty(len(bars))
    plus_dm[0] = minus_dm[0] = 0.0
    for i in range(1, len(bars)):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
    tr_sum = tr[-n:].sum()
    if tr_sum <= 0:
        return None, None, None
    pdi = plus_dm[-n:].sum() / tr_sum * 100
    mdi = minus_dm[-n:].sum() / tr_sum * 100
    dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0.0
    # ADX 简化：用当前 DX 与近期均值近似
    adx = float(dx)
    return float(pdi), float(mdi), adx


# ----------------------------------------------------------------------
# TRIX
# ----------------------------------------------------------------------
def trix(arr, n=12, m=20):
    """返回 (trix, matrix) 末尾值"""
    if len(arr) < n + m:
        return None, None
    e1 = ema(arr, n)
    e2 = ema(e1[~np.isnan(e1)], n)
    e3 = ema(e2[~np.isnan(e2)], n)
    if e3 is None or len(e3) < 2:
        return None, None
    t = np.diff(e3) / e3[:-1] * 100
    t = np.concatenate([[0.0], t])
    mtx = np.convolve(t, np.ones(m) / m, mode="full")[:len(t)]
    return float(t[-1]), float(mtx[-1])


# ----------------------------------------------------------------------
# DMA（平行线差）
# ----------------------------------------------------------------------
def dma(arr, n1=10, n2=50):
    if len(arr) < n2:
        return None, None
    ddd = sma(arr, n1)
    ama = sma(arr, n2)
    return ddd, ama


# ----------------------------------------------------------------------
# KDJ
# ----------------------------------------------------------------------
def kdj(bars, n=9):
    if len(bars) < n:
        return None, None, None
    high = highs(bars)
    low = lows(bars)
    close = closes(bars)
    hn = high[-n:].max()
    ln = low[-n:].min()
    if hn == ln:
        rsv = 50.0
    else:
        rsv = (close[-1] - ln) / (hn - ln) * 100
    k = 2.0 / 3 * 50.0 + 1.0 / 3 * rsv  # 简化：K 初始 50
    d = 2.0 / 3 * 50.0 + 1.0 / 3 * k
    j = 3 * k - 2 * d
    return float(k), float(d), float(j)


# ----------------------------------------------------------------------
# CCI
# ----------------------------------------------------------------------
def cci(bars, n=14):
    if len(bars) < n:
        return None
    high = highs(bars)
    low = lows(bars)
    close = closes(bars)
    tp = (high + low + close) / 3
    tp_n = tp[-n:]
    ma = tp_n.mean()
    md = np.abs(tp_n - ma).mean()
    if md == 0:
        return 0.0
    return float((tp[-1] - ma) / (0.015 * md))


# ----------------------------------------------------------------------
# BIAS（乖离率）
# ----------------------------------------------------------------------
def bias(arr, n=6):
    ma = sma(arr, n)
    if ma is None or ma == 0:
        return None
    return (arr[-1] - ma) / ma * 100


# ----------------------------------------------------------------------
# ROC（变动率）
# ----------------------------------------------------------------------
def roc(arr, n=12):
    if len(arr) < n + 1:
        return None
    return (arr[-1] - arr[-1 - n]) / arr[-1 - n] * 100


# ----------------------------------------------------------------------
# WR（威廉指标）
# ----------------------------------------------------------------------
def wr(bars, n=14):
    if len(bars) < n:
        return None
    high = highs(bars)
    low = lows(bars)
    close = closes(bars)
    hn = high[-n:].max()
    ln = low[-n:].min()
    if hn == ln:
        return 50.0
    return float((hn - close[-1]) / (hn - ln) * 100)


# ----------------------------------------------------------------------
# OBV（能量潮）
# ----------------------------------------------------------------------
def obv(bars):
    close = closes(bars)
    vol = volumes(bars)
    obv_arr = np.zeros(len(bars))
    for i in range(1, len(bars)):
        if close[i] > close[i - 1]:
            obv_arr[i] = obv_arr[i - 1] + vol[i]
        elif close[i] < close[i - 1]:
            obv_arr[i] = obv_arr[i - 1] - vol[i]
        else:
            obv_arr[i] = obv_arr[i - 1]
    return obv_arr


def obv_trend(bars, n=20):
    o = obv(bars)
    if len(o) < n + 1:
        return None
    return float(o[-1] - o[-1 - n])


# ----------------------------------------------------------------------
# VR（成交量变异率）
# ----------------------------------------------------------------------
def vr(bars, n=26):
    if len(bars) < n + 1:
        return None
    close = closes(bars)
    vol = volumes(bars)
    up = down = eq = 0.0
    for i in range(-n, 0):
        if close[i] > close[i - 1]:
            up += vol[i]
        elif close[i] < close[i - 1]:
            down += vol[i]
        else:
            eq += vol[i]
    if down == 0:
        return None
    return float((up + eq / 2) / (down + eq / 2) * 100)


# ----------------------------------------------------------------------
# PVT（价量趋势）
# ----------------------------------------------------------------------
def pvt(bars):
    close = closes(bars)
    vol = volumes(bars)
    pvt_arr = np.zeros(len(bars))
    for i in range(1, len(bars)):
        if close[i - 1] != 0:
            pvt_arr[i] = pvt_arr[i - 1] + vol[i] * (close[i] - close[i - 1]) / close[i - 1]
    return pvt_arr


# ----------------------------------------------------------------------
# ATR（真实波幅）
# ----------------------------------------------------------------------
def atr(bars, n=14):
    if len(bars) < n + 1:
        return None
    high = highs(bars)
    low = lows(bars)
    close = closes(bars)
    tr = np.empty(len(bars))
    tr[0] = high[0] - low[0]
    for i in range(1, len(bars)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return float(tr[-n:].mean())


def atr_pct(bars, n=14):
    a = atr(bars, n)
    c = closes(bars)
    if a is None or c[-1] == 0:
        return None
    return a / c[-1] * 100


# ----------------------------------------------------------------------
# 肯特纳通道 KC
# ----------------------------------------------------------------------
def keltner_channel(bars, n=20, mult=2.0):
    if len(bars) < n:
        return None, None, None
    close = closes(bars)
    atr_n = atr(bars, 10)
    mid = sma(close, n)
    if mid is None or atr_n is None:
        return None, None, None
    upper = mid + mult * atr_n
    lower = mid - mult * atr_n
    return upper, mid, lower


# ----------------------------------------------------------------------
# 唐奇安通道 DC
# ----------------------------------------------------------------------
def donchian_channel(bars, n=20):
    if len(bars) < n:
        return None, None, None
    high = highs(bars)
    low = lows(bars)
    upper = high[-n:].max()
    lower = low[-n:].min()
    mid = (upper + lower) / 2
    return upper, mid, lower


# ----------------------------------------------------------------------
# 历史波动率 HV
# ----------------------------------------------------------------------
def hv(arr, n=20, periods=250):
    if len(arr) < n + 1:
        return None
    rets = np.diff(arr[-n - 1:]) / arr[-n - 1:-1]
    return float(np.std(rets, ddof=0) * np.sqrt(periods) * 100)


# ----------------------------------------------------------------------
# 相对强弱 RS / RPS
# ----------------------------------------------------------------------
def rs(stock_returns, bench_returns):
    """个股相对基准的强弱（近 n 日累计超额收益，%）"""
    if len(stock_returns) == 0 or len(bench_returns) != len(stock_returns):
        return None
    s = np.prod(1 + np.asarray(stock_returns, dtype=float)) - 1
    b = np.prod(1 + np.asarray(bench_returns, dtype=float)) - 1
    return float((s - b) * 100)


def rps(stock_return_pct, all_returns_pct):
    """股价相对强度 RPS：个股涨幅在全市场涨幅中的分位（0-100）"""
    if stock_return_pct is None or not all_returns_pct:
        return None
    arr = np.asarray(all_returns_pct, dtype=float)
    return float((arr <= stock_return_pct).sum() / len(arr) * 100)


# ----------------------------------------------------------------------
# Alpha（Jensen's alpha，简化为超额收益年化）
# ----------------------------------------------------------------------
def alpha(stock_returns, bench_returns, periods=250):
    if len(stock_returns) == 0 or len(bench_returns) != len(stock_returns):
        return None
    s = np.asarray(stock_returns, dtype=float)
    b = np.asarray(bench_returns, dtype=float)
    excess = s - b
    return float(excess.mean() * periods * 100)


# ----------------------------------------------------------------------
# 成本均线 CYC（近似：不同周期成本均线 = 各周期 SMA 的组合）
# ----------------------------------------------------------------------
def cyc(arr, n1=5, n2=13, n3=34):
    """成本均线（用 5/13/34 日 SMA 近似筹码成本，返回 (cyc5, cyc13, cyc34)"""
    c1 = sma(arr, n1)
    c2 = sma(arr, n2)
    c3 = sma(arr, n3)
    return c1, c2, c3
