# -*- coding: utf-8 -*-
"""直接验证三阶段升级：57 因子 + 情绪因子 + 筹码因子 + 两层权重"""
import os
os.environ["NO_PROXY"] = "*"
os.environ["XUANFP_DB"] = r"C:\Users\89689\Desktop\dsh\xuanFP\data\xuanfp_v6.db"

import sys
sys.path.insert(0, r"C:\Users\89689\Desktop\dsh\xuanFP\pylibs")
sys.path.insert(0, r"C:\Users\89689\Desktop\dsh\xuanFP")

from backend import config as cfg
from backend.datasources import EastMoneyClient, TencentClient
from backend.datasources.fundamentals import FundamentalsClient
from backend.repositories import Database, CacheRepository, ScanRepository
from backend.domain.scanner.engine import ScanEngine


def progress(phase, done, total, msg):
    if done in (0, 1, total) or done % 100 == 0:
        print(f"  [{phase}] {done}/{total} - {msg}")


def main():
    db = Database(cfg.CACHE_DB)
    cache_repo = CacheRepository(db)
    scan_repo = ScanRepository(db)
    em = EastMoneyClient()
    tx = TencentClient()
    fund = FundamentalsClient()

    scanner_cfg = dict(cfg.get_config()["scanner"])
    scanner_cfg["universe_limit"] = 200  # 小池子快速验证
    weights = cfg.get_config()["scanner"]["weights"]

    engine = ScanEngine(em, tx, fund, cache_repo, scan_repo, weights, scanner_cfg, progress)
    result = engine.run()
    print("\n扫描结果:", {k: result[k] for k in ("universe_size", "pool_size", "duration")})

    results = scan_repo.get_results(result["run_id"])
    print("评分结果条数:", len(results))
    if not results:
        print("无结果！")
        return
    r = results[0]
    print("首名:", r["name"], r["ts_code"], "得分", r["score"])

    facs = r["factors"]
    print("\n因子总数:", len(facs))
    missing = [k for k, v in facs.items() if v.get("score") is None]
    print("缺失因子:", len(missing), missing if missing else "")

    print("\n情绪因子 g26:")
    g26 = facs.get("g26") or {}
    print("  ", g26.get("name"), "| 得分", g26.get("score"), "|", g26.get("note"))

    print("\n筹码因子:")
    for k in ("g20", "g21", "g22", "g23", "g24", "g25"):
        f = facs.get(k) or {}
        print(f"  {f.get('name')}: {f.get('score')} | {f.get('note')}")

    print("\n技术因子抽样:")
    for k in ("g1", "g2", "g6", "g11", "g15", "g16", "g17", "g18", "g19"):
        f = facs.get(k) or {}
        print(f"  {f.get('name')}: {f.get('score')} | {f.get('note')}")

    print("\n九维得分:")
    for dim, d in r["dimensions"].items():
        print(f"  {d['name']}: {d['score']} (可得 {d['available']}/{d['total']})")


if __name__ == "__main__":
    main()
