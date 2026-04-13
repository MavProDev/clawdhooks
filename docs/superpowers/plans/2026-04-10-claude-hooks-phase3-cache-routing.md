# claude-hooks Phase 3: Caching & Model Cascade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce costs through response caching and add model cascade fallback (degrade to cheaper models on failure).

**Architecture:** Per-hook LRU cache with TTL, keyed by normalized input hash. Cache checked before API call (saves money). Two new fallback strategies: `cache` (return last cached response on failure) and `cascade` (try cheaper models before giving up). Cascade order is fixed: opus → sonnet → haiku.

**Tech Stack:** Python 3.11+ stdlib (hashlib, OrderedDict, threading), existing test infrastructure.

---

## Task 1: Cache Module

**Files:**
- Create: `src/claude_hooks/cache.py`
- Create: `tests/test_cache.py`

### Tests:

```python
# tests/test_cache.py
import time
import pytest
from claude_hooks.cache import HookCache


def test_cache_miss_returns_none():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    assert cache.get("some input") is None


def test_cache_hit_returns_value():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("hello world", {"action": "allow"})
    assert cache.get("hello world") == {"action": "allow"}


def test_cache_normalized_key():
    cache = HookCache(max_size=10, ttl_seconds=60.0)
    cache.put("  Hello World  ", {"action": "allow"})
    assert cache.get("hello world") == {"action": "allow"}
    assert cache.get("  HELLO WORLD  ") == {"action": "allow"}


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
    cache.put("d", {"v": 4})  # evicts "a"
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
```

### Implementation:

```python
# src/claude_hooks/cache.py
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
```

### Commit: `"feat: add HookCache with LRU eviction and TTL"`

---

## Task 2: Add CACHE and CASCADE Fallback Strategies

**Files:**
- Modify: `src/claude_hooks/types.py` — add CACHE and CASCADE to FallbackStrategy
- Modify: `tests/test_types.py` — add assertions for new values

### Changes to types.py:

Add to FallbackStrategy enum:
```python
CACHE = "cache"      # Return last cached response for this hook
CASCADE = "cascade"  # Try cheaper models before giving up
```

### Changes to test_types.py:

Add to `test_fallback_strategy_values`:
```python
assert FallbackStrategy.CACHE.value == "cache"
assert FallbackStrategy.CASCADE.value == "cascade"
```

### Commit: `"feat: add cache and cascade fallback strategies"`

---

## Task 3: Wire Cache + Cascade into Router

**Files:**
- Modify: `src/claude_hooks/router.py`
- Create: `tests/test_router_phase3.py`

### Router changes:

**1. New __init__ params:**
```python
# Cache params
cache_enabled: bool = False,
cache_max_size: int = 128,
cache_ttl_seconds: float = 300.0,
```

**2. Create per-hook caches:**
```python
self._cache_enabled = cache_enabled
self._cache_max_size = cache_max_size
self._cache_ttl_seconds = cache_ttl_seconds
self._caches: dict[str, HookCache] = {}
```

**3. Add cache helper:**
```python
def _get_cache(self, hook_name: str) -> HookCache:
    if hook_name not in self._caches:
        self._caches[hook_name] = HookCache(
            max_size=self._cache_max_size,
            ttl_seconds=self._cache_ttl_seconds,
        )
    return self._caches[hook_name]
```

**4. In _execute_hook, BEFORE budget/circuit gates — check cache:**
```python
if self._cache_enabled:
    cache = self._get_cache(config.name)
    cached = cache.get(user_message)
    if cached is not None:
        result = output_model.model_validate(cached)
        ctx.record_fallback("cache", reason="cache hit")
        self._record_stats(ctx)
        return result
```

**5. After successful API response — store in cache:**
```python
if self._cache_enabled:
    self._get_cache(config.name).put(user_message, response.content)
```

**6. Handle CACHE fallback (after retries exhausted, before resolve_fallback_async):**
```python
if config.fallback == FallbackStrategy.CACHE:
    cache = self._get_cache(config.name)
    cached = cache.get_latest()
    if cached is not None:
        result = output_model.model_validate(cached)
        ctx.record_fallback("cache", reason=f"cache fallback: {last_error}")
        self._record_stats(ctx)
        return result
    # No cache available — fall through to None (like skip)
    ctx.record_fallback("cache", reason=f"no cache: {last_error}")
    self._record_stats(ctx)
    return None
```

