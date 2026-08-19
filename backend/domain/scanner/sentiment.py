# -*- coding: utf-8 -*-
"""单股情绪因子：综合「市场行为」+「财经新闻舆情」，输出 0-100 分（50=中性）。

设计思路（贴合 A 股次日行情）：
- 看多信号：主力资金净流入、涨停/连板、融资余额增加、机构龙虎榜净买入、
  北向增持、股东户数减少（筹码集中）、新闻净利好
- 看空信号：主力资金净流出、跌停、融券余额增加、机构净卖出、减持/亏损类新闻
- 过热/反转信号：换手率极高、放量滞涨（量价背离）、新闻热度骤增——情绪过热往往次日反转
"""
import numpy as np

from . import indicators as ind
from . import technical as tech

# 利好/利空关键词
POS_WORDS = ["回购", "增持", "中标", "签约", "预增", "扭亏", "涨价", "提价", "突破",
             "创新高", "获批", "合作", "战略", "涨停", "分红", "派现", "扩产", "投产",
             "业绩预增", "增长", "盈利", "重组", "收购", "并购", "举牌", "增资", "摘帽", "预喜"]
NEG_WORDS = ["减持", "亏损", "预减", "退市", "违规", "处罚", "诉讼", "立案", "调查",
             "质押", "爆雷", "跌停", "下调", "警示", "问询", "减值", "解禁", "套现",
             "被查", "下滑", "下降", "终止", "失败", "违约", "债务", "预亏", "预降"]


def _num(v):
    try:
        return float(v) if v not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def _board_limit(code):
    """涨跌停幅度（%）：创业板/科创板 20%，主板 10%"""
    if code.startswith(("300", "301", "688", "689")):
        return 19.8
    return 9.8


def _limit_signal(b):
    """涨跌停/连板情绪信号"""
    snap = b.get("snapshot") or {}
    pct = _num(snap.get("pct_chg"))
    code = b.get("ts_code", "")
    lim = _board_limit(code)
    if pct is None:
        return 0.0, "无涨跌幅数据"
    sig = 0.0
    if pct >= lim:
        sig = 1.0
    elif pct >= 7.0:
        sig = 0.6
    elif pct <= -lim:
        sig = -1.0
    elif pct <= -7.0:
        sig = -0.6
    # 连板检测（近5日涨停次数）
    bars = b.get("kline") or []
    if len(bars) >= 6:
        closes = np.array([x["close"] for x in bars], dtype=float)
        rets = np.diff(closes) / closes[:-1] * 100
        up_count = int((rets[-5:] >= lim).sum())
        if up_count >= 2:
            sig = _clamp(sig + 0.3)
            return sig, f"涨跌幅{pct:+.1f}%，近5日{up_count}个涨停（连板）"
    return sig, f"涨跌幅{pct:+.1f}%"


def _money_signal(b):
    """主力资金情绪"""
    snap = b.get("snapshot") or {}
    net = _num(snap.get("main_net_inflow"))
    circ = _num(snap.get("circ_mv"))
    if net is None or circ in (None, 0):
        return 0.0, "无资金流数据"
    r = net / circ
    sig = _clamp(r / 0.02) * 0.6
    return sig, f"主力净流入/流通市值={r*100:.2f}%"


def _margin_signal(b):
    """两融杠杆情绪：融资增=看多，融券增=看空"""
    margin = b.get("margin") or []
    if len(margin) < 5:
        return 0.0, "无两融数据"
    rzye = [_num(r.get("rzye")) for r in margin[:5]]
    rqye = [_num(r.get("rqye")) for r in margin[:5]]
    rzye = [x for x in rzye if x is not None]
    rqye = [x for x in rqye if x is not None]
    sig = 0.0
    note = []
    if len(rzye) >= 2 and rzye[-1] and rzye[0]:
        chg = (rzye[-1] - rzye[0]) / rzye[0]
        sig += _clamp(chg / 0.05) * 0.25
        note.append(f"融资5日{chg*100:+.1f}%")
    if len(rqye) >= 2 and rqye[-1] and rqye[0]:
        chg = (rqye[-1] - rqye[0]) / rqye[0]
        sig -= _clamp(chg / 0.10) * 0.3
        note.append(f"融券5日{chg*100:+.1f}%")
    return sig, " ".join(note) if note else "两融变化"


