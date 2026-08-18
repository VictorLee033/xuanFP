# -*- coding: utf-8 -*-
"""下载前端第三方库全局构建（免 npm 构建）到 frontend/static/vendor/"""
import os
os.environ.setdefault("NO_PROXY", "*")
import requests
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "frontend" / "static" / "vendor"
STATIC.mkdir(parents=True, exist_ok=True)

# 文件名 -> 候选 URL 列表（按优先级）
FILES = {
    "vue.global.prod.js": [
        "https://cdn.jsdelivr.net/npm/vue@3.5.13/dist/vue.global.prod.js",
        "https://unpkg.com/vue@3.5.13/dist/vue.global.prod.js",
        "https://registry.npmmirror.com/vue/3.5.13/files/dist/vue.global.prod.js",
    ],
    "element-plus.full.min.js": [
        "https://cdn.jsdelivr.net/npm/element-plus@2.8.8/dist/index.full.min.js",
        "https://unpkg.com/element-plus@2.8.8/dist/index.full.min.js",
        "https://registry.npmmirror.com/element-plus/2.8.8/files/dist/index.full.min.js",
    ],
    "element-plus.css": [
        "https://cdn.jsdelivr.net/npm/element-plus@2.8.8/dist/index.css",
        "https://unpkg.com/element-plus@2.8.8/dist/index.css",
    ],
    "element-plus.dark.css": [
        "https://cdn.jsdelivr.net/npm/element-plus@2.8.8/theme-chalk/dark/css-vars.css",
        "https://unpkg.com/element-plus@2.8.8/theme-chalk/dark/css-vars.css",
    ],
    "echarts.min.js": [
        "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js",
        "https://unpkg.com/echarts@5.5.1/dist/echarts.min.js",
        "https://registry.npmmirror.com/echarts/5.5.1/files/dist/echarts.min.js",
    ],
}

for fname, urls in FILES.items():
    dest = STATIC / fname
    if dest.exists() and dest.stat().st_size > 10000:
        print(f"[ok ] {fname} (已存在 {dest.stat().st_size} bytes)")
        continue
    ok = False
    for u in urls:
        try:
            r = requests.get(u, timeout=120)
            if r.status_code == 200 and len(r.content) > 10000:
                dest.write_bytes(r.content)
                print(f"[ok ] {fname} <- {u.split('/')[2]} ({len(r.content)} bytes)")
                ok = True
                break
            print(f"  {u.split('/')[2]}: status={r.status_code} len={len(r.content)}")
        except Exception as e:
            print(f"  {u.split('/')[2]}: 异常 {type(e).__name__} {str(e)[:60]}")
    if not ok:
        print(f"[MISS] {fname} 所有源失败！")
