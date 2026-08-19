# -*- coding: utf-8 -*-
"""扫描引擎（领域层核心）：全 A 股多因子扫描流水线。

依赖注入：数据源客户端、缓存仓库、扫描仓库、评分参数均由外部（服务层）注入，
本模块不直接读配置、不直接碰数据库连接，便于单测与替换实现。

阶段0  全市场快照
阶段1  硬性剔除（ST/停牌/新股/流动性/PE-TTM）
阶段2  财务入围门槛（ROE/营收增速/资产负债率）
阶段3  九维 37 因子评分（K线 + 财务 + 快照）
阶段4  综合排名 + Top20 + Top3 核心逻辑 + 历史存档
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from ...errors import DataSourceError
from ...datasources.news import stock_news
from . import chip as chip_calc
from . import factors, filters, scoring

logger = logging.getLogger(__name__)


class ScanEngine:
    """扫描引擎。所有外部依赖注入，内部只做业务编排。"""

    def __init__(self, em, tx, fund, cache_repo, scan_repo, weights, scanner_cfg,
                 progress=None, top5_repo=None):
        self.em = em                    # 东财数据源（快照/财务）
        self.tx = tx                    # 腾讯/多源 K线
        self.fund = fund                # 补充数据源（分红/北向/龙虎榜/股东户数/两融）
        self.cache_repo = cache_repo    # 缓存仓库
        self.scan_repo = scan_repo      # 扫描历史仓库
        self.top5_repo = top5_repo      # Top5 回测记录仓库（可为 None，则跳过记录）
        self.weights = weights          # 九维权重
        self.cfg = scanner_cfg          # 扫描参数（universe_limit/kline_days/...）
        self.progress_fn = progress
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _progress(self, phase, done, total, message=""):
        if self.progress_fn:
            try:
                self.progress_fn(phase, done, total, message)
            except Exception:
                pass

    def _batch(self, items, fn, workers=20, phase="", label=""):
        """并发拉取：items=[(key, arg)]; fn(arg)->rows。单条失败置 None，不中断整体。"""
        results = {}
        total = len(items)
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fn, arg): key for key, arg in items}
            for fut in as_completed(futs):
                key = futs[fut]
                try:
                    results[key] = fut.result()
                except Exception as e:  # noqa: BLE001
                    logger.debug("批量拉取 %s 失败: %s", key, e)
                    results[key] = None
                done += 1
                if phase and done % 50 == 0:
                    self._progress(phase, done, total, f"{label} {done}/{total}")
        if phase:
            self._progress(phase, done, total, f"{label} {done}/{total}")
        return results

    def _cached(self, key, fn, ttl):
        """带缓存的单值获取；取数失败返回 None（防御，不中断）。"""
        hit = self.cache_repo.get(key)
        if hit is not None:
            return hit
        try:
            val = fn()
        except Exception as e:  # noqa: BLE001
            logger.debug("取数失败 %s: %s", key, e)
            return None
        if val is not None:
            self.cache_repo.set(key, val, ttl)
        return val

    # ------------------------------------------------------------------
    def run(self):
        t0 = time.time()
        warnings = []
        limit = int(self.cfg.get("universe_limit", 0) or 0)
        kline_days = int(self.cfg.get("kline_days", 320))

        # ---------- 阶段0：全市场快照 ----------
        self._progress("snapshot", 0, 1, "拉取全市场行情快照…")
        try:
            snapshots = self.em.market_snapshot()
        except Exception as e:  # noqa: BLE001
            logger.error("行情快照失败: %s", e)
            raise DataSourceError(
                "行情数据源连接失败（东财快照被拦截或限流），请稍后重试。"
                "若前端行情面板正常，说明是瞬时拦截，稍等重试即可。"
            ) from e

        if not snapshots:
            raise DataSourceError("行情快照返回空数据，请稍后重试。")

        if limit and limit > 0:
            snapshots = sorted(snapshots, key=lambda s: (s.get("total_mv") or 0), reverse=True)[:limit]
        snap_map = {s["ts_code"]: s for s in snapshots}
        universe = list(snap_map.keys())
        self._progress("snapshot", 1, 1, f"快照完成，共 {len(universe)} 只")

        # ---------- 阶段1：硬性剔除 ----------
        excluded = {}
        kept1 = []
        for code in universe:
            snap = snap_map[code]
            ex, reason, ws = filters.check_hard_exclusion(snap)
            warnings.extend(ws)
            if ex:
                excluded[code] = reason
                continue
            pe = snap.get("pe_ttm")
            if pe is not None and not (0 < pe < filters.MAX_PE_TTM):
                excluded[code] = f"PE-TTM={pe:.1f} 超出(0,{filters.MAX_PE_TTM:.0f})"
                continue
            kept1.append(code)
        self._progress("exclude", len(kept1), len(universe),
                       f"硬性剔除 {len(excluded)} 只，剩余 {len(kept1)}")

        # ---------- 阶段2：财务门槛 ----------
        fin_items = [(c, c) for c in kept1]
        self._progress("fin", 0, len(fin_items), f"拉取财务数据（{len(fin_items)} 只）…")

        def fetch_fin(ts_code):
            key = "em:fin:" + ts_code
            hit = self.cache_repo.get(key)
            if hit is not None:
                return hit
            rows = self.em.finance_report(ts_code, page_size=12)
            self.cache_repo.set(key, rows, 14 * 86400)
            return rows

        fin_map = self._batch(fin_items, fetch_fin,
                              workers=int(self.cfg.get("max_workers", 24)),
                              phase="fin", label="财务数据")

        kept2 = []
        for code in kept1:
            fin_rows = fin_map.get(code) or []
            pe = snap_map[code].get("pe_ttm")
            passed, reason, ws = filters.check_financial_gate(fin_rows, pe)
            warnings.extend(ws)
            if passed:
                kept2.append(code)
            else:
                excluded[code] = reason  # 门槛未过也计入剔除原因，便于诊断
        self._progress("gate", len(kept2), len(kept1),
                       f"财务门槛入围 {len(kept2)} 只（淘汰 {len(kept1)-len(kept2)}）")

        # ---------- 阶段3：九维评分 ----------
        pool = kept2
        self._progress("score", 0, 1, f"入围 {len(pool)} 只，开始九维评分…")

        try:
            bench = self.tx.kline("000300.SH", days=120)
        except Exception as e:  # noqa: BLE001
            logger.warning("基准指数K线获取失败，β因子将降权: %s", e)
            bench = []
        us_mom = self._us_momentum()

        kline_items = [(c, c) for c in pool]
        self._progress("kline", 0, len(kline_items), "拉取K线…")
        kline_map = self._batch(kline_items, lambda c: self.tx.kline(c, days=kline_days),
                                workers=int(self.cfg.get("max_workers", 24)),
                                phase="kline", label="K线")

        # ---------- 补充数据：分红/北向/股东户数/两融（按股票）+ 机构龙虎榜（按交易日） ----------
        workers = int(self.cfg.get("max_workers", 24))
        self._progress("extra", 0, 1, "拉取补充数据（分红/北向/股东户数/两融/龙虎榜）…")
        pool_items = [(c, c) for c in pool]

        dividend_map = self._batch(
            pool_items, lambda c: self._cached("em:div:" + c,
                                               lambda: self.fund.dividend_report(c), 14 * 86400),
            workers=workers)
        northbound_map = self._batch(
            pool_items, lambda c: self._cached("em:nb:" + c,
                                               lambda: self.fund.northbound_hold(c), 14 * 86400),
            workers=workers)
        holder_map = self._batch(
            pool_items, lambda c: self._cached("em:holder:" + c,
                                               lambda: self.fund.holder_number(c), 14 * 86400),
            workers=workers)
        margin_map = self._batch(
            pool_items, lambda c: self._cached("em:margin:" + c,
                                               lambda: self.fund.margin_data(c, days=30), 86400),
            workers=workers)

        # 机构龙虎榜：近10个交易日机构专用席位净买入聚合
        trade_dates = [b["date"] for b in (bench or [])[-10:]]
        inst_net_by_code = {}
        for d in trade_dates:
            net = self._cached("em:toplist:" + d,
                               lambda dd=d: self.fund.top_list_inst_net(dd), 86400) or {}
            for code, v in net.items():
                inst_net_by_code[code] = inst_net_by_code.get(code, 0.0) + v

        # 新闻（舆情热度/方向，供情绪因子）
        news_map = self._batch(
            pool_items, lambda c: self._cached("em:news:" + c,
                                               lambda: stock_news(c, page_size=20), 86400),
            workers=workers)

        # RPS：20 日收益在评分池中的分位（股价相对强度）
        pool_ret = {}
        for c in pool:
            bars = kline_map.get(c) or []
            if len(bars) >= 21 and bars[-21]["close"]:
                pool_ret[c] = bars[-1]["close"] / bars[-21]["close"] - 1
        rets_list = list(pool_ret.values())
        rps_map = {}
        if rets_list:
            for c in pool:
                r = pool_ret.get(c)
                if r is not None:
                    rps_map[c] = sum(1 for x in rets_list if x <= r) / len(rets_list) * 100
        self._progress("extra", 1, 1, "补充数据完成")

        # ---------- 评分（两遍：先算原始维度分，再池内百分位校准） ----------
        staged = []
        for code in pool:
            if self._cancel:
                break
            snap = snap_map.get(code) or {}
            float_shares = None
            if snap.get("circ_mv") and snap.get("price"):
                float_shares = snap["circ_mv"] / snap["price"]
            chip_data = chip_calc.chip_distribution(kline_map.get(code) or [], float_shares)
            bundle = {
                "ts_code": code,
                "name": snap.get("name") or code,
                "industry": snap.get("industry"),
                "snapshot": snap,
                "fin": fin_map.get(code) or [],
                "kline": kline_map.get(code) or [],
                "bench": bench,
                "us_momentum": us_mom,
                "dividends": dividend_map.get(code) or [],
                "northbound": northbound_map.get(code),
                "holders": holder_map.get(code) or [],
                "margin": margin_map.get(code) or [],
                "inst_net": inst_net_by_code.get(code.split(".")[0]),
                "news": news_map.get(code) or [],
                "rps": rps_map.get(code),
                "chip": chip_data,
            }
            bundle["sw_industry"] = factors.SW_MAP.get(bundle["industry"] or "", bundle["industry"] or "")
            try:
                factor_result = factors.compute_factors(bundle)
                raw_dims = scoring.dimension_scores(factor_result)
            except Exception as e:  # noqa: BLE001
                logger.exception("评分异常 %s: %s", code, e)
                continue
            staged.append({
                "ts_code": code,
                "name": bundle["name"],
                "industry": bundle["industry"],
                "sw_industry": bundle["sw_industry"],
                "price": snap.get("price"),
                "pct_chg": snap.get("pct_chg"),
                "amount": snap.get("amount"),
                "total_mv": snap.get("total_mv"),
                "factors": factor_result,
                "dims": raw_dims,
                "missing_count": sum(1 for v in factor_result.values() if v["score"] is None),
            })

        # 池内百分位校准（每个维度的原始分 → 百分位排名）
        for dim in scoring.DIM_ORDER:
            vals = [s["dims"][dim]["raw_score"] for s in staged
                    if s["dims"][dim]["raw_score"] is not None]
            for s in staged:
                r = s["dims"][dim]["raw_score"]
                s["dims"][dim]["score"] = (round(scoring.percentile_rank(vals, r), 2)
                                            if r is not None and vals else None)

        # 综合分（加权合成百分位维度分）
        # 先算「原始综合分」，再对整个评分池做一次百分位校准：
        # 保证综合分分布均匀、Top 股票能进高阈值档（建议加仓 ≥85 等）。
        for s in staged:
            s["combined_raw"] = scoring.combine(s["dims"], self.weights)

        raw_pool = [s["combined_raw"] for s in staged if s["combined_raw"] is not None]
        for s in staged:
            s["combined"] = (round(scoring.percentile_rank(raw_pool, s["combined_raw"]), 2)
                             if s["combined_raw"] is not None and raw_pool else None)

        results = []
        scored = 0
        for s in staged:
            combined = s["combined"]
            if combined is None:
                continue
            results.append({
                "ts_code": s["ts_code"],
                "name": s["name"],
                "industry": s["industry"],
                "sw_industry": s["sw_industry"],
                "price": s["price"],
                "pct_chg": s.get("pct_chg"),
                "amount": s.get("amount"),
                "total_mv": s.get("total_mv"),
                "score": round(float(combined), 2),
                "dimensions": s["dims"],
                "factors": s["factors"],
                "missing_count": s["missing_count"],
                "flags": (["强烈关注"] if combined > 85 else []),
            })
            scored += 1
        self._progress("score", scored, len(pool), f"评分完成 {scored} 只")

        results.sort(key=lambda r: r["score"], reverse=True)

        # ---------- 阶段4：输出与存档 ----------
        top20 = [{k: r[k] for k in ("ts_code", "name", "industry", "sw_industry", "price", "score", "flags")}
                 for r in results[:10]]
        summary = self._build_summary(results, len(universe), len(pool), warnings)

        run_id = self.scan_repo.create_run(status="done", universe_size=len(universe))
        self.scan_repo.update_run(
            run_id,
            passed_size=len(pool), top20=top20, summary=summary,
            stats={"duration": round(time.time() - t0, 1),
                   "date": date.today().isoformat(),
                   "universe": len(universe), "pool": len(pool),
                   "excluded": len(excluded)},
        )
        for i, r in enumerate(results[:100]):
            self.scan_repo.save_result(
                run_id, i + 1, r["ts_code"], r["name"], r["price"],
                r["industry"], r["sw_industry"], r["score"], r["dimensions"],
                r["factors"], r["flags"],
            )

        # 自动记录 Top5 到回测库（同一天多次扫描 → 只保留最后一次）
        if self.top5_repo is not None:
            try:
                self.top5_repo.replace_day(date.today().isoformat(), [
                    {
                        "rank": i + 1,
                        "ts_code": r["ts_code"],
                        "name": r["name"],
                        "close_price": r["price"],
                        "pct_chg": r.get("pct_chg"),
                        "amount": r.get("amount"),
                        "total_mv": r.get("total_mv"),
                        "score": r["score"],
                        "industry": r.get("industry"),
                        "sw_industry": r.get("sw_industry"),
                        "tags": r.get("flags") or [],
                        "dimensions": {d: v.get("score") for d, v in (r.get("dimensions") or {}).items()},
                    }
                    for i, r in enumerate(results[:5])
                ])
            except Exception as e:  # noqa: BLE001
                logger.warning("Top5 回测记录失败: %s", e)

        logger.info("扫描完成: run=%s universe=%s pool=%s 耗时=%.1fs",
                    run_id, len(universe), len(pool), time.time() - t0)
        self._progress("done", 1, 1, f"扫描完成，耗时 {time.time()-t0:.0f}s")
        return {
            "run_id": run_id, "top20": top20, "summary": summary,
            "duration": round(time.time() - t0, 1),
            "universe_size": len(universe), "pool_size": len(pool),
            "excluded_size": len(excluded),
        }

    # ------------------------------------------------------------------
    def _us_momentum(self):
        out = {}
        for sw, symbol in factors.US_MAP.items():
            try:
                bars = self.tx.kline_us(symbol, days=30)
                if len(bars) >= 21:
                    out[symbol] = bars[-1]["close"] / bars[-21]["close"] - 1
            except Exception as e:  # noqa: BLE001
                logger.debug("外盘映射 %s 失败: %s", symbol, e)
        return out

    def _build_summary(self, results, universe_size, pool_size, warnings):
        head = results[:10]
        ind_count = {}
        for r in head:
            ind = r.get("sw_industry") or r.get("industry") or "未知"
            ind_count[ind] = ind_count.get(ind, 0) + 1
        top_ind = sorted(ind_count.items(), key=lambda x: -x[1])[:5]

        dim_sum = {}
        for r in head:
            for dim, d in r["dimensions"].items():
                # 维度分析用「原始绝对分」体现真实强弱（综合分用百分位校准）
                v = d.get("raw_score", d.get("score"))
                if v is not None:
                    dim_sum.setdefault(dim, []).append(v)
        dim_avg = {dim: round(sum(v) / len(v), 1) for dim, v in dim_sum.items() if v}
        top_dims = sorted(dim_avg.items(), key=lambda x: -x[1])[:3]

        strong = [r for r in head if r["score"] > 85]
        strong_inds = {}
        for r in strong:
            ind = r.get("sw_industry") or r.get("industry") or "未知"
            strong_inds[ind] = strong_inds.get(ind, 0) + 1

        lines = []
        if top_ind:
            inds = "、".join(f"{i}({n}只)" for i, n in top_ind[:3])
            lines.append(f"今日上榜股票主要集中在 {inds} 等行业，市场风格偏向这些景气方向。")
        if top_dims:
            dims = "、".join(f"{scoring.DIM_NAMES[d]}({s}分)" for d, s in top_dims[:3])
            lines.append(f"综合得分主要由 {dims} 等维度驱动，其中「{scoring.DIM_NAMES[top_dims[0][0]]}」贡献最大。")
        if strong:
            si = "、".join(f"{i}({n}只)" for i, n in strong_inds.items())
            lines.append(f"综合得分超过85分的【强烈关注】标的共 {len(strong)} 只，集中于 {si}，呈现高成长+强资金共振特征。")
        else:
            lines.append("今日无综合得分超过85分的标的，市场整体评分中性，建议谨慎追高。")
        lines.append(f"本次扫描覆盖全市场 {universe_size} 只，硬性剔除与财务门槛后入围评分池 {pool_size} 只。")

        data_gaps = [w for w in warnings]
        data_gaps += ["筹码获利盘比例、行业库存周期已从评分体系中删除（免费数据无法精确获取）",
                      "审计意见与大股东质押率数据缺失：双高暴雷规则降级为商誉/净资产>35%预警（简化）",
                      "流动性门槛以当日成交额代理近5日均额（简化）"]
        return {
            "top3_logic": lines[:3],
            "industry_stats": [{"industry": i, "count": c} for i, c in top_ind],
            "dimension_avg": dim_avg,
            "strong_count": len(strong),
            "date": date.today().isoformat(),
            "universe_size": universe_size,
            "pool_size": pool_size,
            "data_gaps": sorted(set(data_gaps)),
        }
