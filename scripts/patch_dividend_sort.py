# -*- coding: utf-8 -*-
"""补丁：修复 fundamentals.py 分红数据排序（按除权日降序、加大拉取量）

背景：RPT_SHAREBONUS_DET 默认升序返回最旧的 12 条分红，导致 f2 股息率
对上市较久的股票（如茅台/平安）取不到近 12 个月分红 → 股息率恒为 None。
"""
import io

P = r"C:\Users\89689\Desktop\dsh\xuanFP\backend\datasources\fundamentals.py"


def main():
    s = io.open(P, encoding="utf-8").read()

    # 1) _dc_v1 增加 sort_columns 参数
    old1 = 'def _dc_v1(self, report_name, filter_str, pagesize=100, source="HSF10"):'
    new1 = ('def _dc_v1(self, report_name, filter_str, pagesize=100, source="HSF10",\n'
            '               sort_columns="", sort_types="-1"):')
    old2 = '"sortColumns": "", "sortTypes": "-1",'
    new2 = '"sortColumns": sort_columns, "sortTypes": sort_types,'

    # 2) dividend_report 按除权除息日降序（最新在前），pageSize 加大到 30
    old3 = ('data = self._dc_v1("RPT_SHAREBONUS_DET", '
            'f\'(SECUCODE="{secucode_of(ts_code)}")\',\n'
            '                           pagesize=12, source="HSF10")')
    new3 = ('data = self._dc_v1("RPT_SHAREBONUS_DET", '
            'f\'(SECUCODE="{secucode_of(ts_code)}")\',\n'
            '                           pagesize=30, source="HSF10",\n'
            '                           sort_columns="EX_DIVIDEND_DATE")')

    assert old1 in s, "未找到 _dc_v1 签名"
    assert old2 in s, "未找到 sortColumns 片段"
    assert old3 in s, "未找到 dividend_report 调用"
    s = s.replace(old1, new1).replace(old2, new2).replace(old3, new3)
    io.open(P, "w", encoding="utf-8").write(s)
    print("补丁应用成功 ✓")


if __name__ == "__main__":
    main()
