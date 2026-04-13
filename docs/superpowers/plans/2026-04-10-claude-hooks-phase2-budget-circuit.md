# claude-hooks Phase 2: Budget Engine & Circuit Breaker — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent cost overruns and handle API outages gracefully. Per-hook budgets, global spending caps, and circuit breakers that degrade hooks to fallback when the API is failing.

**Architecture:** Budget engine uses a sliding window counter (calls + tokens per hour per hook, plus global cost caps on the router). Circuit breaker is per-hook with three states (closed/open/half-open). Both integrate into the router's Gate step — checked before every API call. If either gate fails, the hook falls back immediately without wasting an API call.

**Tech Stack:** Python 3.11+, time module for sliding windows, threading.Lock for thread safety, existing pytest infrastructure.

---

## File Structure

```
Changes from Phase 1:

src/claude_hooks/
  budget.py              # NEW — BudgetTracker: per-hook + global spending limits
  circuit.py             # NEW — CircuitBreaker: closed/open/half-open per hook
  router.py              # MODIFY — Wire budget + circuit into Gate step, add config params

tests/
  test_budget.py         # NEW
  test_circuit.py        # NEW
  test_router_phase2.py  # NEW — Tests for budget/circuit integration in router
```

---

## Task 1: Budget Engine

**Files:**
- Create: `src/claude_hooks/budget.py`
- Create: `tests/test_budget.py`

- [ ] **Step 1: Write test file `tests/test_budget.py`**

