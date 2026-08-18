# -*- coding: utf-8 -*-
"""九大维度 37 因子评分引擎（东方财富快照 + 数据中心财务 + 腾讯K线）

DataBundle 结构：
{
  "ts_code", "name", "industry" (申万二级), "sw_industry" (申万一级),
  "snapshot": {price,pct_chg,amount,turnover_rate,volume_ratio,total_mv,circ_mv,pb,pe_ttm,main_net_inflow,industry},
  "fin": [数据中心财务, report_date 降序],
  "kline": [bars], "bench": [bars], "us_momentum": {symbol: pct},
}
因子返回 (score, value, note)：score=None 表示数据缺失（触发维度降权）。
"""
import numpy as np

from . import indicators as ind

# 申万二级 -> 申万一级（近似映射）
SW_MAP = {
    "白酒Ⅱ": "食品饮料", "非白酒": "食品饮料", "啤酒": "食品饮料", "其他酒类": "食品饮料",
    "软饮料": "食品饮料", "乳品": "食品饮料", "休闲食品": "食品饮料", "食品加工": "食品饮料",
    "调味发酵品Ⅱ": "食品饮料", "预加工食品": "食品饮料", "保健品": "食品饮料",
    "半导体": "电子", "元件": "电子", "光学光电子": "电子", "消费电子": "电子",
    "电子化学品Ⅱ": "电子", "其他电子Ⅱ": "电子",
    "软件开发": "计算机", "IT服务Ⅱ": "计算机", "计算机设备": "计算机",
    "通信设备": "通信", "通信服务": "通信",
    "化学制药": "医药生物", "中药Ⅱ": "医药生物", "生物制品": "医药生物",
    "医疗器械": "医药生物", "医疗服务": "医药生物", "医药商业": "医药生物",
    "电池": "电力设备", "光伏设备": "电力设备", "电网设备": "电力设备",
    "风电设备": "电力设备", "电机Ⅱ": "电力设备", "其他电源设备Ⅱ": "电力设备", "电源设备": "电力设备",
    "乘用车": "汽车", "商用车": "汽车", "汽车零部件": "汽车", "汽车服务": "汽车",
    "摩托车及其他": "汽车",
    "白色家电": "家用电器", "黑色家电": "家用电器", "小家电": "家用电器",
    "厨卫电器": "家用电器", "照明设备Ⅱ": "家用电器", "家电零部件Ⅱ": "家用电器",
    "国有大型银行Ⅱ": "银行", "股份制银行Ⅱ": "银行", "城商行Ⅱ": "银行", "农商行Ⅱ": "银行", "银行Ⅱ": "银行", "银行": "银行",
    "证券Ⅱ": "非银金融", "保险Ⅱ": "非银金融", "多元金融": "非银金融", "证券": "非银金融", "保险": "非银金融",
    "房地产开发": "房地产", "房地产服务": "房地产",
    "煤炭开采": "煤炭", "焦炭Ⅱ": "煤炭",
    "油气开采Ⅱ": "石油石化", "油服工程": "石油石化", "炼化及贸易": "石油石化",
    "贵金属": "有色金属", "工业金属": "有色金属", "小金属": "有色金属", "能源金属": "有色金属", "金属新材料": "有色金属",
    "普钢": "钢铁", "特钢Ⅱ": "钢铁", "冶钢原料": "钢铁",
    "水泥": "建筑材料", "玻璃玻纤": "建筑材料", "装修建材": "建筑材料",
    "化学原料": "基础化工", "化学制品": "基础化工", "化学纤维": "基础化工",
    "塑料": "基础化工", "橡胶": "基础化工", "农化制品": "基础化工", "非金属材料Ⅱ": "基础化工",
    "工程机械": "机械设备", "通用设备": "机械设备", "专用设备": "机械设备",
    "自动化设备": "机械设备", "轨交设备Ⅱ": "机械设备",
    "航空装备Ⅱ": "国防军工", "航天装备Ⅱ": "国防军工", "地面兵装Ⅱ": "国防军工",
    "航海装备Ⅱ": "国防军工", "军工电子Ⅱ": "国防军工",
    "种植业": "农林牧渔", "养殖业": "农林牧渔", "农产品加工": "农林牧渔", "饲料": "农林牧渔",
    "动物保健Ⅱ": "农林牧渔", "渔业": "农林牧渔", "林业Ⅱ": "农林牧渔",
    "电力": "公用事业", "燃气Ⅱ": "公用事业", "环保设备Ⅱ": "环保", "环境治理": "环保", "水务及水治理": "环保",
    "旅游及景区": "社会服务", "酒店餐饮": "社会服务", "教育": "社会服务", "专业服务": "社会服务",
    "影视院线": "传媒", "游戏Ⅱ": "传媒", "广告营销": "传媒", "出版": "传媒",
    "电视广播Ⅱ": "传媒", "数字媒体": "传媒", "社交Ⅱ": "传媒",
    "纺织制造": "纺织服饰", "服装家纺": "纺织服饰", "饰品": "纺织服饰",
    "造纸": "轻工制造", "包装印刷": "轻工制造", "家居用品": "轻工制造", "文娱用品": "轻工制造",
    "航空机场": "交通运输", "铁路公路": "交通运输", "航运港口": "交通运输", "物流": "交通运输",
    "贸易Ⅱ": "商贸零售", "一般零售": "商贸零售", "专业连锁Ⅱ": "商贸零售", "互联网电商": "商贸零售",
    "装修装饰Ⅱ": "建筑装饰", "房屋建设Ⅱ": "建筑装饰", "基础建设": "建筑装饰",
    "专业工程": "建筑装饰", "工程咨询服务Ⅱ": "建筑装饰",
}

