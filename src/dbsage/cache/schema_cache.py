"""TTL-based in-memory cache for schema metadata.

Schema data (table lists, column definitions, FK relationships) rarely changes.
Caching it reduces information_schema queries and improves tool response time.

The cache is a plain dict keyed by (operation, args). Entries expire after
DBSAGE_CACHE_TTL_SECONDS (default 300s = 5 minutes).
"""

import time
from typing import Any

# module-level cache: key -> (value, expires_at_monotonic)
_cache: dict[str, tuple[Any, float]] = {}


def cache_get(key: str) -> Any | None:
    """Return a cached value if it exists and hasn't expired, else None."""
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() < expires_at:
        return value
    del _cache[key]
    return None


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    """Store a value in the cache with a TTL."""
    _cache[key] = (value, time.monotonic() + ttl_seconds)


def cache_invalidate(prefix: str = "") -> None:
    """Remove all cache entries whose key starts with prefix.

    Call with no argument to flush the entire cache.
    """
    if not prefix:
        _cache.clear()
        return
    for key in list(_cache.keys()):
        if key.startswith(prefix):
            del _cache[key]
