# -*- coding: utf-8 -*-
"""扫描引擎：全 A 股多因子扫描（隔夜选股）

数据源：东方财富快照（价格/估值/流动性/资金流/行业）+ 东方财富数据中心（财务，真实）
        + 腾讯K线（技术面）+ 新浪/腾讯美股（外盘映射）

阶段0  全市场快照
阶段1  硬性剔除（ST/停牌/新股/流动性/PE-TTM）
阶段2  财务入围门槛（ROE/营收增速/资产负债率，来自数据中心）
阶段3  九维 37 因子评分（K线 + 财务 + 快照）
阶段4  综合排名 + Top20 + Top3 核心逻辑 + 历史存档
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from ..config import get_config
from ..datasources import EastMoneyClient, TencentClient
from ..storage import history as hist
from ..storage.cache import cache_get, cache_set
from . import filters, factors, scoring


class ScanEngine:
    def __init__(self, progress=None):
        self.em = EastMoneyClient()
        self.tx = TencentClient()
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
        """items: [(key, arg)]; fn(arg) -> rows。返回 {key: rows}"""
        results = {}
        total = len(items)
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fn, arg): key for key, arg in items}
            for fut in as_completed(futs):
                key = futs[fut]
                try:
                    results[key] = fut.result()
                except Exception:
                    results[key] = None
                done += 1
                if phase and done % 50 == 0:
                    self._progress(phase, done, total, f"{label} {done}/{total}")
        if phase:
            self._progress(phase, done, total, f"{label} {done}/{total}")
        return results

    # ------------------------------------------------------------------
    def run(self):
        t0 = time.time()
        cfg = get_config()
        weights = cfg["scanner"]["weights"]
        warnings = []

        # ---------- 阶段0：全市场快照 ----------
        self._progress("snapshot", 0, 1, "拉取全市场行情快照…")
        try:
            snapshots = self.em.market_snapshot()
        except Exception as e:
            # 行情源全部失败：扫描无法进行，给出明确错误
            raise RuntimeError(
                f"行情数据源连接失败（东财快照被拦截或限流）：{str(e)[:120]}。"
                f"请稍后重试，或在「设置」中检查网络；前端行情面板若正常说明仅是瞬时拦截。") from e
        limit = int(cfg["scanner"].get("universe_limit", 0) or 0)
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
            hit = cache_get(key)
            if hit is not None:
                return hit
            rows = self.em.finance_report(ts_code, page_size=12)
            cache_set(key, rows, 14 * 86400)
            return rows

        fin_map = self._batch(fin_items, fetch_fin, workers=24, phase="fin", label="财务数据")

        kept2 = []
        gate_failed = {}
        for code in kept1:
            fin_rows = fin_map.get(code) or []
            pe = snap_map[code].get("pe_ttm")
            passed, reason, ws = filters.check_financial_gate(fin_rows, pe)
            warnings.extend(ws)
            if passed:
                kept2.append(code)
            else:
                gate_failed[code] = reason
        self._progress("gate", len(kept2), len(kept1),
                       f"财务门槛入围 {len(kept2)} 只（淘汰 {len(kept1)-len(kept2)}）")

        # ---------- 阶段3：九维评分 ----------
        pool = kept2
        self._progress("score", 0, 1, f"入围 {len(pool)} 只，开始九维评分…")

        try:
            bench = self.tx.kline("000300.SH", days=120)
        except Exception:
            bench = []  # 基准指数失败时 β 因子降权，不中断扫描
        us_mom = self._us_momentum()

        kline_items = [(c, c) for c in pool]
        self._progress("kline", 0, len(kline_items), "拉取K线…")
        kline_map = self._batch(
            kline_items,
            lambda c: self.tx.kline(c, days=cfg["scanner"]["kline_days"]),
            workers=24, phase="kline", label="K线")

        results = []
        scored = 0
        for code in pool:
            if self._cancel:
                break
            snap = snap_map.get(code) or {}
            bundle = {
                "ts_code": code,
                "name": snap.get("name") or code,
                "industry": snap.get("industry"),
                "snapshot": snap,
                "fin": fin_map.get(code) or [],
                "kline": kline_map.get(code) or [],
                "bench": bench,
                "us_momentum": us_mom,
            }
            bundle["sw_industry"] = factors.SW_MAP.get(bundle["industry"] or "", bundle["industry"] or "")
            factor_result = factors.compute_factors(bundle)
            combined, dims, missing = scoring.aggregate(factor_result, weights)
            if combined is None:
                continue
            results.append({
                "ts_code": code,
                "name": bundle["name"],
                "industry": bundle["industry"],
                "sw_industry": bundle["sw_industry"],
                "price": snap.get("price"),
                "score": round(float(combined), 2),
                "dimensions": dims,
                "factors": factor_result,
                "missing_count": len(missing),
                "flags": (["强烈关注"] if combined > 85 else []),
            })
            scored += 1
        self._progress("score", scored, len(pool), f"评分完成 {scored} 只")

        results.sort(key=lambda r: r["score"], reverse=True)

        # ---------- 阶段4：输出与存档 ----------
        top20 = [{k: r[k] for k in ("ts_code", "name", "industry", "sw_industry", "price", "score", "flags")}
                 for r in results[:20]]
        summary = self._build_summary(results, top20, len(universe), len(pool), warnings)

        run_id = hist.create_run(status="done", universe_size=len(universe))
        hist.update_run(run_id, passed_size=len(pool), top20=top20, summary=summary,
                        stats={"duration": round(time.time() - t0, 1),
                               "date": date.today().isoformat(),
                               "universe": len(universe), "pool": len(pool),
                               "excluded": len(excluded)})
        for i, r in enumerate(results[:100]):
            hist.save_result(run_id, i + 1, r["ts_code"], r["name"], r["price"],
                             r["industry"], r["sw_industry"], r["score"], r["dimensions"],
                             r["factors"], r["flags"])

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
            except Exception:
                continue
        return out

    def _build_summary(self, results, top20, universe_size, pool_size, warnings):
        head = results[:20]
        ind_count = {}
        for r in head:
            ind = r.get("sw_industry") or r.get("industry") or "未知"
            ind_count[ind] = ind_count.get(ind, 0) + 1
        top_ind = sorted(ind_count.items(), key=lambda x: -x[1])[:5]

        dim_sum = {}
        for r in head:
            for dim, d in r["dimensions"].items():
                if d["score"] is not None:
                    dim_sum.setdefault(dim, []).append(d["score"])
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
        data_gaps += ["股息率/北向/龙虎榜/筹码获利盘/股东户数/融资融券/库存周期数据源缺失，对应维度已自动降权",
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