US_MAP = {
    "电子": "NVDA", "计算机": "NVDA", "通信": "NVDA",
    "医药生物": "LLY", "电力设备": "TSLA", "汽车": "TSLA",
    "食品饮料": "PEP", "银行": "JPM", "非银金融": "GS",
}

SW_BONUS = {"电子": 100, "计算机": 100, "通信": 85, "医药生物": 85, "电力设备": 70}


def _num(v):
    try:
        return float(v) if v not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def _annual(fin):
    """年报行（report_date 降序）"""
    return [r for r in fin if r.get("report_type") == "年报"]


def _lin(x, x0, x1, y0=0.0, y1=100.0):
    if x is None:
        return None
    if x1 == x0:
        return y0 if x < x0 else y1
    t = (x - x0) / (x1 - x0)
    return max(min(y0, y1), min(max(y0, y1), y0 + (y1 - y0) * t))


def _cagr(first, last, years):
    if first is None or last is None or first <= 0 or years <= 0:
        return None
    return (last / first) ** (1.0 / years) - 1.0


# ======================================================================
# 维度1 价值估值
# ======================================================================
def f1_peg(b):
    pe = _num((b.get("snapshot") or {}).get("pe_ttm"))
    annual = _annual(b.get("fin") or [])
    g = None
    if annual:
        g = _num(annual[0].get("profit_yoy")) or _num(annual[0].get("dedt_profit_yoy"))
    if g is None and b.get("fin"):
        g = _num(b["fin"][0].get("profit_yoy"))
    if pe is None or g is None or g <= 0:
        return None, None, "缺 PE-TTM 或净利润增速"
    peg = pe / g
    if 0.3 <= peg <= 0.8:
        score = 100.0
    elif peg > 2:
        score = 0.0
    elif peg < 0.3:
        score = 100.0
    else:
        score = _lin(peg, 0.8, 2.0, 100.0, 0.0)
    return score, round(peg, 2), f"PE-TTM={pe:.1f}, 净利增速={g:.1f}%"


def f2_dividend(b):
    # 股息率需个股分红接口，暂按缺失降权
    return None, None, "股息率数据缺失（降权）"