```python
import time
import pytest
from claude_hooks.budget import BudgetTracker


def test_budget_tracker_allows_under_limit():
    tracker = BudgetTracker(calls_per_hour=10, tokens_per_hour=1000)
    assert tracker.check("hook_a") is True


def test_budget_tracker_blocks_over_call_limit():
    tracker = BudgetTracker(calls_per_hour=3, tokens_per_hour=100000)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    assert tracker.check("hook_a") is False


def test_budget_tracker_blocks_over_token_limit():
    tracker = BudgetTracker(calls_per_hour=1000, tokens_per_hour=100)
    tracker.record("hook_a", input_tokens=60, output_tokens=50, cost_usd=0.01)
    assert tracker.check("hook_a") is False


def test_budget_tracker_independent_per_hook():
    tracker = BudgetTracker(calls_per_hour=2, tokens_per_hour=100000)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    assert tracker.check("hook_a") is False
    assert tracker.check("hook_b") is True  # different hook, still has budget


def test_budget_tracker_global_cost_limit():
    tracker = BudgetTracker(
        calls_per_hour=1000,
        tokens_per_hour=1000000,
        global_max_cost_per_hour=0.05,
    )
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.03)
    tracker.record("hook_b", input_tokens=100, output_tokens=50, cost_usd=0.03)
    # Total cost = $0.06, exceeds $0.05 global limit
    assert tracker.check("hook_a") is False
    assert tracker.check("hook_b") is False


def test_budget_tracker_no_limits_always_allows():
    tracker = BudgetTracker()
    for _ in range(100):
        tracker.record("hook_a", input_tokens=1000, output_tokens=500, cost_usd=1.0)
    assert tracker.check("hook_a") is True


def test_budget_tracker_remaining():
    tracker = BudgetTracker(calls_per_hour=10, tokens_per_hour=1000)
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.01)
    remaining = tracker.remaining("hook_a")
    assert remaining["calls"] == 9
    assert remaining["tokens"] == 850


def test_budget_tracker_reset():
    tracker = BudgetTracker(calls_per_hour=3, tokens_per_hour=1000)
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.01)
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.01)
    tracker.reset("hook_a")
    assert tracker.check("hook_a") is True
    remaining = tracker.remaining("hook_a")
    assert remaining["calls"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "C:/Users/reeld/OneDrive/Desktop/Claude Projects/ClaudeHooks" && source .venv/Scripts/activate && pytest tests/test_budget.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement `src/claude_hooks/budget.py`**

```python
"""Budget tracking for hook invocations."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _HookBudgetWindow:
    """Sliding window counters for a single hook."""
    calls: list[float] = field(default_factory=list)
    tokens: list[tuple[float, int]] = field(default_factory=list)  # (timestamp, token_count)


class BudgetTracker:
    """Tracks per-hook and global spending against configurable limits.

    Uses a 1-hour sliding window for all limits.
    """

    def __init__(
        self,
        *,
        calls_per_hour: int | None = None,
        tokens_per_hour: int | None = None,
        global_max_cost_per_hour: float | None = None,
    ):
        self._calls_per_hour = calls_per_hour
        self._tokens_per_hour = tokens_per_hour
        self._global_max_cost_per_hour = global_max_cost_per_hour
        self._windows: dict[str, _HookBudgetWindow] = {}
        self._global_costs: list[tuple[float, float]] = []  # (timestamp, cost_usd)
        self._lock = threading.Lock()

    def _get_window(self, hook_name: str) -> _HookBudgetWindow:
        if hook_name not in self._windows:
            self._windows[hook_name] = _HookBudgetWindow()
        return self._windows[hook_name]

    def _prune(self, cutoff: float, hook_name: str) -> None:
        """Remove entries older than cutoff from a hook's window."""
        window = self._get_window(hook_name)
        window.calls = [t for t in window.calls if t > cutoff]
        window.tokens = [(t, n) for t, n in window.tokens if t > cutoff]

    def _prune_global(self, cutoff: float) -> None:
        self._global_costs = [(t, c) for t, c in self._global_costs if t > cutoff]

    def record(self, hook_name: str, *, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        """Record a hook invocation against the budget."""
        now = time.monotonic()
        with self._lock:
            window = self._get_window(hook_name)
            window.calls.append(now)
            window.tokens.append((now, input_tokens + output_tokens))
            self._global_costs.append((now, cost_usd))

    def check(self, hook_name: str) -> bool:
        """Check if a hook is within budget. Returns True if allowed."""
        now = time.monotonic()
        cutoff = now - 3600  # 1 hour window

        with self._lock:
            # No limits = always allowed
            if (self._calls_per_hour is None
                    and self._tokens_per_hour is None
                    and self._global_max_cost_per_hour is None):
                return True

            self._prune(cutoff, hook_name)
            self._prune_global(cutoff)

            window = self._get_window(hook_name)

            # Check per-hook call limit
            if self._calls_per_hour is not None:
                if len(window.calls) >= self._calls_per_hour:
                    return False

            # Check per-hook token limit
            if self._tokens_per_hour is not None:
                total_tokens = sum(n for _, n in window.tokens)
                if total_tokens >= self._tokens_per_hour:
                    return False

            # Check global cost limit
            if self._global_max_cost_per_hour is not None:
                total_cost = sum(c for _, c in self._global_costs)
                if total_cost >= self._global_max_cost_per_hour:
                    return False

            return True

    def remaining(self, hook_name: str) -> dict[str, Any]:
        """Return remaining budget for a hook."""
        now = time.monotonic()
        cutoff = now - 3600

        with self._lock:
            self._prune(cutoff, hook_name)
            window = self._get_window(hook_name)

            calls_used = len(window.calls)
            tokens_used = sum(n for _, n in window.tokens)

            return {
                "calls": (self._calls_per_hour - calls_used) if self._calls_per_hour else None,
                "tokens": (self._tokens_per_hour - tokens_used) if self._tokens_per_hour else None,
            }

    def reset(self, hook_name: str) -> None:
        """Reset budget counters for a specific hook."""
        with self._lock:
            self._windows[hook_name] = _HookBudgetWindow()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_budget.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/claude_hooks/budget.py tests/test_budget.py
git commit -m "feat: add BudgetTracker with per-hook and global limits"
```

---

## Task 2: Circuit Breaker

**Files:**
- Create: `src/claude_hooks/circuit.py`
- Create: `tests/test_circuit.py`

- [ ] **Step 1: Write test file `tests/test_circuit.py`**

```python
import time
import pytest
from claude_hooks.circuit import CircuitBreaker, CircuitState


def test_initial_state_is_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.is_closed


def test_stays_closed_under_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED


def test_opens_at_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_open


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


def test_open_circuit_allows_check_returns_false():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.should_allow() is False


def test_closed_circuit_allows_check_returns_true():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    assert cb.should_allow() is True


def test_half_open_after_recovery_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.should_allow() is True  # transitions to half-open, allows one test
    assert cb.state == CircuitState.HALF_OPEN


def test_half_open_success_closes():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    cb.should_allow()  # transition to half-open
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    cb.should_allow()  # transition to half-open
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_reset():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


def test_stats():
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=5.0)
    cb.record_success()
    cb.record_success()
    cb.record_failure()
    stats = cb.stats()
    assert stats["state"] == "closed"
    assert stats["consecutive_failures"] == 1
    assert stats["total_successes"] == 2
    assert stats["total_failures"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_circuit.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement `src/claude_hooks/circuit.py`**

```python
"""Circuit breaker for LLM API resilience."""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal — requests flow through
    OPEN = "open"          # Tripped — all requests go to fallback
    HALF_OPEN = "half_open"  # Recovery — one test request allowed


class CircuitBreaker:
    """Per-hook circuit breaker with three states.

    CLOSED: Requests flow normally. Failures are counted.
    OPEN: After failure_threshold consecutive failures, all requests
          route to fallback immediately. No API calls.
    HALF_OPEN: After recovery_timeout seconds, one test request is sent.
               Success closes the circuit. Failure reopens it.
    """

    def __init__(self, *, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._total_successes = 0
        self._total_failures = 0
        self._last_failure_time: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def should_allow(self) -> bool:
        """Check if a request should be allowed through.

        Returns True if the circuit is closed or transitioning to half-open.
        Returns False if the circuit is open and recovery timeout hasn't elapsed.
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.HALF_OPEN:
                return False  # Only one test request in half-open

            # OPEN — check if recovery timeout has elapsed
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    return True

            return False

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self._consecutive_failures = 0
            self._total_successes += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed request."""
        with self._lock:
            self._consecutive_failures += 1
            self._total_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._consecutive_failures >= self._failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._last_failure_time = None

    def stats(self) -> dict[str, Any]:
        """Return circuit breaker stats."""
        return {
            "state": self._state.value,
            "consecutive_failures": self._consecutive_failures,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_circuit.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add src/claude_hooks/circuit.py tests/test_circuit.py
git commit -m "feat: add CircuitBreaker with closed/open/half-open states"
```

---

## Task 3: Wire Budget + Circuit into Router

**Files:**
- Modify: `src/claude_hooks/router.py`
- Create: `tests/test_router_phase2.py`

- [ ] **Step 1: Write test file `tests/test_router_phase2.py`**

```python
import pytest
from pydantic import BaseModel
from claude_hooks.router import HookRouter
from claude_hooks.exceptions import HookBudgetError


class Result(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_router_budget_blocks_over_limit(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "yes"}),
        make_response(content={"answer": "yes"}),
        make_response(content={"answer": "yes"}),
    ]
    router = HookRouter(
        provider=mock_provider,
        calls_per_hour=2,
    )

    @router.hook(model="sonnet", fallback="skip")
    async def decide(q: str) -> Result:
        """Answer the question."""
        ...

    await decide("q1")  # call 1 — OK
    await decide("q2")  # call 2 — OK
    result = await decide("q3")  # call 3 — over budget, falls back to skip
    assert result is None
    assert len(mock_provider._calls) == 2  # only 2 API calls made


@pytest.mark.asyncio
async def test_router_budget_raise_strategy(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "yes"}),
    ]
    router = HookRouter(
        provider=mock_provider,
        calls_per_hour=1,
    )

    @router.hook(model="sonnet", fallback="raise")
    async def decide(q: str) -> Result:
        """Answer the question."""
        ...

    await decide("q1")  # call 1 — OK
    with pytest.raises(HookBudgetError):
        await decide("q2")  # over budget + raise = HookBudgetError


@pytest.mark.asyncio
async def test_router_circuit_breaker_trips(mock_provider, make_response):
    # 3 consecutive failures should trip the circuit
    mock_provider._responses = [
        Exception("fail 1"),
        Exception("fail 2"),
        Exception("fail 3"),
        Exception("fail 4"),  # this should NOT reach the provider
    ]
    router = HookRouter(
        provider=mock_provider,
        circuit_failure_threshold=3,
    )

    @router.hook(model="sonnet", fallback="skip", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("q1")  # fail 1
    await decide("q2")  # fail 2
    await decide("q3")  # fail 3 — trips circuit
    await decide("q4")  # circuit open — goes straight to fallback

    # Only 3 API calls should have been made (4th was blocked by circuit)
    assert len(mock_provider._calls) == 3


@pytest.mark.asyncio
async def test_router_circuit_breaker_recovers(mock_provider, make_response):
    mock_provider._responses = [
        Exception("fail 1"),
        Exception("fail 2"),
        make_response(content={"answer": "recovered"}),
    ]
    router = HookRouter(
        provider=mock_provider,
        circuit_failure_threshold=2,
        circuit_recovery_timeout=0.1,
    )

    @router.hook(model="sonnet", fallback="skip", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("q1")  # fail 1
    await decide("q2")  # fail 2, trips circuit

    import asyncio
    await asyncio.sleep(0.15)  # wait for recovery timeout

    result = await decide("q3")  # half-open test — succeeds
    assert result is not None
    assert result.answer == "recovered"


@pytest.mark.asyncio
async def test_router_stats_include_budget_and_circuit(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "yes"}),
    ]
    router = HookRouter(
        provider=mock_provider,
        calls_per_hour=100,
        circuit_failure_threshold=5,
    )

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("q1")
    stats = router.stats()
    assert "budget" in stats
    assert "circuit_breakers" in stats
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_router_phase2.py -v`
Expected: FAIL — TypeError (router doesn't accept budget/circuit params yet)

- [ ] **Step 3: Modify `src/claude_hooks/router.py`**

Changes needed in HookRouter:

1. Add new `__init__` params: `calls_per_hour`, `tokens_per_hour`, `global_max_cost_per_hour`, `circuit_failure_threshold`, `circuit_recovery_timeout`
2. Create `BudgetTracker` and per-hook `CircuitBreaker` instances
3. In `_execute_hook`, add Gate step before API call:
   - Check budget: `if not self._budget.check(hook_name)` → fallback with HookBudgetError
   - Check circuit: `if not self._get_circuit(hook_name).should_allow()` → fallback
4. After successful API call: `circuit.record_success()`, `budget.record()`
5. After failed API call: `circuit.record_failure()`
6. Update `stats()` to include budget remaining and circuit state

The key changes to `__init__`:
```python
def __init__(
    self,
    *,
    provider: LLMProvider | None = None,
    api_key: str | None = None,
    calls_per_hour: int | None = None,
    tokens_per_hour: int | None = None,
    global_max_cost_per_hour: float | None = None,
    circuit_failure_threshold: int = 5,
    circuit_recovery_timeout: float = 30.0,
):
```

The key changes to `_execute_hook` (add before the retry loop):
```python
# Gate: Budget check
if not self._budget.check(config.name):
    error = HookBudgetError(
        f"Hook '{config.name}' is over budget",
        hook_name=config.name,
        limit=self._budget._calls_per_hour or 0,
        current=0,
    )
    ctx.record_fallback(config.fallback.value, reason=str(error))
    self._record_stats(ctx)
    return await resolve_fallback_async(
        strategy=config.fallback, error=error,
        original_func=original_func, args=args, kwargs=kwargs,
        default_response=config.default_response,
    )

# Gate: Circuit breaker check
circuit = self._get_circuit(config.name)
if not circuit.should_allow():
    error = HookProviderError(
        f"Circuit breaker open for hook '{config.name}'", provider=self._provider.name
    )
    ctx.record_fallback(config.fallback.value, reason=str(error))
    self._record_stats(ctx)
    return await resolve_fallback_async(
        strategy=config.fallback, error=error,
        original_func=original_func, args=args, kwargs=kwargs,
        default_response=config.default_response,
    )
```

After successful response (before return):
```python
circuit.record_success()
self._budget.record(
    config.name,
    input_tokens=response.input_tokens,
    output_tokens=response.output_tokens,
    cost_usd=response.cost_usd,
)
```

After all retries exhausted (before fallback):
```python
circuit.record_failure()
```

- [ ] **Step 4: Run Phase 2 tests**

Run: `pytest tests/test_router_phase2.py -v`
Expected: 5 passed

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass (57 existing + 8 budget + 11 circuit + 5 router_phase2 = 81)

- [ ] **Step 6: Commit**

```bash
git add src/claude_hooks/router.py tests/test_router_phase2.py
git commit -m "feat: wire budget engine and circuit breaker into router lifecycle"
```

- [ ] **Step 7: Tag**

```bash
git tag v0.2.0-alpha
```
