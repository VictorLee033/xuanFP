# -*- coding: utf-8 -*-
"""补充基本面/资金/情绪数据源（东方财富数据中心）。

独立于 eastmoney.py 的新模块，提供补因子所需的 6 类真实数据：
- dividend_report:   分红送配（股息率）
- northbound_hold:   北向（沪深股通）持股
- top_list_inst_net: 机构龙虎榜净买入（按交易日聚合）
- holder_number:     股东户数变化
- margin_data:       融资融券明细（融资余额/融券余额）
"""
import logging

from .base import http_get_json_fallback
from .eastmoney import DATACENTER_HEADERS, DATACENTER_URLS, secucode_of

logger = logging.getLogger(__name__)

# 两融用证券端点（RPTA_WEB_* 报告）
SEC_API_URLS = [
    "https://datacenter.eastmoney.com/securities/api/data/get",
    "https://datacenter-web.eastmoney.com/securities/api/data/get",
]


class FundamentalsClient:
    """补充数据源：分红/北向/龙虎榜/股东户数/两融。"""

    # ------------------------------------------------------------------
    def _dc_v1(self, report_name, filter_str, pagesize=100, source="HSF10",
               sort_columns="", sort_types="-1"):
        r = http_get_json_fallback(DATACENTER_URLS, params={
            "reportName": report_name, "columns": "ALL",
            "filter": filter_str, "pageNumber": 1, "pageSize": pagesize,
            "source": source, "client": "PC",
            "sortColumns": sort_columns, "sortTypes": sort_types,
        }, headers=DATACENTER_HEADERS, timeout=25, retries=1)
        return ((r or {}).get("result") or {}).get("data") or []

    def _sec_api(self, type_, filter_str, ps=30):
        r = http_get_json_fallback(SEC_API_URLS, params={
            "type": type_, "sty": "ALL", "filter": filter_str,
            "p": 1, "ps": ps, "sr": -1, "st": "date"},
            headers=DATACENTER_HEADERS, timeout=25, retries=1)
        return ((r or {}).get("result") or {}).get("data") or []

    # ------------------------------------------------------------------
    def dividend_report(self, ts_code):
        """分红送配（按除权除息日降序，最新在前），返回 [{ex_date, pretax_bonus_10}]"""
        data = self._dc_v1("RPT_SHAREBONUS_DET", f'(SECUCODE="{secucode_of(ts_code)}")',
                           pagesize=30, source="HSF10",
                           sort_columns="EX_DIVIDEND_DATE")
        out = []
        for d in data:
            ex = str(d.get("EX_DIVIDEND_DATE") or "")[:10]
            bonus = d.get("PRETAX_BONUS_RMB")
            if not ex or bonus is None:
                continue
            try:
                out.append({"ex_date": ex, "pretax_bonus_10": float(bonus)})
            except (TypeError, ValueError):
                continue
        return out

    def northbound_hold(self, ts_code):
        """最新一期北向持股，返回 {trade_date, hold_ratio, change_rate}（季度披露）"""
        data = self._dc_v1("RPT_MUTUAL_HOLDSTOCKNORTH_STA",
                           f'(SECUCODE="{secucode_of(ts_code)}")',
                           pagesize=1, source="HSF10")
        if not data:
            return None
        d = data[0]
        return {
            "trade_date": str(d.get("TRADE_DATE") or "")[:10],
            "hold_ratio": d.get("HOLD_SHARES_RATIO"),
            "change_rate": d.get("CHANGE_RATE"),
        }

    def top_list_inst_net(self, trade_date):
        """某交易日机构专用席位净买入（按股票聚合），返回 {code6: 净额(元)}"""
        result = {}
        for rn in ("RPT_BILLBOARD_DAILYDETAILSBUY", "RPT_BILLBOARD_DAILYDETAILSSELL"):
            try:
                data = self._dc_v1(rn, f"(TRADE_DATE='{trade_date}')",
                                   pagesize=800, source="WEB")
            except Exception as e:  # noqa: BLE001
                logger.debug("龙虎榜 %s 失败: %s", rn, e)
                data = []
            for d in data:
                dept = d.get("OPERATEDEPT_NAME") or ""
                if "机构" not in dept:
                    continue
                code = d.get("SECURITY_CODE") or str(d.get("SECUCODE") or "")[:6]
                if not code:
                    continue
                code = str(code).zfill(6)
                try:
                    net = float(d.get("NET") or 0)
                except (TypeError, ValueError):
                    net = 0.0
                result[code] = result.get(code, 0.0) + net
        return result

    def holder_number(self, ts_code):
        """股东户数变化，返回 [{end_date, holder_num, ratio}]（降序）"""
        data = self._dc_v1("RPT_HOLDERNUM_DET", f'(SECUCODE="{secucode_of(ts_code)}")',
                           pagesize=4, source="HSF10")
        out = []
        for d in data:
            end = str(d.get("END_DATE") or "")[:10]
            num = d.get("HOLDER_NUM")
            if not end or num is None:
                continue
            out.append({"end_date": end, "holder_num": num, "ratio": d.get("HOLDER_NUM_RATIO")})
        return out

    def margin_data(self, ts_code, days=30):
        """两融明细，返回 [{date, rzye(融资余额), rqye(融券余额)}]（降序）"""
        code = ts_code.split(".")[0]
        data = self._sec_api("RPTA_WEB_RZRQ_GGMX", f'(scode="{code}")', ps=days)
        out = []
        for d in data:
            date = str(d.get("DATE") or "")[:10]
            rzye = d.get("RZYE")
            rqye = d.get("RQYE")
            if not date or rzye is None or rqye is None:
                continue
            out.append({"date": date, "rzye": rzye, "rqye": rqye})
        return out