def f3_pcf(b):
    total_mv = _num((b.get("snapshot") or {}).get("total_mv"))  # 元
    annual = _annual(b.get("fin") or [])
    if not annual:
        return None, None, "缺财务数据"
    nco = _num(annual[0].get("ocf_to_profit"))  # 净现比
    profit = _num(annual[0].get("net_profit"))   # 归母净利(元)
    ocf = nco * profit if (nco is not None and profit is not None) else None
    if total_mv is None or ocf is None or ocf <= 0:
        return None, None, "缺市值或经营现金流"
    pcf = total_mv / ocf
    score = _lin(pcf, 40.0, 10.0, 0.0, 100.0)
    return score, round(pcf, 2), f"市现率={pcf:.1f}"


def f4_fcf_yield(b):
    total_mv = _num((b.get("snapshot") or {}).get("total_mv"))
    annual = _annual(b.get("fin") or [])
    if not annual:
        return None, None, "缺财务数据"
    fcff = _num(annual[0].get("fcff"))
    if total_mv is None or fcff is None:
        return None, None, "缺市值或自由现金流"
    y = fcff / total_mv
    score = _lin(y, 0.0, 0.06, 0.0, 100.0)
    return score, round(y * 100, 2), f"FCF/市值={y*100:.2f}%"


# ======================================================================
# 维度2 资产质量
# ======================================================================
def f5_dedt_roe(b):
    annual = _annual(b.get("fin") or [])[:3]
    vals = [_num(r.get("roe_dt")) or _num(r.get("roe")) for r in annual]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None, "缺扣非ROE"
    m = sum(vals) / len(vals)
    score = _lin(m, 6.0, 18.0, 0.0, 100.0)
    return score, round(m, 2), f"近3年扣非ROE均值={m:.2f}%"


def f6_gross_margin(b):
    annual = _annual(b.get("fin") or [])[:3]
    vals = [_num(r.get("gross_margin")) for r in annual]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None, "缺毛利率"
    m = sum(vals) / len(vals)
    cv = (np.std(vals) / m) if m > 0 else None
    score = _lin(m, 10.0, 35.0, 0.0, 100.0)
    if cv is not None and cv > 0.10:
        score *= (1 - min((cv - 0.10) / 0.20, 0.5))
    if m >= 35 and cv is not None and cv <= 0.10:
        score = 100.0
    return score, round(m, 2), (f"近3年毛利率均值={m:.2f}%, CV={cv:.2f}" if cv else f"近3年毛利率均值={m:.2f}%")


def f7_net_cash_ratio(b):
    annual = _annual(b.get("fin") or [])[:3]
    vals = [_num(r.get("ocf_to_profit")) for r in annual]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None, "缺净现比"
    m = sum(vals) / len(vals)
    score = _lin(m, 0.5, 1.2, 0.0, 100.0)
    return score, round(m, 2), f"近3年净现比均值={m:.2f}"


def f8_turnover_improve(b):
    annual = _annual(b.get("fin") or [])[:2]
    if len(annual) < 2:
        return None, None, "周转率期数不足"
    cur, prev = annual[0], annual[1]
    inv_c, inv_p = _num(cur.get("inv_turn")), _num(prev.get("inv_turn"))
    ar_c, ar_p = _num(cur.get("ar_turn")), _num(prev.get("ar_turn"))
    improved = 0
    total = 0
    if inv_c is not None and inv_p is not None:
        total += 1
        improved += 1 if inv_c > inv_p else 0
    if ar_c is not None and ar_p is not None:
        total += 1
        improved += 1 if ar_c > ar_p else 0
    if total == 0:
        return None, None, "周转率数据不足"
    ratio = improved / total
    score = 100 if ratio >= 1 else (60 if ratio >= 0.5 else (30 if ratio > 0 else 0))
    note = (f"存货周转 {inv_p:.2f}->{inv_c:.2f}" if inv_c else "存货周转—") + \
           (f"，应收周转 {ar_p:.2f}->{ar_c:.2f}" if ar_c else "，应收周转—")
    return score, round(ratio, 2), note


