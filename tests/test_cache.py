import time
import pytest
from claudehooks.cache import HookCache


def test_cache_miss_returns_none():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    assert cache.get("some input") is None


def test_cache_hit_returns_value():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("hello world", {"action": "allow"})
    assert cache.get("hello world") == {"action": "allow"}


def test_cache_normalized_key():
    # Keys are normalized by stripping leading/trailing whitespace only.
    # Case is preserved (full SHA-256, no .lower()).
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("  Hello World  ", {"action": "allow"})
    # Same content after strip → cache hit
    assert cache.get("  Hello World  ") == {"action": "allow"}
    assert cache.get("Hello World") == {"action": "allow"}
    # Different case → cache miss (case-sensitive)
    assert cache.get("hello world") is None
    assert cache.get("  HELLO WORLD  ") is None


def test_cache_ttl_expiry():
    cache = HookCache(max_size=10, ttl_seconds=0.1)
    cache.put("hello", {"action": "allow"})
    assert cache.get("hello") == {"action": "allow"}
    time.sleep(0.15)
    assert cache.get("hello") is None


def test_cache_lru_eviction():
    cache = HookCache(max_size=3, ttl_seconds=60.0)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    cache.put("c", {"v": 3})
    cache.put("d", {"v": 4})
    assert cache.get("a") is None
    assert cache.get("b") == {"v": 2}
    assert cache.get("d") == {"v": 4}


def test_cache_get_latest():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("first", {"v": 1})
    cache.put("second", {"v": 2})
    assert cache.get_latest() == {"v": 2}


def test_cache_get_latest_empty():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    assert cache.get_latest() is None


def test_cache_get_latest_expired():
    cache = HookCache(max_size=10, ttl_seconds=0.1)
    cache.put("old", {"v": 1})
    time.sleep(0.15)
    assert cache.get_latest() is None


def test_cache_clear():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("a", {"v": 1})
    cache.put("b", {"v": 2})
    assert cache.size == 2
    cache.clear()
    assert cache.size == 0
    assert cache.get("a") is None


def test_cache_overwrite():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("key", {"v": 1})
    cache.put("key", {"v": 2})
    assert cache.get("key") == {"v": 2}
    assert cache.size == 1
