# -*- coding: utf-8 -*-
import sqlite3
c = sqlite3.connect(r'C:\Users\89689\Desktop\dsh\xuanFP\data\xuanfp.db')
c.row_factory = sqlite3.Row
for r in c.execute('SELECT id,status,universe_size,passed_size,error,stats FROM scan_runs ORDER BY id DESC LIMIT 2'):
    print(dict(r))
print('cache entries:', c.execute('SELECT COUNT(*) FROM data_cache').fetchone()[0])
print('fina cache sample:')
for r in c.execute("SELECT key FROM data_cache WHERE key LIKE 'ts:fina_indicator%' LIMIT 3"):
    print(' ', r[0])
print('daily_basic cache:')
for r in c.execute("SELECT key FROM data_cache WHERE key LIKE 'ts:daily_basic%' LIMIT 3"):
    print(' ', r[0])
