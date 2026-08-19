# -*- coding: utf-8 -*-
"""九维评分：两层权重 + 百分位校准。

口径（按需求约定）：
- 因子层「绝对打分」：每个因子用绝对阈值打 0-100 分，真实反映指标好坏。
- 维度层「加权聚合」：维度原始分 = 维度内因子加权平均（绝对分）。
- 综合层「百分位校准」：把每个维度的原始分转成「评分池内百分位」（0-100），
  再加权合成综合分。这样综合分分布均匀、Top 股票能进高阈值档，同时因子层面仍真实。

数据缺失（score=None）：该因子不计入，权重在同维度内自然归一；整维度缺失则维度不计入。
"""
from .factors import DIM_NAMES, FACTOR_WEIGHTS

DIM_ORDER = ["value", "quality", "growth", "trend", "momentum",
             "capital", "chip", "safety", "macro"]


def dimension_scores(factors):
    """各维度原始得分（维度内因子加权平均，0-100 绝对分）。
    返回 {dim: {name, raw_score, available, total}}
    """
    dims = {}
    for dim in DIM_ORDER:
        items = {k: v for k, v in factors.items() if v["dim"] == dim}
        scored = {k: v for k, v in items.items() if v["score"] is not None}
        n_avail = len(scored)
        if scored:
            wsum = sum(FACTOR_WEIGHTS.get(k, 1.0) for k in scored)
            wscore = sum(v["score"] * FACTOR_WEIGHTS.get(k, 1.0) for k, v in scored.items())
            avg = wscore / wsum if wsum else 0.0
        else:
            avg = None
        dims[dim] = {
            "name": DIM_NAMES[dim],
            "raw_score": round(avg, 2) if avg is not None else None,
            "score": None,  # 百分位由引擎跨截面填充
            "available": n_avail,
            "total": len(items),
        }
    return dims


def percentile_rank(values, value):
    """value 在 values 中的百分位（0-100）。"""
    if value is None or not values:
        return None
    arr = sorted(values)
    return (sum(1 for x in arr if x <= value) - 0.5) / len(arr) * 100


def combine(dims, dim_weights):
    """加权合成综合分。dims: {dim: {score(百分位), ...}}；dim_weights: {dim: 权重}。
    只对「有得分的维度」加权并归一，返回综合分（0-100）。
    """
    total_w = 0.0
    total_s = 0.0
    for dim, d in dims.items():
        if d.get("score") is not None:
            total_s += d["score"] * dim_weights.get(dim, 0)
            total_w += dim_weights.get(dim, 0)
    return (total_s / total_w) if total_w > 0 else None
