# -*- coding: utf-8 -*-
"""LLM 分析报告生成（DeepSeek / OpenAI 兼容接口；无 Key 时使用模板 Mock）"""
import json

import requests

from ..config import get_config
from ..domain.scanner.scoring import DIM_NAMES


def _llm_config():
    return get_config().get("llm", {})


def llm_available():
    return bool((_llm_config().get("api_key") or "").strip())


def _chat(messages, temperature=0.7, max_tokens=1200):
    cfg = _llm_config()
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {cfg['api_key']}",
                 "Content-Type": "application/json"},
        json={"model": cfg.get("model", "deepseek-chat"),
              "messages": messages,
              "temperature": temperature,
              "max_tokens": max_tokens},
        timeout=cfg.get("timeout", 90),
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _factor_summary(stock):
    """抽取因子明细，按维度组织成文本"""
    dims = stock.get("dimensions") or {}
    factors = stock.get("factors") or {}
    lines = []
    order = ["value", "quality", "growth", "trend", "momentum", "capital", "chip", "safety", "macro"]
    for dim in order:
        d = dims.get(dim) or {}
        dname = DIM_NAMES.get(dim, dim)
        dscore = d.get("score")
        head = f"- {dname}：{dscore} 分" if dscore is not None else f"- {dname}：数据缺失（已降权）"
        details = []
        for k, v in factors.items():
            if v.get("dim") == dim and v.get("score") is not None:
                details.append(f"    {v['name']} {v['score']:.0f}分（{v.get('note')}）")
        lines.append(head)
        lines.extend(details[:4])
    return "\n".join(lines)


def generate_report(stock, market_summary=None):
    """生成单只股票的 LLM 分析报告；无 Key 时用模板 Mock"""
    name = stock.get("name", stock.get("ts_code"))
    ts_code = stock.get("ts_code")
    price = stock.get("price")
    industry = stock.get("industry") or "未知"
    score = stock.get("score")
    factors_text = _factor_summary(stock)

    if llm_available():
        try:
            prompt = f"""你是资深A股量化分析师。请基于以下多因子扫描数据，为股票【{name}（{ts_code}）】撰写一份专业的投资分析报告（中文，Markdown 格式，500字左右）。

基本信息：
- 最新价：{price} 元，所属行业：{industry}
- 多因子综合得分：{score}/100

九维评分与因子明细：
{factors_text}

{'市场背景：' + market_summary if market_summary else ''}

报告结构要求：
1. **核心结论**（2-3句话）
2. **基本面解读**（财务质量、成长性、估值）
3. **技术面与资金面解读**（趋势、量价、主力资金）
4. **主要风险提示**（结合低分因子与行业风险）
5. **操作建议**（明确给出关注/观望/回避，附理由）

注意：报告仅基于量化因子数据，不构成投资建议。避免绝对化表述。"""
            return _chat([{"role": "user", "content": prompt}])
        except Exception:
            pass  # LLM 失败降级到 Mock
    return _mock_report(stock)


def _mock_report(stock):
    name = stock.get("name", stock.get("ts_code"))
    ts_code = stock.get("ts_code")
    price = stock.get("price")
    industry = stock.get("industry") or "未知"
    score = stock.get("score")
    dims = stock.get("dimensions") or {}
    factors = stock.get("factors") or {}

    def dim_s(dim):
        d = dims.get(dim) or {}
        return d.get("score")

    strong = []
    weak = []
    for k, v in factors.items():
        if v.get("score") is None:
            continue
        if v["score"] >= 80:
            strong.append(v["name"])
        elif v["score"] <= 25:
            weak.append(v["name"])
    strong = list(dict.fromkeys(strong))[:5]
    weak = list(dict.fromkeys(weak))[:4]

    return f"""## 核心结论
{name}（{ts_code}）今日多因子综合得分 **{score} 分**，在扫描池中表现{'强势' if score > 85 else '良好' if score > 70 else '中等'}。当前价 {price} 元，所属 {industry} 行业。{'综合得分超过85分，符合【强烈关注】标准。' if score > 85 else ''}

## 基本面解读
- 价值估值维度得分：{dim_s('value')} 分；资产质量：{dim_s('quality')} 分；盈利成长：{dim_s('growth')} 分。
- 优势因子：{'、'.join(strong) if strong else '暂无特别突出的高分因子'}。

## 技术面与资金面解读
- 趋势技术面：{dim_s('trend')} 分；量价动能：{dim_s('momentum')} 分；主力资金流：{dim_s('capital')} 分。
- 筹码与情绪：{dim_s('chip')} 分；安全边际：{dim_s('safety')} 分；景气与宏观：{dim_s('macro')} 分。

## 主要风险提示
- 低分因子：{'、'.join(weak) if weak else '无显著低分因子（部分因子因数据缺失已降权处理）'}。
- 请注意：筹码获利盘、北向持股、行业库存周期等数据源缺失，相关维度已自动降权，分析覆盖度有限。

## 操作建议
**{'重点关注' if score > 85 else '跟踪观察' if score > 70 else '谨慎观望'}**。建议结合行业景气度与大盘环境综合判断，严格控制仓位。

> ⚠️ 本报告由量化因子模板生成（未配置大模型 API Key），仅供参考，不构成投资建议。
"""


def generate_market_summary(summary):
    """生成市场综述（Top3 核心逻辑的展开版）"""
    if not llm_available():
        return None
    try:
        prompt = f"""你是A股市场策略分析师。以下是一次全市场多因子扫描的统计结果，请用中文（Markdown）写一段 300 字以内的市场综述，总结今日市场风格与机会方向：

{json.dumps(summary, ensure_ascii=False, indent=1)}

注意：仅基于以上统计，不编造数据，不构成投资建议。"""
        return _chat([{"role": "user", "content": prompt}], temperature=0.5, max_tokens=600)
    except Exception:
        return None