# ======================================================================
# 维度3 盈利成长
# ======================================================================
def f9_dedt_profit_cagr(b):
    annual = _annual(b.get("fin") or [])[:4]
    vals = [_num(r.get("dedt_profit")) for r in reversed(annual)]
    vals = [v for v in vals if v is not None]
    if len(vals) < 3:
        return None, None, "扣非净利期数不足"
    cagr = _cagr(vals[0], vals[-1], len(vals) - 1)
    if cagr is None:
        return None, None, "扣非净利为负"
    score = _lin(cagr, 0.0, 0.30, 0.0, 100.0)
    return score, round(cagr * 100, 2), f"近3年扣非净利CAGR={cagr*100:.1f}%"


def f10_revenue_cagr(b):
    annual = _annual(b.get("fin") or [])[:4]
    vals = [_num(r.get("revenue")) for r in reversed(annual)]
    vals = [v for v in vals if v is not None]
    if len(vals) < 3:
        return None, None, "营收期数不足"
    cagr = _cagr(vals[0], vals[-1], len(vals) - 1)
    if cagr is None:
        return None, None, "营收异常"
    score = _lin(cagr, 0.03, 0.20, 0.0, 100.0)
    return score, round(cagr * 100, 2), f"近3年营收CAGR={cagr*100:.1f}%"


def f11_qoq_profit(b):
    fin = b.get("fin") or []
    if not fin:
        return None, None, "单季数据不足"
    qoq = _num(fin[0].get("profit_qoq"))
    if qoq is None:
        return None, None, "单季环比缺失"
    score = _lin(qoq, 0.0, 0.15, 0.0, 100.0)
    return score, round(qoq, 2), f"单季净利环比={qoq*100:.1f}%"


def f12_rd_ratio(b):
    annual = _annual(b.get("fin") or [])[:1]
    if not annual:
        return None, None, "缺利润表"
    rd = _num(annual[0].get("rd_expense"))
    rev = _num(annual[0].get("revenue"))
    if rd is None or rev is None or rev <= 0:
        return None, None, "缺研发费用/营收"
    ratio = rd / rev
    score = _lin(ratio, 0.01, 0.08, 0.0, 100.0)
    sw = b.get("sw_industry") or ""
    if sw in ("电子", "计算机", "通信", "医药生物", "电力设备"):
        score = min(100.0, score * 1.2)
        note = f"研发费用率={ratio*100:.2f}%（{sw}加权）"
    else:
        note = f"研发费用率={ratio*100:.2f}%"
    return score, round(ratio * 100, 2), note


# ======================================================================
# 维度4 趋势技术面
# ======================================================================
def _ma(bars, n):
    if bars is None or len(bars) < n:
        return None
    return float(np.mean([b["close"] for b in bars[-n:]]))


def f13_ma_alignment(b):
    bars = b.get("kline") or []
    if len(bars) < 130:
        return None, None, "K线不足130日"
    c = np.array([x["close"] for x in bars], dtype=float)
    ma5, ma20, ma60, ma120 = _ma(bars, 5), _ma(bars, 20), _ma(bars, 60), _ma(bars, 120)
    if None in (ma5, ma20, ma60, ma120):
        return None, None, "均线数据不足"
    aligned = ma5 > ma20 > ma60 > ma120
    up5 = ind.slope(c, 5) or 0
    up20 = ind.slope(c, 20) or 0
    rising = up5 > 0 and up20 > 0
    score = (60 if aligned else 0) + (40 if rising else 0)
    if not aligned:
        score += 15 * sum([ma5 > ma20, ma20 > ma60, ma60 > ma120])
        score = min(score, 60)
    return score, round(ma5, 2), f"{'多头排列' if aligned else '未多头排列'}，MA5斜率{up5:.3f}/MA20斜率{up20:.3f}"


