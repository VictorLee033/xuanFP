# -*- coding: utf-8 -*-
"""东方财富数据源：实时快照（push2delay）+ 财务数据（数据中心，真实、免token）

- market_snapshot: 全市场 A 股快照（价格/PE-TTM/PB/市值/换手/量比/主力净流入/申万行业/上市日期）
- finance_report: 个股财务主要指标（近4年季度，ROE/扣非ROE/毛利率/营收/净利/负债率/周转/现金流等）
"""
import time

from ..config import get_config
from .base import http_get_json_fallback

FS_A_SHARE = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"

# 多主机容灾：主域名被 WAF/限流拦截时自动切换
CLIST_URLS = [
    "https://push2delay.eastmoney.com/api/qt/clist/get",
    "https://push2.eastmoney.com/api/qt/clist/get",
    "http://push2delay.eastmoney.com/api/qt/clist/get",
]
DATACENTER_URLS = [
    "https://datacenter-web.eastmoney.com/api/data/v1/get",
    "https://datacenter.eastmoney.com/api/data/v1/get",
]
DATACENTER_HEADERS = {"Referer": "https://data.eastmoney.com/"}  # 数据中心反爬需要 Referer

# 快照字段
FIELDS = ("f2,f3,f6,f8,f10,f12,f14,f20,f21,f23,f26,f62,f100,f115")

_FIELD_MAP = {
    "f2": "price", "f3": "pct_chg", "f6": "amount", "f8": "turnover_rate",
    "f10": "volume_ratio", "f12": "code", "f14": "name", "f20": "total_mv",
    "f21": "circ_mv", "f23": "pb", "f26": "list_date", "f62": "main_net_inflow",
    "f100": "industry", "f115": "pe_ttm",
}


def _clean(val):
    if val == "-" or val is None or val == "":
        return None
    return val


def secid_of(ts_code):
    code, market = ts_code.split(".")
    return ("1." if market == "SH" else "0.") + code


def secucode_of(ts_code):
    code, market = ts_code.split(".")
    return f"{code}.{'SH' if market == 'SH' else 'SZ'}"


class EastMoneyClient:
    def __init__(self):
        self._cfg = None

    def _get_cfg(self):
        if self._cfg is None:
            self._cfg = get_config()["eastmoney"]
        return self._cfg

    def invalidate(self):
        self._cfg = None

    # ------------------------------------------------------------------
    def clist_page(self, pn=1, pz=100, fields=FIELDS, fs=FS_A_SHARE, order_field="f20"):
        return http_get_json_fallback(CLIST_URLS, params={
            "pn": pn, "pz": pz, "po": 0, "np": 1, "fltt": 2, "invt": 2,
            "fid": order_field, "fs": fs, "fields": fields,
        }, timeout=30, retries=1)

    def market_snapshot(self, page_size=None):
        """全市场 A 股快照，返回 [{ts_code, ...}]"""
        cfg = self._get_cfg()
        pz = page_size or cfg.get("page_size", 100)  # 东财每页上限 100
        rows = []
        pn = 1
        total = None
        while True:
            j = self.clist_page(pn=pn, pz=pz)
            data = (j or {}).get("data") or {}
            diff = data.get("diff") or []
            if not diff:
                break
            for item in diff:
                mapped = {}
                for k, v in item.items():
                    if k in _FIELD_MAP:
                        mapped[_FIELD_MAP[k]] = _clean(v)
                code = mapped.get("code")
                if not code:
                    continue
                market = "SH" if str(code).startswith(("6", "9", "5")) else "SZ"
                mapped["ts_code"] = f"{code}.{market}"
                for numk in ("price", "pct_chg", "amount", "turnover_rate", "volume_ratio",
                             "total_mv", "circ_mv", "pb", "pe_ttm", "main_net_inflow"):
                    try:
                        if mapped.get(numk) is not None:
                            mapped[numk] = float(mapped[numk])
                    except (TypeError, ValueError):
                        mapped[numk] = None
                rows.append(mapped)
            total = data.get("total") or 0
            if len(rows) >= total:
                break
            pn += 1
            time.sleep(0.05)
        return rows

    # ------------------------------------------------------------------
    def finance_report(self, ts_code, page_size=12):
        """财务主要指标（按报告期降序），返回 [{report_date, report_type, 字段...}]"""
        r = http_get_json_fallback(DATACENTER_URLS, params={
            "reportName": "RPT_F10_FINANCE_MAINFINADATA", "columns": "ALL",
            "filter": f'(SECUCODE="{secucode_of(ts_code)}")',
            "pageNumber": 1, "pageSize": page_size,
            "source": "HSF10", "client": "PC",
            "sortColumns": "REPORT_DATE", "sortTypes": "-1",
        }, headers=DATACENTER_HEADERS, timeout=25, retries=1)
        data = ((r or {}).get("result") or {}).get("data") or []
        out = []
        for d in data:
            rd = str(d.get("REPORT_DATE") or "")[:10].replace("-", "")
            out.append({
                "report_date": rd,
                "report_type": d.get("REPORT_TYPE"),
                "eps": d.get("EPSJB"),
                "bps": d.get("BPS"),
                "revenue": d.get("TOTALOPERATEREVE"),          # 营业总收入(元)
                "gross_margin": d.get("XSMLL"),                # 销售毛利率(%)
                "net_margin": d.get("XSJLL"),                  # 销售净利率(%)
                "roe": d.get("ROEJQ"),                         # 加权ROE(%)
                "roe_dt": d.get("ROEKCJQ"),                    # 扣非加权ROE(%)
                "rev_yoy": d.get("TOTALOPERATEREVETZ"),        # 营收同比(%)
                "profit_yoy": d.get("PARENTNETPROFITTZ"),      # 归母净利同比(%)
                "dedt_profit_yoy": d.get("KCFJCXSYJLRTZ"),     # 扣非净利同比(%)
                "net_profit": d.get("PARENTNETPROFIT"),        # 归母净利润(元)
                "dedt_profit": d.get("KCFJCXSYJLR"),           # 扣非净利润(元)
                "debt_ratio": d.get("ZCFZL"),                  # 资产负债率(%)
                "inv_turn": d.get("CHZZL"),                    # 存货周转率
                "ar_turn": d.get("YSZKZZL"),                   # 应收账款周转率
                "inv_turn_yoy": d.get("INVENTORY_TR_YOY"),     # 存货周转率同比(%)
                "ocf_to_rev": d.get("JYXJLYYSR"),              # 经营现金流/营收
                "ocf_to_profit": d.get("NCO_NETPROFIT"),       # 净现比(经营现金流/净利)
                "fcff": d.get("FCFF_FORWARD"),                 # 自由现金流(元)
                "rd_expense": d.get("RDEXPEND"),               # 研发费用(元)
                "profit_qoq": d.get("DJD_DPNP_QOQ"),           # 单季归母净利环比(%)
                "rev_q_yoy": d.get("DJD_TOI_YOY"),             # 单季营收同比(%)
                "equity_multiplier": d.get("QYCS"),            # 权益乘数
            })
        return out
