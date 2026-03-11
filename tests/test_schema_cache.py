"""Tests for the TTL schema cache."""

import time

from dbsage.cache.schema_cache import cache_get, cache_invalidate, cache_set


def test_cache_miss_returns_none() -> None:
    assert cache_get("nonexistent_key_xyz") is None


def test_cache_set_and_get() -> None:
    cache_set("test:tables", ["users", "orders"], ttl_seconds=60)
    result = cache_get("test:tables")
    assert result == ["users", "orders"]


def test_cache_returns_none_after_expiry() -> None:
    cache_set("test:expiring", "value", ttl_seconds=0)
    # TTL=0 means expires_at = now + 0, already expired
    time.sleep(0.01)
    assert cache_get("test:expiring") is None


def test_cache_invalidate_specific_prefix() -> None:
    cache_set("describe:users", [{"col": "id"}], ttl_seconds=60)
    cache_set("describe:orders", [{"col": "id"}], ttl_seconds=60)
    cache_set("list_tables", ["users", "orders"], ttl_seconds=60)

    cache_invalidate("describe:")

    assert cache_get("describe:users") is None
    assert cache_get("describe:orders") is None
    assert cache_get("list_tables") is not None  # unaffected


def test_cache_invalidate_all() -> None:
    cache_set("a", 1, ttl_seconds=60)
    cache_set("b", 2, ttl_seconds=60)
    cache_invalidate()
    assert cache_get("a") is None
    assert cache_get("b") is None


def test_cache_overwrites_existing_key() -> None:
    cache_set("test:overwrite", "old", ttl_seconds=60)
    cache_set("test:overwrite", "new", ttl_seconds=60)
    assert cache_get("test:overwrite") == "new"


def test_cache_stores_dict_values() -> None:
    data = [{"column_name": "id", "data_type": "int"}]
    cache_set("describe:products", data, ttl_seconds=60)
    assert cache_get("describe:products") == data
