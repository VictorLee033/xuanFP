# -*- coding: utf-8 -*-
"""硬性剔除规则 + 财务入围门槛（基于东方财富快照 + 数据中心财务）"""
from datetime import date

NEW_STOCK_DAYS = 130
MIN_DAILY_AMOUNT = 8.0e7       # 当日成交额 8000万元（元）
GOODWILL_RATIO_WARN = 0.35
MAX_PE_TTM = 80.0
MIN_ROE = 6.0
MIN_REV_YOY = 3.0
MAX_DEBT_RATIO = 78.0


def check_hard_exclusion(snapshot):
    """一票否决检查（ST/停牌/新股/流动性）。返回 (excluded, reason, warnings[])"""
    warnings = []
    name = (snapshot.get("name") or "").upper()
    if "ST" in name:
        return True, "ST/*ST 股", warnings

    price = snapshot.get("price")
    amount = snapshot.get("amount")
    if price is None or amount is None or amount <= 0:
        return True, "停牌或当日无成交", warnings

    list_date = str(snapshot.get("list_date") or "")
    if len(list_date) == 8:
        try:
            ld = date(int(list_date[:4]), int(list_date[4:6]), int(list_date[6:8]))
            if (date.today() - ld).days < NEW_STOCK_DAYS:
                return True, f"新股（上市{ld}，不足90交易日）", warnings
        except ValueError:
            pass
    elif not list_date:
        warnings.append("上市日期缺失，新股剔除规则未执行")

    if amount < MIN_DAILY_AMOUNT:
        return True, f"流动性枯竭（当日额{amount/1e4:.0f}万元<8000万）", warnings

    return False, "", warnings


def check_financial_gate(fin_rows, pe_ttm):
    """财务入围门槛。fin_rows: 数据中心财务（report_date 降序）
    返回 (passed, reason, warnings[])
    """
    warnings = []
    if not fin_rows:
        return False, "财务数据缺失", warnings

    def num(v):
        try:
            return float(v) if v not in (None, "", "-") else None
        except (TypeError, ValueError):
            return None

    annual = [r for r in fin_rows if r.get("report_type") == "年报"]
    latest = fin_rows[0]
    latest_annual = annual[0] if annual else latest

    pe = num(pe_ttm)
    if pe is not None and not (0 < pe < MAX_PE_TTM):
        return False, f"PE-TTM={pe:.1f} 不在 (0,{MAX_PE_TTM:.0f})", warnings

    roe = num(latest_annual.get("roe"))
    if roe is None:
        roe = num(latest.get("roe"))
    if roe is not None and roe <= MIN_ROE:
        return False, f"ROE={roe:.2f}% ≤ {MIN_ROE}%", warnings

    rev_yoy = num(latest_annual.get("rev_yoy"))
    if rev_yoy is None:
        rev_yoy = num(latest.get("rev_yoy"))
    if rev_yoy is not None and rev_yoy <= MIN_REV_YOY:
        return False, f"营收同比={rev_yoy:.2f}% ≤ {MIN_REV_YOY}%", warnings

    debt = num(latest.get("debt_ratio"))
    if debt is not None and debt >= MAX_DEBT_RATIO:
        return False, f"资产负债率={debt:.1f}% ≥ {MAX_DEBT_RATIO}%", warnings

    return True, "通过", warnings
