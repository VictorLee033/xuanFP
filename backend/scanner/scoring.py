# -*- coding: utf-8 -*-
"""九维评分聚合：数据缺失维度降权、权重按比例分摊、综合得分"""
from .factors import DIM_NAMES

DIM_ORDER = ["value", "quality", "growth", "trend", "momentum",
             "capital", "chip", "safety", "macro"]


def aggregate(factors, weights):
    """factors: compute_factors 输出；weights: {dim: 名义权重}
    返回 (综合得分, 维度明细 dict, 缺失说明列表)
    """
    dims = {}
    for dim in DIM_ORDER:
        items = [v for k, v in factors.items() if v["dim"] == dim]
        n_total = len(items)
        scored = [v for v in items if v["score"] is not None]
        n_avail = len(scored)
        avg = sum(v["score"] for v in scored) / n_avail if n_avail else None
        dims[dim] = {
            "name": DIM_NAMES[dim],
            "score": round(avg, 2) if avg is not None else None,
            "available": n_avail,
            "total": n_total,
            "weight_nominal": weights.get(dim, 0),
            "weight_effective": 0.0,
        }

    # 权重分摊：有效权重 = 名义权重 × 可得性；损失权重按名义权重比例再分配
    total_eff = 0.0
    for dim, d in dims.items():
        avail = d["available"] / d["total"] if d["total"] else 0.0
        d["availability"] = avail
        d["weight_effective"] = d["weight_nominal"] * avail
        total_eff += d["weight_effective"]

    lost = sum(d["weight_nominal"] for d in dims.values()) - total_eff
    if lost > 0 and total_eff > 0:
        # 按名义权重比例把损失权重分给有数据的维度
        nominal_total = sum(d["weight_nominal"] for d in dims.values())
        for dim, d in dims.items():
            if d["available"] > 0 and nominal_total > 0:
                d["weight_effective"] += lost * (d["weight_nominal"] / nominal_total)
        total_eff = sum(d["weight_effective"] for d in dims.values())

    total = 0.0
    for dim, d in dims.items():
        if d["score"] is not None:
            total += d["score"] * d["weight_effective"]
    combined = total / total_eff if total_eff > 0 else None

    missing = [v for v in factors.values() if v["score"] is None]
    return combined, dims, missing
