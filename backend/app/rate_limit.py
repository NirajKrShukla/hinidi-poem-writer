"""Rate-limit configuration.

Production deployments should use a shared Redis-backed limiter so limits work across
multiple API replicas. The middleware below is intentionally small and can be replaced
by SlowAPI/API Gateway/WAF policies.
"""
import time
from collections import defaultdict
from threading import Lock


class SimpleRateLimiter:
    def __init__(self, limit=60, window_seconds=60):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(list)
        self._lock = Lock()

    def allow(self, key):
        now = time.time()
        with self._lock:
            values = [x for x in self._hits[key] if x > now - self.window]
            if len(values) >= self.limit:
                self._hits[key] = values
                return False
            values.append(now)
            self._hits[key] = values
            return True
