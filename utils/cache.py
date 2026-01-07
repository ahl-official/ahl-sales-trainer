import os
from datetime import datetime, timedelta, timezone

CACHE = {}
CACHE_ENABLED = os.environ.get('DISABLE_CACHE', 'false').lower() != 'true'

def cache_get(key: str):
    """Get value from cache if not expired"""
    if not CACHE_ENABLED:
        return None
    entry = CACHE.get(key)
    if not entry:
        return None
    expires, value = entry
    if expires < datetime.now(timezone.utc):
        del CACHE[key]
        return None
    return value

def cache_set(key: str, value, ttl_seconds: int):
    """Set value in cache with TTL"""
    if not CACHE_ENABLED:
        return
    CACHE[key] = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds), value)
