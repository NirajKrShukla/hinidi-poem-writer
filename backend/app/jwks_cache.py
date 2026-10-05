import requests
from datetime import datetime, timedelta

JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_cache = {"jwks": None, "expires": None}

import threading
try:
    from prometheus_client import Counter
    _PROM_AVAILABLE = True
except Exception:
    _PROM_AVAILABLE = False

if _PROM_AVAILABLE:
    JWKS_HITS = Counter('jwks_hits_total', 'JWKS cache hits')
    JWKS_MISSES = Counter('jwks_misses_total', 'JWKS cache misses')
else:
    JWKS_HITS = JWKS_MISSES = None



def get_jwks():
    global _cache
    now = datetime.utcnow()
    if _cache["jwks"] and _cache["expires"] and now < _cache["expires"]:
        _metrics["hits"] += 1
        if _PROM_AVAILABLE:
            JWKS_HITS.inc()
        return _cache["jwks"]
    r = requests.get(JWKS_URL, timeout=5)
    r.raise_for_status()
    jwks = r.json()
    # Google's cache-control max-age is typically provided
    max_age = 3600
    try:
        cc = r.headers.get("Cache-Control", "")
        for part in cc.split(','):
            part = part.strip()
            if part.startswith('max-age='):
                max_age = int(part.split('=')[1])
    except Exception:
        pass
    _cache["jwks"] = jwks
    _cache["expires"] = now + timedelta(seconds=max_age)
    _metrics["misses"] += 1
    if _PROM_AVAILABLE:
        JWKS_MISSES.inc()
    return jwks


def refresh_jwks():
    # Force refresh
    global _cache
    _cache["jwks"] = None
    return get_jwks()


def _refresh_loop(interval_seconds: int = 3600):
    while True:
        try:
            refresh_jwks()
        except Exception:
            pass
        finally:
            threading.Event().wait(interval_seconds)


def start_refresh_loop(interval_seconds: int = 3600):
    t = threading.Thread(target=_refresh_loop, args=(interval_seconds,), daemon=True)
    t.start()
    return t


# Simple metrics
_metrics = {"hits": 0, "misses": 0}

def metrics():
    return dict(_metrics)
