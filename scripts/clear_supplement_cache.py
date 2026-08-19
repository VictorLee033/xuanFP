# -*- coding: utf-8 -*-
"""清除修复前缓存的补充数据（em:div / em:nb / em:holder / em:margin / em:toplist）"""
import sqlite3

p = r"C:\Users\89689\Desktop\dsh\xuanFP\data\xuanfp_v3.db"
conn = sqlite3.connect(p)
for prefix in ["em:div:", "em:nb:", "em:holder:", "em:margin:", "em:toplist:"]:
    n = conn.execute("DELETE FROM data_cache WHERE key LIKE ?", (prefix + "%",)).rowcount
    conn.commit()
    print(f"已清除 {prefix} 缓存 {n} 条")
conn.close()