def f14_price_to_ma250(b):
    bars = b.get("kline") or []
    c = np.array([x["close"] for x in bars], dtype=float)
    if len(c) < 250:
        return None, None, "K线不足250日"
    ma250 = float(c[-250:].mean())
    ratio = c[-1] / ma250
    if 1.05 <= ratio <= 1.25:
        score = 100.0
    elif ratio <= 0.85 or ratio >= 1.60:
        score = 0.0
    elif ratio < 1.05:
        score = _lin(ratio, 0.85, 1.05, 0.0, 100.0)
    else:
        score = _lin(ratio, 1.25, 1.60, 100.0, 0.0)
    return score, round(ratio, 3), f"股价/年线={ratio:.2f}"


def f15_rsi(b):
    bars = b.get("kline") or []
    c = np.array([x["close"] for x in bars], dtype=float)
    r = ind.rsi(c, 14)
    if r is None:
        return None, None, "RSI数据不足"
    if 50 <= r <= 65:
        score = 100.0
    elif r < 30 or r > 80:
        score = 0.0
    elif r < 50:
        score = _lin(r, 30, 50, 0.0, 100.0)
    else:
        score = _lin(r, 65, 80, 100.0, 0.0)
    return score, round(r, 2), f"RSI(14)={r:.1f}"


def f16_bollinger(b):
    bars = b.get("kline") or []
    c = np.array([x["close"] for x in bars], dtype=float)
    if len(c) < 20:
        return None, None, "K线不足20日"
    upper, mid, low = ind.bollinger(c, 20, 2.0)
    price = c[-1]
    if price <= mid:
        score = 0.0
    else:
        score = _lin((upper - price) / price, 0.0, 0.05, 0.0, 100.0)
    return score, round((upper - price) / price * 100, 2), f"价={price:.2f} 中轨={mid:.2f} 距上轨={(upper-price)/price*100:.1f}%"


# ======================================================================
# 维度5 量价动能
# ======================================================================
def f17_volume_ratio(b):
    bars = b.get("kline") or []
    if len(bars) < 6:
        return None, None, "K线不足6日"
    vol = bars[-1]["volume"]
    avg5 = float(np.mean([x["volume"] for x in bars[-6:-1]]))
    if avg5 <= 0:
        return None, None, "5日均量为0"
    vr = vol / avg5
    pct = (bars[-1]["close"] / bars[-2]["close"] - 1) if len(bars) > 1 else 0
    score = _lin(vr, 0.5, 2.0, 0.0, 100.0)
    if vr > 2.0 and pct > 0:
        score = 100.0
    elif pct <= 0:
        score *= 0.5
    return score, round(vr, 2), f"量比={vr:.2f}，当日{pct*100:+.2f}%"


def f18_price_vol_corr(b):
    bars = b.get("kline") or []
    if len(bars) < 6:
        return None, None, "K线不足6日"
    seg = bars[-5:]
    c = ind.pearson([x["close"] for x in seg], [x["volume"] for x in seg])
    if c is None:
        return None, None, "相关系数无法计算"
    score = _lin(c, 0.0, 0.5, 0.0, 100.0)
    return score, round(c, 3), f"近5日量价相关系数={c:.2f}"


def f19_turnover(b):
    tr = _num((b.get("snapshot") or {}).get("turnover_rate"))
    if tr is None:
        return None, None, "缺换手率"
    if 3 <= tr <= 15:
        score = 100.0
    elif tr <= 1 or tr >= 30:
        score = 0.0
    elif tr < 3:
        score = _lin(tr, 1, 3, 0.0, 100.0)
    else:
        score = _lin(tr, 15, 30, 100.0, 0.0)
    return score, round(tr, 2), f"换手率={tr:.2f}%"


def f20_momentum_20d(b):
    bars = b.get("kline") or []
    c = np.array([x["close"] for x in bars], dtype=float)
    m = ind.momentum(c, 20)
    if m is None:
        return None, None, "K线不足20日"
    if 0.05 <= m <= 0.25:
        score = 100.0
    elif m <= 0 or m >= 0.40:
        score = 0.0
    elif m < 0.05:
        score = _lin(m, 0.0, 0.05, 0.0, 100.0)
    else:
        score = _lin(m, 0.25, 0.40, 100.0, 0.0)
    return score, round(m * 100, 2), f"20日动量={m*100:+.1f}%"


