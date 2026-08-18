# -*- coding: utf-8 -*-
"""通用 HTTP 工具：带重试的请求、代理环境规避"""
import os
import time

import requests

os.environ.setdefault("NO_PROXY", "*")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "*/*",
})

# 禁用证书校验告警
import urllib3  # noqa: E402
urllib3.disable_warnings()


def http_get(url, params=None, headers=None, timeout=30, verify=True, retries=2, backoff=1.0):
    """带重试的 GET，返回 requests.Response；非 200 抛出含 URL 的明确错误"""
    last = None
    for attempt in range(retries + 1):
        try:
            resp = _SESSION.get(url, params=params, headers=headers, timeout=timeout, verify=verify)
            if resp.status_code == 200:
                return resp
            last = RuntimeError(f"HTTP {resp.status_code} @ {url}: {resp.text[:150]!r}")
            # 403/429/501 等拦截类错误不重试同一主机，交给上层回退其他主机
            if resp.status_code in (403, 429, 501, 502, 503):
                break
        except requests.RequestException as e:
            last = e
        time.sleep(backoff * (attempt + 1))
    raise last


def http_get_json(url, params=None, headers=None, timeout=30, verify=True, retries=2, backoff=1.0):
    resp = http_get(url, params=params, headers=headers, timeout=timeout, verify=verify,
                    retries=retries, backoff=backoff)
    return resp.json()


def http_get_fallback(urls, params=None, headers=None, timeout=30, verify=True, retries=1):
    """依次尝试多个 URL（多主机容灾），全部失败抛出最后一个错误"""
    last = None
    for u in urls:
        try:
            return http_get(u, params=params, headers=headers, timeout=timeout,
                            verify=verify, retries=retries)
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def http_get_json_fallback(urls, params=None, headers=None, timeout=30, verify=True, retries=1):
    resp = http_get_fallback(urls, params=params, headers=headers, timeout=timeout,
                             verify=verify, retries=retries)
    return resp.json()
