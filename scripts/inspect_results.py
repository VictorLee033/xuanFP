# -*- coding: utf-8 -*-
import sqlite3, json
c = sqlite3.connect(r'C:\Users\89689\Desktop\dsh\xuanFP\data\xuanfp.db')
c.row_factory = sqlite3.Row
print('scan_results count:', c.execute('SELECT COUNT(*) FROM scan_results').fetchone()[0])
for r in c.execute('SELECT run_id,rank,ts_code,name,score,industry FROM scan_results ORDER BY run_id DESC, rank LIMIT 10'):
    print(dict(r))
print('--- run 3 top20/summary ---')
r = c.execute('SELECT top20, summary FROM scan_runs WHERE id=3').fetchone()
print('top20:', (r['top20'] or '')[:300])
print('summary:', (r['summary'] or '')[:500])
