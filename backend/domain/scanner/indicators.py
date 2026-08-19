# -*- coding: utf-8 -*-
"""技术指标计算（纯 numpy，输入为 K线 dict 列表）"""
import numpy as np


def closes(bars):
    return np.array([b["close"] for b in bars], dtype=float)


def sma(values, n):
    arr = closes(values) if isinstance(values, list) else np.asarray(values, dtype=float)
    if len(arr) < n:
        return None
    return float(arr[-n:].mean())


def ma_series(arr, n):
    if len(arr) < n:
        return None
    out = np.full(len(arr), np.nan)
    for i in range(n - 1, len(arr)):
        out[i] = arr[i - n + 1:i + 1].mean()
    return out


def rsi(closes_arr, n=14):
    if len(closes_arr) < n + 1:
        return None
    diff = np.diff(closes_arr[-(n + 1):])
    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)
    avg_gain = gains.mean()
    avg_loss = losses.mean()
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def bollinger(closes_arr, n=20, k=2.0):
    if len(closes_arr) < n:
        return None, None, None
    window = closes_arr[-n:]
    mid = float(window.mean())
    std = float(window.std(ddof=0))
    return mid + k * std, mid, mid - k * std


def pearson(x, y):
    if len(x) < 2 or len(y) < 2:
        return None
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def annual_volatility(daily_returns, window=60, periods=250):
    if len(daily_returns) < 20:
        return None
    seg = daily_returns[-window:]
    return float(np.std(seg, ddof=0) * np.sqrt(periods))


def max_drawdown_recovery_days(closes_arr):
    """近一年最大回撤及修复天数（交易日）。返回 (max_dd, recover_days, still_in_dd)"""
    if len(closes_arr) < 30:
        return None, None, None
    arr = closes_arr[-250:]
    peak = arr[0]
    peak_idx = 0
    max_dd = 0.0
    trough_idx = 0
    for i in range(1, len(arr)):
        if arr[i] > peak:
            peak = arr[i]
            peak_idx = i
        dd = (arr[i] - peak) / peak
        if dd < max_dd:
            max_dd = dd
            trough_idx = i
    if max_dd == 0:
        return 0.0, 0, False
    # 从坑底到恢复到前高的天数
    pre_peak = arr[peak_idx] if peak_idx <= trough_idx else max(arr[:trough_idx + 1])
    recover = None
    for j in range(trough_idx + 1, len(arr)):
        if arr[j] >= pre_peak:
            recover = j - trough_idx
            break
    still = recover is None
    return float(abs(max_dd)), recover, still


def beta_vs_bench(stock_returns, bench_returns):
    if len(stock_returns) < 20 or len(bench_returns) != len(stock_returns):
        return None
    s = np.asarray(stock_returns, dtype=float)
    b = np.asarray(bench_returns, dtype=float)
    if np.std(b) == 0:
        return None
    return float(np.cov(s, b)[0, 1] / np.var(b))


def momentum(closes_arr, n):
    if len(closes_arr) < n + 1:
        return None
    return float(closes_arr[-1] / closes_arr[-1 - n] - 1)


def slope(closes_arr, n=5):
    """近 n 日线性斜率（归一化到均价）"""
    if len(closes_arr) < n:
        return None
    y = closes_arr[-n:]
    x = np.arange(n, dtype=float)
    if np.std(y) == 0:
        return 0.0
    k = np.polyfit(x, y, 1)[0]
    return float(k / np.mean(y))
