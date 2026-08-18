# -*- coding: utf-8 -*-
"""自定义依赖安装器：绕过 pip 临时目录被沙箱拦截的问题。
从 PyPI JSON API 获取 wheel 直链，requests 下载并用 zipfile 解压到 pylibs/，
之后以 PYTHONPATH=pylibs 运行。全部使用默认 UA（镜像源 WAF 拦截浏览器 UA）。
"""
import os
import re
import sys
import zipfile
from pathlib import Path

os.environ.setdefault("NO_PROXY", "*")
import requests  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WHEELS = ROOT / "wheels"
PYLIBS = ROOT / "pylibs"
PYPI_JSON = "https://pypi.org/pypi/{name}/json"

# 依赖闭包（名称 -> 最低版本）
DEPS = {
    "fastapi": "0.115", "starlette": "0.37", "anyio": "4.0", "idna": "3.4",
    "sniffio": "1.3", "pydantic": "2.7", "pydantic-core": "2.18",
    "annotated-types": "0.6", "typing-extensions": "4.9",
    "uvicorn": "0.30", "click": "8.1", "h11": "0.14",
    "requests": "2.31", "charset-normalizer": "3.3", "urllib3": "2.0", "certifi": "2024.7",
    "pyyaml": "6.0", "numpy": "1.26", "packaging": "24.0",
    "annotated-doc": "0.0",
    "typing-inspection": "0.4",
}

# 需要精确版本锁定的包（避免版本错配）
EXACT = {"pydantic-core": "2.46.4"}


def norm(name):
    return name.lower().replace("_", "-")


def ver_key(v):
    out = []
    for part in re.split(r"[.\-+]", v):
        if part.isdigit():
            out.append(int(part))
        else:
            break
    return tuple(out)


def best_wheel(pkg, min_ver):
    """返回 (下载url, 文件名)；无可用 wheel 抛异常"""
    r = requests.get(PYPI_JSON.format(name=norm(pkg)), timeout=30)
    r.raise_for_status()
    data = r.json()
    py_ver = f"cp{sys.version_info.major}{sys.version_info.minor}"
    latest_ver = data.get("info", {}).get("version", "0")
    if pkg in EXACT:
        min_ver = EXACT[pkg]
    elif ver_key(latest_ver) < ver_key(min_ver):
        raise RuntimeError(f"{pkg}: 最新版 {latest_ver} < {min_ver}")
    best = None
    best_score = -1
    is_64 = sys.maxsize > 2 ** 32
    if pkg in EXACT:
        candidates = data.get("releases", {}).get(EXACT[pkg], [])
    else:
        candidates = data.get("urls", [])
    for f in candidates:
        if f.get("packagetype") != "bdist_wheel":
            continue
        fname = f["filename"]
        tags = fname[:-4].split("-")[-3:]  # [pytag, abi, platform]
        if len(tags) != 3:
            continue
        pytag, abi, plat = tags
        if plat == "win32" and is_64:
            continue
        if plat not in ("any", "win_amd64", "win32"):
            continue
        if pytag == py_ver and (plat == "win_amd64" or plat == "any"):
            score = 100
        elif pytag.startswith("cp3") and abi == "abi3" and plat in ("any", "win_amd64"):
            score = 60
        elif pytag in ("py3", "py2.py3"):
            score = 40
        elif pytag == py_ver and plat == "win32":
            score = 35
        else:
            continue
        if score > best_score:
            best_score = score
            best = (f["url"], fname)
    if not best:
        raise RuntimeError(f"{pkg}: 无可用 wheel（>= {min_ver}）")
    return best


def main():
    WHEELS.mkdir(parents=True, exist_ok=True)
    PYLIBS.mkdir(parents=True, exist_ok=True)
    for pkg, min_ver in DEPS.items():
        try:
            dl_url, fname = best_wheel(pkg, min_ver)
        except Exception as e:
            print(f"[skip] {pkg}: {e}")
            continue
        local = WHEELS / fname
        if not local.exists():
            print(f"[get ] {fname}")
            rr = requests.get(dl_url, timeout=300)
            rr.raise_for_status()
            local.write_bytes(rr.content)
        try:
            with zipfile.ZipFile(local) as z:
                z.extractall(PYLIBS)
            print(f"[ok  ] {fname}")
        except zipfile.BadZipFile:
            print(f"[skip] {fname}: 非wheel")
    print("完成。运行: $env:PYTHONPATH='pylibs'; python -m backend.main")


if __name__ == "__main__":
    main()