**7. Handle CASCADE fallback:**
```python
CASCADE_ORDER = ["opus", "sonnet", "haiku"]

if config.fallback == FallbackStrategy.CASCADE:
    cascade_result = await self._try_cascade(
        config, output_model, output_schema, user_message, ctx
    )
    if cascade_result is not None:
        return cascade_result
    ctx.record_fallback("cascade", reason=f"all models failed: {last_error}")
    self._record_stats(ctx)
    return None
```

**8. Add _try_cascade method:**
```python
async def _try_cascade(self, config, output_model, output_schema, user_message, ctx):
    current = config.model or "sonnet"
    cascade_order = ["opus", "sonnet", "haiku"]
    try:
        idx = cascade_order.index(current)
    except ValueError:
        return None
    for fallback_model in cascade_order[idx + 1:]:
        try:
            timeout = self._provider.model_timeout(fallback_model)
            response = await asyncio.wait_for(
                self._provider.complete(
                    system_prompt=config.system_prompt,
                    user_message=user_message,
                    output_schema=output_schema,
                    model=fallback_model,
                    timeout_seconds=timeout,
                ),
                timeout=timeout,
            )
            result = output_model.model_validate(response.content)
            ctx.record_response(response)
            circuit = self._get_circuit(config.name)
            circuit.record_success()
            self._budget.record(
                config.name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
            )
            self._record_stats(ctx)
            return result
        except Exception:
            continue
    return None
```

### Tests `tests/test_router_phase3.py`:

```python
import pytest
from pydantic import BaseModel
from claude_hooks.router import HookRouter


class Result(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_cache_hit_skips_api_call(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "first"}),
    ]
    router = HookRouter(provider=mock_provider, cache_enabled=True)

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    r1 = await decide("what is 2+2")
    r2 = await decide("what is 2+2")  # same input — should hit cache

    assert r1.answer == "first"
    assert r2.answer == "first"
    assert len(mock_provider._calls) == 1  # only one API call


@pytest.mark.asyncio
async def test_cache_miss_calls_api(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "a"}),
        make_response(content={"answer": "b"}),
    ]
    router = HookRouter(provider=mock_provider, cache_enabled=True)

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("question 1")
    await decide("question 2")  # different input — cache miss
    assert len(mock_provider._calls) == 2


@pytest.mark.asyncio
async def test_cache_fallback_returns_cached(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "cached"}),
        Exception("API down"),
    ]
    router = HookRouter(provider=mock_provider, cache_enabled=True)

    @router.hook(model="sonnet", fallback="cache", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("q1")  # succeeds, cached
    result = await decide("q2")  # fails, falls back to cache
    assert result is not None
    assert result.answer == "cached"


@pytest.mark.asyncio
async def test_cache_fallback_none_when_empty(mock_provider):
    mock_provider._responses = [Exception("API down")]
    router = HookRouter(provider=mock_provider, cache_enabled=True)

    @router.hook(model="sonnet", fallback="cache", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    result = await decide("q1")  # fails, no cache available
    assert result is None


@pytest.mark.asyncio
async def test_cascade_tries_cheaper_model(mock_provider, make_response):
    mock_provider._responses = [
        Exception("opus failed"),
        make_response(content={"answer": "sonnet saved it"}),
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="opus", fallback="cascade", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    result = await decide("hard question")
    assert result is not None
    assert result.answer == "sonnet saved it"
    assert len(mock_provider._calls) == 2  # opus + sonnet


@pytest.mark.asyncio
async def test_cascade_all_fail_returns_none(mock_provider):
    mock_provider._responses = [
        Exception("opus failed"),
        Exception("sonnet failed"),
        Exception("haiku failed"),
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="opus", fallback="cascade", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    result = await decide("impossible question")
    assert result is None


@pytest.mark.asyncio
async def test_cache_disabled_by_default(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "a"}),
        make_response(content={"answer": "b"}),
    ]
    router = HookRouter(provider=mock_provider)  # cache_enabled=False default

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("same")
    await decide("same")  # no cache — calls API again
    assert len(mock_provider._calls) == 2
```

### Commit: `"feat: wire caching and cascade fallback into router"`
### Tag: `v0.3.0-alpha`
