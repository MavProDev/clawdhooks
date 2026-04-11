"""Per-hook LRU cache with TTL."""
from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any


class HookCache:
    """LRU cache with TTL for hook responses.

    Keys are normalized hashes of input data.
    Values are cached response dicts.
    """

    def __init__(self, *, max_size: int = 128, ttl_seconds: float = 300.0):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def _make_key(self, input_data: str) -> str:
        normalized = input_data.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def get(self, input_data: str) -> Any | None:
        key = self._make_key(input_data)
        with self._lock:
            if key not in self._cache:
                return None
            timestamp, value = self._cache[key]
            if time.monotonic() - timestamp > self._ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def put(self, input_data: str, value: Any) -> None:
        key = self._make_key(input_data)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            self._cache[key] = (time.monotonic(), value)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def get_latest(self) -> Any | None:
        with self._lock:
            if not self._cache:
                return None
            key = next(reversed(self._cache))
            timestamp, value = self._cache[key]
            if time.monotonic() - timestamp > self._ttl:
                return None
            return value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
