# -*- coding: utf-8 -*-
"""验证百分位校准后的得分分布"""
import os
os.environ["NO_PROXY"] = "*"
os.environ["XUANFP_DB"] = r"C:\Users\89689\Desktop\dsh\xuanFP\data\xuanfp_v7.db"
import sys
sys.path.insert(0, r"C:\Users\89689\Desktop\dsh\xuanFP\pylibs")
sys.path.insert(0, r"C:\Users\89689\Desktop\dsh\xuanFP")

from backend import config as cfg
from backend.datasources import EastMoneyClient, TencentClient
from backend.datasources.fundamentals import FundamentalsClient
from backend.repositories import Database, CacheRepository, ScanRepository
from backend.domain.scanner.engine import ScanEngine


def progress(phase, done, total, msg):
    if done in (0, 1, total):
        print(f"  [{phase}] {done}/{total}")


def main():
    db = Database(cfg.CACHE_DB)
    em = EastMoneyClient()
    tx = TencentClient()
    fund = FundamentalsClient()
    sc = dict(cfg.get_config()["scanner"])
    sc["universe_limit"] = 200
    engine = ScanEngine(em, tx, fund, CacheRepository(db), ScanRepository(db),
                        cfg.get_config()["scanner"]["weights"], sc, progress)
    r = engine.run()
    res = ScanRepository(db).get_results(r["run_id"])
    print("结果条数:", len(res), "| 前10得分:")
    for x in res[:10]:
        print(f"  {x['rank']} {x['name']} {x['score']}")
    # 得分分布
    scores = [x["score"] for x in res]
    if scores:
        print(f"得分区间: min={min(scores):.1f} max={max(scores):.1f}")
        for th in (85, 75, 65, 55):
            n = sum(1 for s in scores if s >= th)
            print(f"  >= {th}: {n} 只")
    # 查看首名维度（百分位）
    if res:
        d = res[0]["dimensions"]
        for dim, v in d.items():
            print(f"  {v['name']}: 百分位{v['score']} 原始{v['raw_score']}")


if __name__ == "__main__":
    main()