def _top_inst_signal(b):
    net = b.get("inst_net")
    if net is None:
        return 0.0, "无龙虎榜"
    sig = 0.4 if net > 0 else (-0.3 if net < 0 else 0.1)
    return sig, f"机构净买入{net/1e4:.0f}万元"


def _holder_signal(b):
    holders = b.get("holders") or []
    if not holders:
        return 0.0, "无股东户数"
    ratio = _num(holders[0].get("ratio"))
    if ratio is None:
        return 0.0, "股东户数变动缺失"
    sig = _clamp(-ratio / 10.0) * 0.3  # 户数减少(负)=集中=看多
    return sig, f"股东户数环比{ratio:+.1f}%"


def _northbound_signal(b):
    nb = b.get("northbound")
    if not nb:
        return 0.0, "无北向数据"
    change = _num(nb.get("change_rate"))
    if change is None:
        return 0.0, "北向变动缺失"
    sig = _clamp(change / 0.8) * 0.4
    return sig, f"北向持股变动{change:.2f}%"


def _turnover_signal(b):
    snap = b.get("snapshot") or {}
    tr = _num(snap.get("turnover_rate"))
    if tr is None:
        return 0.0, "无换手率"
    if tr > 25:
        return -0.4, f"换手率{tr:.1f}%（过热）"
    if tr > 15:
        return -0.2, f"换手率{tr:.1f}%（偏高）"
    if tr >= 3:
        return 0.2, f"换手率{tr:.1f}%（活跃）"
    if tr < 1:
        return -0.1, f"换手率{tr:.1f}%（冷淡）"
    return 0.0, f"换手率{tr:.1f}%"


def _volume_divergence_signal(b):
    """量价背离：近5日价与量相关系数（价涨量缩=负相关=看空）"""
    bars = b.get("kline") or []
    if len(bars) < 6:
        return 0.0, "K线不足"
    seg = bars[-5:]
    p = [x["close"] for x in seg]
    v = [x["volume"] for x in seg]
    c = ind.pearson(p, v)
    if c is None:
        return 0.0, "无法计算量价相关"
    sig = _clamp(c) * 0.3
    return sig, f"近5日量价相关={c:.2f}"


def _news_signal(b):
    """新闻舆情：热度 + 方向"""
    news = b.get("news") or []
    if not news:
        return 0.0, "无新闻"
    n = len(news)
    pos = sum(1 for it in news if any(w in (it.get("title") or "") for w in POS_WORDS))
    neg = sum(1 for it in news if any(w in (it.get("title") or "") for w in NEG_WORDS))
    # 方向
    direction = 0.0
    if pos + neg > 0:
        direction = _clamp((pos - neg) / (pos + neg)) * 0.5
    # 热度
    if n >= 8:
        heat = 0.2
    elif n >= 4:
        heat = 0.3
    elif n >= 1:
        heat = 0.1
    else:
        heat = 0.0
    sig = direction + heat
    return sig, f"新闻{n}条 利好{pos}/利空{neg}"


# 子信号权重（合计约 1.0）
_SIGNALS = [
    (0.20, _limit_signal, "涨跌停/连板"),
    (0.18, _money_signal, "主力资金"),
    (0.10, _margin_signal, "两融杠杆"),
    (0.08, _top_inst_signal, "龙虎榜机构"),
    (0.08, _holder_signal, "股东户数"),
    (0.08, _northbound_signal, "北向资金"),
    (0.10, _turnover_signal, "换手率"),
    (0.08, _volume_divergence_signal, "量价背离"),
    (0.10, _news_signal, "新闻舆情"),
]


def compute_sentiment(b):
    """综合情绪因子，返回 (score 0-100, value, note)"""
    total = 0.0
    parts = []
    for w, fn, label in _SIGNALS:
        try:
            sig, note = fn(b)
        except Exception as e:  # noqa: BLE001
            sig, note = 0.0, f"异常:{e}"
        total += w * sig
        parts.append(f"{label}({sig:+.2f})")
    # 50 + 加权和 * 30 → 映射到 0-100（50 中性）
    score = round(max(0.0, min(100.0, 50.0 + total * 30.0)), 2)
    return score, round(total, 3), "；".join(parts)