# ======================================================================
# 维度6 主力资金流
# ======================================================================
def f21_main_inflow(b):
    snap = b.get("snapshot") or {}
    net = _num(snap.get("main_net_inflow"))   # 元
    circ_mv = _num(snap.get("circ_mv"))       # 元
    if net is None or circ_mv in (None, 0):
        return None, None, "缺主力资金流或流通市值"
    ratio = net / circ_mv
    score = _lin(ratio, 0.0, 0.02, 0.0, 100.0)
    return score, round(ratio * 100, 3), f"主力净流入/流通市值={ratio*100:.2f}%"


def f22_northbound(b):
    return None, None, "北向持股数据缺失（降权）"


def f23_top_inst(b):
    return None, None, "龙虎榜机构席位数据缺失（降权）"


def f24_big_order_ratio(b):
    return None, None, "大单净买入占比数据缺失（降权）"


# ======================================================================
# 维度7 筹码与情绪
# ======================================================================
def f25_chip_profit(b):
    return None, None, "筹码获利盘数据缺失（降权）"


def f26_holder_change(b):
    return None, None, "股东户数数据缺失（降权）"


def f27_margin_ratio(b):
    return None, None, "融资融券数据缺失（降权）"


# ======================================================================
# 维度8 安全边际与波动
# ======================================================================
def f28_beta(b):
    bars = b.get("kline") or []
    bench = b.get("bench") or []
    if len(bars) < 30 or len(bench) < 30:
        return None, None, "缺K线或基准"
    bench_map = {x["date"]: x["close"] for x in bench}
    cs, cb = [], []
    for x in bars:
        if x["date"] in bench_map:
            cs.append(x["close"])
            cb.append(bench_map[x["date"]])
    if len(cs) < 30:
        return None, None, "基准对齐不足30日"
    ret_s = np.diff(cs) / np.array(cs[:-1])
    ret_b = np.diff(cb) / np.array(cb[:-1])
    beta = ind.beta_vs_bench(ret_s[-60:], ret_b[-60:])
    if beta is None:
        return None, None, "β无法计算"
    if 0.8 <= beta <= 1.2:
        score = 100.0
    elif beta <= 0.4 or beta >= 1.6:
        score = 0.0
    else:
        score = _lin(beta, 0.4, 0.8, 0.0, 100.0) if beta < 0.8 else _lin(beta, 1.2, 1.6, 100.0, 0.0)
    return score, round(beta, 2), f"β={beta:.2f}"


def f29_volatility(b):
    bars = b.get("kline") or []
    c = np.array([x["close"] for x in bars], dtype=float)
    if len(c) < 30:
        return None, None, "K线不足30日"
    rets = np.diff(c) / c[:-1]
    vol = ind.annual_volatility(rets, 60)
    if vol is None:
        return None, None, "波动率无法计算"
    score = _lin(vol, 0.60, 0.35, 0.0, 100.0)
    return score, round(vol * 100, 2), f"60日年化波动率={vol*100:.1f}%"


def f30_drawdown_recovery(b):
    bars = b.get("kline") or []
    c = np.array([x["close"] for x in bars], dtype=float)
    dd, recover, still = ind.max_drawdown_recovery_days(c)
    if dd is None:
        return None, None, "K线不足"
    if dd == 0:
        return 100.0, 0.0, "近一年无回撤"
    if still:
        return 20.0, -1, f"最大回撤{dd*100:.1f}%尚未修复"
    score = 100.0 if recover <= 30 else _lin(recover, 30, 120, 100.0, 0.0)
    return score, recover, f"最大回撤{dd*100:.1f}%，{recover}日修复"


# ======================================================================
# 维度9 景气度与宏观映射
# ======================================================================
def f31_industry_prosperity(b):
    sw = b.get("sw_industry") or ""
    if not sw:
        return 40.0, "-", "行业映射缺失"
    return SW_BONUS.get(sw, 40.0), sw, f"申万一级：{sw}"


