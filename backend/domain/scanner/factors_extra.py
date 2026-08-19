# -*- coding: utf-8 -*-
"""新增因子：细化技术指标 + 筹码分布 + 情绪因子（打分包装）。

每个函数返回 (score, value, note)，score 0-100；由 factors.py 注册进 FACTORS。
依赖 bundle 字段（由 engine 组装）：snapshot/kline/bench/chip/rps/news/margin/等。
"""
import numpy as np

from . import technical as tech
from .factors import _lin, _num
from .sentiment import compute_sentiment


def _clamp01(x):
    return max(0.0, min(1.0, x))


# ======================================================================
# 趋势类（trend）
# ======================================================================
def g1_macd(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    dif, dea, hist = tech.macd(c)
    if dif is None or np.isnan(dif[-1]) or np.isnan(dea[-1]):
        return None, None, "MACD数据不足"
    d, e, h = dif[-1], dea[-1], hist[-1]
    if d > e:
        score = 60 + _clamp01(abs(h) / max(abs(dif[-20:]).max(), 1e-9)) * 40
        note = "MACD金叉多头"
    else:
        score = 40 - _clamp01(abs(h) / max(abs(dif[-20:]).max(), 1e-9)) * 30
        note = "MACD死叉空头"
    return round(score, 1), round(h, 3), f"{note}（DIF={d:.3f} DEA={e:.3f}）"


def g2_dmi(b):
    pdi, mdi, adx = tech.dmi(b.get("kline") or [])
    if pdi is None:
        return None, None, "DMI数据不足"
    if pdi > mdi:
        score = 60 + _clamp01((pdi - mdi) / 40) * 40
    else:
        score = 40 - _clamp01((mdi - pdi) / 40) * 40
    return round(score, 1), round(pdi - mdi, 2), f"+DI={pdi:.1f} -DI={mdi:.1f} ADX={adx:.1f}"


def g3_trix(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    t, m = tech.trix(c)
    if t is None:
        return None, None, "TRIX数据不足"
    score = 60 + _clamp01((t - m) / 1.0) * 40 if t > m else 40 + _clamp01((t - m) / 1.0) * 40
    return round(max(0, min(100, score)), 1), round(t, 3), f"TRIX={t:.3f} MATRIX={m:.3f}"


def g4_dma(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    ddd, ama = tech.dma(c)
    if ddd is None:
        return None, None, "DMA数据不足"
    score = 70 if ddd > ama else 30
    return score, round(ddd - ama, 2), f"DDD={ddd:.2f} AMA={ama:.2f}"


def g5_ema_trend(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    e5, e20, e60 = tech.ema_last(c, 5), tech.ema_last(c, 20), tech.ema_last(c, 60)
    if None in (e5, e20, e60):
        return None, None, "EMA数据不足"
    if e5 > e20 > e60:
        score = 100.0
    elif e5 < e20 < e60:
        score = 0.0
    else:
        score = 50 + sum([e5 > e20, e20 > e60]) * 20 - sum([e5 < e20, e20 < e60]) * 20
    return round(max(0, min(100, score)), 1), round(e5, 2), f"EMA5={e5:.2f} EMA20={e20:.2f} EMA60={e60:.2f}"


# ======================================================================
# 量价动能类（momentum）
# ======================================================================
def g6_kdj(b):
    k, d, j = tech.kdj(b.get("kline") or [])
    if k is None:
        return None, None, "KDJ数据不足"
    if j < 20:
        score = 100.0
        note = "KDJ超卖"
    elif j > 100:
        score = 0.0
        note = "KDJ超买"
    elif k > d:
        score = 70.0
        note = "KDJ金叉"
    else:
        score = 30.0
        note = "KDJ死叉"
    return score, round(j, 2), f"{note}（K={k:.1f} D={d:.1f} J={j:.1f}）"


def g7_cci(b):
    c = tech.cci(b.get("kline") or [])
    if c is None:
        return None, None, "CCI数据不足"
    if c < -100:
        score = 100.0
        note = "CCI超卖"
    elif c > 100:
        score = 0.0
        note = "CCI超买"
    else:
        score = 50 + c / 2
        note = "CCI常态"
    return round(max(0, min(100, score)), 1), round(c, 2), f"{note}（CCI={c:.1f}）"


def g8_bias(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    bi = tech.bias(c, 6)
    if bi is None:
        return None, None, "BIAS数据不足"
    score = 100.0 if bi <= -8 else (0.0 if bi >= 8 else 50 - bi * 6.25)
    return round(max(0, min(100, score)), 1), round(bi, 2), f"BIAS(6)={bi:.2f}%"


def g9_roc(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    r = tech.roc(c, 12)
    if r is None:
        return None, None, "ROC数据不足"
    score = _lin(r, -10, 15, 0.0, 100.0)
    return round(score, 1), round(r, 2), f"ROC(12)={r:.2f}%"


def g10_wr(b):
    w = tech.wr(b.get("kline") or [])
    if w is None:
        return None, None, "WR数据不足"
    score = 100.0 if w > 80 else (0.0 if w < 20 else 50 + (50 - w))
    return round(max(0, min(100, score)), 1), round(w, 2), f"WR={w:.1f}"


def g11_obv(b):
    t = tech.obv_trend(b.get("kline") or [], 20)
    if t is None:
        return None, None, "OBV数据不足"
    score = 60 + _clamp01(t / max(np.abs(tech.obv(b.get("kline") or [])).max(), 1e-9)) * 40
    return round(max(0, min(100, score)), 1), round(t / 1e4, 0), f"OBV近20日净变化={t/1e4:.0f}万"


def g12_vr(b):
    v = tech.vr(b.get("kline") or [])
    if v is None:
        return None, None, "VR数据不足"
    if 40 <= v <= 160:
        score = 80.0
    elif v < 40:
        score = 40.0
    else:
        score = 30.0
    return score, round(v, 2), f"VR={v:.1f}"


def g13_pvt(b):
    p = tech.pvt(b.get("kline") or [])
    if p is None or len(p) < 21:
        return None, None, "PVT数据不足"
    trend = p[-1] - p[-20]
    score = 60 + _clamp01(trend / max(np.abs(p).max(), 1e-9)) * 40
    return round(max(0, min(100, score)), 1), round(trend / 1e4, 0), f"PVT近20日净变化"


def g14_vol_ma(b):
    bars = b.get("kline") or []
    if len(bars) < 6:
        return None, None, "K线不足"
    v = bars[-1]["volume"]
    ma5 = np.mean([x["volume"] for x in bars[-6:-1]])
    if ma5 <= 0:
        return None, None, "均量为0"
    ratio = v / ma5
    score = _lin(ratio, 0.5, 2.0, 0.0, 100.0)
    return round(score, 1), round(ratio, 2), f"量能/5日均量={ratio:.2f}"


# ======================================================================
# 波动/风险收益（safety）
# ======================================================================
def g15_atr(b):
    a = tech.atr_pct(b.get("kline") or [])
    if a is None:
        return None, None, "ATR数据不足"
    score = _lin(a, 8.0, 2.0, 0.0, 100.0)
    return round(score, 1), round(a, 2), f"ATR/价={a:.2f}%"


def g16_kc(b):
    upper, mid, lower = tech.keltner_channel(b.get("kline") or [])
    if upper is None:
        return None, None, "KC数据不足"
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)[-1]
    pos = (c - lower) / (upper - lower) if upper > lower else 0.5
    score = 100.0 if pos <= 0.2 else (0.0 if pos >= 0.9 else _lin(pos, 0.2, 0.9, 100.0, 0.0))
    return round(score, 1), round(pos, 2), f"KC位置={pos:.2f}（0=下轨 1=上轨）"


def g17_dc(b):
    upper, mid, lower = tech.donchian_channel(b.get("kline") or [])
    if upper is None:
        return None, None, "DC数据不足"
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)[-1]
    if c >= upper:
        score, note = 100.0, "突破20日新高"
    elif c <= lower:
        score, note = 0.0, "跌破20日新低"
    else:
        pos = (c - lower) / (upper - lower)
        score, note = _lin(pos, 0.0, 1.0, 30.0, 70.0), "通道内"
    return round(score, 1), round(c, 2), f"{note}（上轨{upper:.2f} 下轨{lower:.2f}）"


def g18_alpha(b):
    bars = b.get("kline") or []
    bench = b.get("bench") or []
    if len(bars) < 30 or len(bench) < 30:
        return None, None, "Alpha数据不足"
    bm = {x["date"]: x["close"] for x in bench}
    rs, rb = [], []
    for x in bars:
        if x["date"] in bm:
            rs.append(x["close"])
            rb.append(bm[x["date"]])
    if len(rs) < 30:
        return None, None, "基准对齐不足"
    rs = np.asarray(rs)
    rb = np.asarray(rb)
    ret_s = np.diff(rs) / rs[:-1]
    ret_b = np.diff(rb) / rb[:-1]
    a = tech.alpha(ret_s[-60:], ret_b[-60:])
    if a is None:
        return None, None, "Alpha无法计算"
    score = _lin(a, -20.0, 20.0, 0.0, 100.0)
    return round(score, 1), round(a, 2), f"近60日年化超额={a:.2f}%"


def g19_rps(b):
    r = b.get("rps")
    if r is None:
        return None, None, "RPS缺失"
    return round(r, 1), round(r, 2), f"RPS={r:.1f}（全池分位）"


# ======================================================================
# 筹码与情绪（chip）
# ======================================================================
def g20_profit_ratio(b):
    chip = b.get("chip")
    if not chip:
        return None, None, "筹码分布不可用"
    pr = chip.get("profit_ratio")
    # 获利盘 85~98 最佳（上方套牢少且未极度超买）
    score = _lin(pr, 0.0, 85.0, 0.0, 100.0)
    if pr > 98:
        score = 30.0
    return round(score, 1), round(pr, 2), f"获利盘比例={pr:.1f}%"


def g21_cost_position(b):
    chip = b.get("chip")
    if not chip:
        return None, None, "筹码分布不可用"
    cur = chip.get("cur_price")
    avg = chip.get("avg_cost")
    if not cur or not avg:
        return None, None, "成本数据缺失"
    ratio = cur / avg
    # 当前价相对持仓成本：略高于成本(1.0~1.2)最佳
    score = 100.0 if 1.0 <= ratio <= 1.2 else (_lin(ratio, 0.8, 1.0, 30.0, 100.0) if ratio < 1.0 else _lin(ratio, 1.2, 1.6, 100.0, 0.0))
    return round(score, 1), round(ratio, 3), f"价/平均成本={ratio:.2f}"


def g22_concentration90(b):
    chip = b.get("chip")
    if not chip:
        return None, None, "筹码分布不可用"
    c = chip.get("c90")
    if c is None:
        return None, None, "集中度缺失"
    # 集中度越低（筹码越集中）越好
    score = _lin(c, 30.0, 10.0, 0.0, 100.0)
    return round(score, 1), round(c, 2), f"90%集中度={c:.2f}%"


def g23_concentration70(b):
    chip = b.get("chip")
    if not chip:
        return None, None, "筹码分布不可用"
    c = chip.get("c70")
    if c is None:
        return None, None, "集中度缺失"
    score = _lin(c, 20.0, 5.0, 0.0, 100.0)
    return round(score, 1), round(c, 2), f"70%集中度={c:.2f}%"


def g24_penetration(b):
    chip = b.get("chip")
    if not chip:
        return None, None, "筹码分布不可用"
    p = chip.get("penetration")
    if p is None:
        return None, None, "穿透率缺失"
    score = _lin(p, 0.0, 100.0, 20.0, 80.0)
    return round(score, 1), round(p, 2), f"筹码穿透率={p:.1f}%"


def g25_cyc(b):
    c = np.array([x["close"] for x in (b.get("kline") or [])], dtype=float)
    c5, c13, c34 = tech.cyc(c)
    if c5 is None:
        return None, None, "CYC数据不足"
    if c5 > c13 > c34:
        score = 100.0
        note = "成本均线多头"
    elif c5 < c13 < c34:
        score = 0.0
        note = "成本均线空头"
    else:
        score = 50 + sum([c5 > c13, c13 > c34]) * 20 - sum([c5 < c13, c13 < c34]) * 20
        note = "成本均线纠缠"
    return round(max(0, min(100, score)), 1), round(c5, 2), f"{note}（CYC5={c5:.2f}）"


def g26_sentiment(b):
    """综合情绪因子"""
    return compute_sentiment(b)


# ======================================================================
# 注册表：新因子 + 维度内权重
# ======================================================================
EXTRA_FACTORS = [
    ("g1", "trend", "MACD", g1_macd),
    ("g2", "trend", "DMI方向指标", g2_dmi),
    ("g3", "trend", "TRIX三重指数平滑", g3_trix),
    ("g4", "trend", "DMA平行线差", g4_dma),
    ("g5", "trend", "EMA多头排列", g5_ema_trend),

    ("g6", "momentum", "KDJ随机指标", g6_kdj),
    ("g7", "momentum", "CCI顺势指标", g7_cci),
    ("g8", "momentum", "BIAS乖离率", g8_bias),
    ("g9", "momentum", "ROC变动率", g9_roc),
    ("g10", "momentum", "WR威廉指标", g10_wr),
    ("g11", "momentum", "OBV能量潮", g11_obv),
    ("g12", "momentum", "VR成交量变异率", g12_vr),
    ("g13", "momentum", "PVT价量趋势", g13_pvt),
    ("g14", "momentum", "均量线（量能）", g14_vol_ma),

    ("g15", "safety", "ATR真实波幅", g15_atr),
    ("g16", "safety", "肯特纳通道KC", g16_kc),
    ("g17", "safety", "唐奇安通道DC", g17_dc),
    ("g18", "safety", "Alpha超额收益", g18_alpha),
    ("g19", "safety", "RPS相对强度", g19_rps),

    ("g20", "chip", "筹码获利比例", g20_profit_ratio),
    ("g21", "chip", "持仓成本位置", g21_cost_position),
    ("g22", "chip", "90%筹码集中度", g22_concentration90),
    ("g23", "chip", "70%筹码集中度", g23_concentration70),
    ("g24", "chip", "筹码穿透率", g24_penetration),
    ("g25", "chip", "成本均线CYC", g25_cyc),
    ("g26", "chip", "综合情绪因子", g26_sentiment),
]

# 注：因子权重统一在 factors.py 的 FACTOR_WEIGHTS 中维护（含 g1~g26），
# 这里不再单独维护权重，避免两处不一致。
