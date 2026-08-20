# -*- coding: utf-8 -*-
"""重建 08-18/08-19/08-20 三天标准批次种子数据（as_of 历史K线回放）。

- 用截至目标日的K线跑标准模式扫描 → 引擎自动写入回测库(trade_date=目标日, mode=normal)
- 重建后删除扫描历史记录，保持「历史对比」只含真实扫描
"""
import os
import sys

os.environ["NO_PROXY"] = "*"
sys.path.insert(0, r"C:\Users\89689\Desktop\dsh\xuanFP\pylibs")
sys.path.insert(0, r"C:\Users\89689\Desktop\dsh\xuanFP")

from backend import config as cfg
from backend.container import Container
from backend.domain.scanner.engine import ScanEngine

DAYS = ["2026-08-18", "2026-08-19", "2026-08-20"]


def progress(phase, done, total, msg):
    if done in (0, 1, total):
        print(f"  [{phase}] {done}/{total}")


def main():
    c = Container()
    weights = cfg.get_config()["scanner"]["weights"]
    for d in DAYS:
        sc = dict(cfg.get_config()["scanner"])
        sc["mode"] = "normal"
        sc["as_of"] = d
        engine = ScanEngine(c.em, c.tx, c.fund, c.cache_repo, c.scan_repo,
                            weights, sc, progress, c.top5_repo)
        r = engine.run()
        # 种子重建不是真实扫描，删除其历史记录（不污染历史对比）
        c.scan_repo.delete_run(r["run_id"])
        n = c.db.query_one(
            "SELECT COUNT(*) c FROM top5_records WHERE trade_date=? AND mode='normal'", (d,)
        )["c"]
        print(f"== {d} 重建完成 pool={r['pool_size']} 回测库标准批次={n} 条 ==")


if __name__ == "__main__":
    main()
