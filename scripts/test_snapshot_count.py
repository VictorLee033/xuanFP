# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NO_PROXY", "*")
from backend.datasources import EastMoneyClient

em = EastMoneyClient()
t0 = time.time()
snaps = em.market_snapshot()
print(f"快照数量: {len(snaps)}, 耗时 {time.time()-t0:.1f}s")
# 检查分页
j = em.clist_page(pn=1, pz=200)
print("clist p1 total:", (j.get("data") or {}).get("total"), "diff:", len((j.get("data") or {}).get("diff") or []))
j2 = em.clist_page(pn=28, pz=200)
print("clist p28 diff:", len((j2.get("data") or {}).get("diff") or []))
