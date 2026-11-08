"""共用的 HTTPS GET。各业务文件从这里取正文，不再互相下载。"""

import json
import time
import threading
from collections import OrderedDict
import ssl
import urllib.request
from pathlib import Path


_CACHE = OrderedDict()
_LOCK = threading.RLock()


def fetch_text(url: str, timeout: int = 20, user_agent: str = "Mozilla/5.0") -> str:
    with _LOCK:
        cached = _CACHE.get(url)
        if cached and cached[0] > time.monotonic():
            return cached[1]
    request = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent},
    )
    # python.org 安装的 Python 默认不带证书。macOS 系统证书在这个路径。
    cafile = Path("/etc/ssl/cert.pem")
    context = (
        ssl.create_default_context(cafile=cafile)
        if cafile.exists()
        else ssl.create_default_context()
    )
    with urllib.request.urlopen(
        request, timeout=min(timeout, 10), context=context
    ) as response:
        raw = response.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ValueError("Response too large")
        value = raw.decode("utf-8")
    with _LOCK:
        if len(_CACHE) >= 64:
            _CACHE.popitem(last=False)
        _CACHE[url] = (time.monotonic() + 60, value)
    return value


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url))
