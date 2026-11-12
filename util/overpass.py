"""Bounded Overpass requests, successful-result cache and in-process coalescing."""

import copy
import hashlib
import json
import os
import ssl
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import HTTPError

OVERPASS_URLS = (
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
_LOCK = threading.Lock()
_CACHE = {}
_KEY_LOCKS = {}
_COOLDOWN = {}


def post_overpass(query):
    key = hashlib.sha256(query.encode()).hexdigest()
    with _LOCK:
        now = time.monotonic()
        if key in _CACHE and _CACHE[key][0] > now:
            return copy.deepcopy(_CACHE[key][1])
        lock = _KEY_LOCKS.setdefault(key, threading.Lock())
    with lock:
        with _LOCK:
            if key in _CACHE and _CACHE[key][0] > time.monotonic():
                return copy.deepcopy(_CACHE[key][1])
        deadline = time.monotonic() + float(os.getenv("OVERPASS_TOTAL_TIMEOUT", "12"))
        cafile = Path("/etc/ssl/cert.pem")
        context = ssl.create_default_context(
            cafile=str(cafile) if cafile.exists() else None
        )
        last = None
        for url in OVERPASS_URLS:
            remaining = deadline - time.monotonic()
            if remaining < 1:
                break
            if _COOLDOWN.get(url, 0) > time.monotonic():
                continue
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode({"data": query}).encode(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "HongKongTravelProject/2.0",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    req, timeout=min(6, remaining), context=context
                ) as response:
                    raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise ValueError("Response too large")
                data = json.loads(raw)
                elements = data.get("elements")
                if not isinstance(elements, list) or data.get("remark"):
                    raise ValueError("Incomplete Overpass response")
                with _LOCK:
                    if len(_CACHE) >= 64:
                        _CACHE.pop(next(iter(_CACHE)))
                    _CACHE[key] = (time.monotonic() + 600, data)
                return copy.deepcopy(
                    data
                )  # An empty successful response is valid, not a reason to query every mirror.
            except HTTPError as exc:
                last = exc
                if exc.code in (403, 429):
                    _COOLDOWN[url] = time.monotonic() + 60
                    raise RuntimeError(
                        "OpenStreetMap service is rate-limited. Please retry later."
                    ) from None
                if exc.code not in (502, 503, 504):
                    break
            except (OSError, TimeoutError, ValueError) as exc:
                last = exc
        raise RuntimeError(
            "OpenStreetMap query timed out or was unavailable. Please retry later."
        ) from last
