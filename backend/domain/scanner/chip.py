# -*- coding: utf-8 -*-
"""筹码分布（CYQ）算法：从 K线（价格+成交量+流通股本）推算筹码分布。

标准「移动成本分布」算法：
- 每日成交量按当日 [最低价, 最高价] 区间做三角分布（峰值在收盘价）
- 历史筹码按当日换手率逐日衰减（换手 = 当日成交量 / 流通股本）
- 累计归一化得到筹码分布曲线，再据此计算获利比例、平均持仓成本、
  90%/70% 筹码集中度、筹码穿透率等。
"""
import numpy as np


def chip_distribution(bars, float_shares, bins=200):
    """计算筹码分布。bars: K线（升序）；float_shares: 流通股本(股)。
    返回 dict（None 表示数据不足）。
    """
    if not bars or not float_shares or float_shares <= 0 or len(bars) < 30:
        return None

    highs = np.array([b["high"] for b in bars], dtype=float)
    lows = np.array([b["low"] for b in bars], dtype=float)
    closes = np.array([b["close"] for b in bars], dtype=float)
    vols = np.array([b["volume"] for b in bars], dtype=float) * 100.0  # 手 -> 股

    pmin, pmax = float(lows.min()), float(highs.max())
    if pmax <= pmin:
        return None
    price = np.linspace(pmin, pmax, bins)
    bin_w = (pmax - pmin) / (bins - 1)

    chip = np.zeros(bins)
    for i in range(len(bars)):
        turn = min(vols[i] / float_shares, 1.0)
        chip *= (1.0 - turn)  # 历史筹码衰减（换手离场）
        lo, hi, cl = lows[i], highs[i], closes[i]
        if hi < lo:
            lo, hi = hi, lo
        ilo = max(0, min(bins - 1, int((lo - pmin) / bin_w)))
        ihi = max(0, min(bins - 1, int((hi - pmin) / bin_w)))
        ipk = max(ilo, min(ihi, int((cl - pmin) / bin_w)))
        w = np.zeros(bins)
        if ipk > ilo:
            w[ilo:ipk + 1] = np.linspace(0.0, 1.0, ipk - ilo + 1)
        if ihi > ipk:
            w[ipk:ihi + 1] = np.linspace(1.0, 0.0, ihi - ipk + 1)
        else:
            w[ipk] = 1.0
        s = w.sum()
        if s > 0:
            w /= s
        chip += w * turn

    total = chip.sum()
    if total <= 0:
        return None
    chip /= total
    cur = float(closes[-1])

    # 获利比例（当前价下方的筹码占比）
    profit_ratio = float(chip[price <= cur].sum() * 100)
    # 平均持仓成本
    avg_cost = float((chip * price).sum())
    # 90% / 70% 筹码集中度（(高-低)/(高+低)）
    c90 = _concentration(chip, price, 0.90)
    c70 = _concentration(chip, price, 0.70)
    # 筹码穿透率（当前价在 90% 筹码区间内的位置，0-100）
    pene = _penetration(chip, price, cur, 0.90)

    return {
        "profit_ratio": profit_ratio,
        "avg_cost": avg_cost,
        "c90": c90,
        "c70": c70,
        "penetration": pene,
        "cur_price": cur,
    }


def _concentration(chip, price, pct):
    """包含 pct 比例筹码的最窄价格区间集中度 = (高-低)/(高+低)*100"""
    cum = np.cumsum(chip)
    total = cum[-1]
    if total <= 0:
        return None
    best = None
    n = len(chip)
    j = 0
    for i in range(n):
        while j < n and (cum[j] - (cum[i - 1] if i > 0 else 0)) < pct * total:
            j += 1
        if j >= n:
            break
        lo, hi = price[i], price[j]
        span = (hi - lo) / (hi + lo) * 100 if (hi + lo) > 0 else 0.0
        if best is None or span < best:
            best = span
    return round(float(best), 2) if best is not None else None


def _penetration(chip, price, cur, pct=0.90):
    """当前价在 pct 筹码区间内的位置（0-100，50=区间中部）"""
    cum = np.cumsum(chip)
    total = cum[-1]
    if total <= 0:
        return None
    lo_idx = int(np.searchsorted(cum, (1 - pct) / 2 * total))
    hi_idx = int(np.searchsorted(cum, (1 + pct) / 2 * total))
    lo_idx = max(0, min(len(price) - 1, lo_idx))
    hi_idx = max(0, min(len(price) - 1, hi_idx))
    lo, hi = price[lo_idx], price[hi_idx]
    if hi <= lo:
        return 50.0
    return float((cur - lo) / (hi - lo) * 100)