def f32_inventory_cycle(b):
    return None, None, "行业库存周期数据缺失（降权）"


def f33_us_mapping(b):
    sw = b.get("sw_industry") or ""
    symbol = US_MAP.get(sw)
    if not symbol:
        return 50.0, "-", f"行业{sw}无外盘映射"
    mom = (b.get("us_momentum") or {}).get(symbol)
    if mom is None:
        return None, None, f"美股{symbol}行情获取失败"
    if mom > 0.10:
        score = 100.0
    elif mom <= 0:
        score = 0.0
    else:
        score = _lin(mom, 0.0, 0.10, 0.0, 100.0)
    return score, round(mom * 100, 2), f"映射{symbol}近20日{mom*100:+.1f}%"


# ======================================================================
# 因子注册表
# ======================================================================
FACTORS = [
    ("f1", "value", "PEG（PE/净利增速）", f1_peg),
    ("f2", "value", "股息率", f2_dividend),
    ("f3", "value", "市现率 PCF", f3_pcf),
    ("f4", "value", "自由现金流收益率", f4_fcf_yield),

    ("f5", "quality", "扣非ROE（近3年均值）", f5_dedt_roe),
    ("f6", "quality", "毛利率（近3年+稳定性）", f6_gross_margin),
    ("f7", "quality", "净现比（近3年均值）", f7_net_cash_ratio),
    ("f8", "quality", "存货/应收周转改善", f8_turnover_improve),

    ("f9", "growth", "扣非净利 CAGR", f9_dedt_profit_cagr),
    ("f10", "growth", "营收 CAGR", f10_revenue_cagr),
    ("f11", "growth", "单季净利环比", f11_qoq_profit),
    ("f12", "growth", "研发费用率", f12_rd_ratio),

    ("f13", "trend", "多周期均线排列", f13_ma_alignment),
    ("f14", "trend", "股价/年线 MA250", f14_price_to_ma250),
    ("f15", "trend", "RSI(14)", f15_rsi),
    ("f16", "trend", "布林带位置", f16_bollinger),

    ("f17", "momentum", "量比", f17_volume_ratio),
    ("f18", "momentum", "5日量价相关性", f18_price_vol_corr),
    ("f19", "momentum", "换手率", f19_turnover),
    ("f20", "momentum", "20日价格动量", f20_momentum_20d),

    ("f21", "capital", "主力净流入/流通市值", f21_main_inflow),
    ("f22", "capital", "北向持股变动", f22_northbound),
    ("f23", "capital", "机构龙虎榜", f23_top_inst),
    ("f24", "capital", "大单净买入占比", f24_big_order_ratio),

    ("f25", "chip", "筹码获利盘比例", f25_chip_profit),
    ("f26", "chip", "股东户数变化", f26_holder_change),
    ("f27", "chip", "融券/融资余额分位", f27_margin_ratio),

    ("f28", "safety", "贝塔系数 β", f28_beta),
    ("f29", "safety", "60日年化波动率", f29_volatility),
    ("f30", "safety", "最大回撤修复天数", f30_drawdown_recovery),

    ("f31", "macro", "申万行业景气", f31_industry_prosperity),
    ("f32", "macro", "行业库存周期", f32_inventory_cycle),
    ("f33", "macro", "外盘映射（美股龙头）", f33_us_mapping),
]

DIM_NAMES = {
    "value": "价值估值", "quality": "资产质量", "growth": "盈利成长",
    "trend": "趋势技术面", "momentum": "量价动能", "capital": "主力资金流",
    "chip": "筹码与情绪", "safety": "安全边际", "macro": "景气与宏观",
}


def compute_factors(bundle):
    out = {}
    for key, dim, name, fn in FACTORS:
        try:
            score, value, note = fn(bundle)
        except Exception as e:  # noqa: BLE001
            score, value, note = None, None, f"计算异常: {e}"
        out[key] = {"key": key, "dim": dim, "name": name, "score": score, "value": value, "note": note}
    return out
