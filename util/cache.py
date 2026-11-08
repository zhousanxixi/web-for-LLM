"""Small TTL cache with per-key request coalescing; failed locations expire quickly."""

from collections import OrderedDict
from copy import deepcopy
from functools import wraps
import threading
import time


def ttl_cache(ttl=1800, miss_ttl=30, maxsize=256):
    def decorate(function):
        cache = OrderedDict()
        lock = threading.RLock()

        @wraps(function)
        def wrapped(*args):
            # Geocoding is serialised deliberately to respect public-service limits.
            with lock:
                now = time.monotonic()
                cached = cache.get(args)
                if cached and cached[0] > now:
                    cache.move_to_end(args)
                    return deepcopy(cached[1])
                value = function(*args)
                cache[args] = (
                    time.monotonic() + (ttl if value is not None else miss_ttl),
                    deepcopy(value),
                )
                if len(cache) > maxsize:
                    cache.popitem(last=False)
                return value

        return wrapped

    return decorate
