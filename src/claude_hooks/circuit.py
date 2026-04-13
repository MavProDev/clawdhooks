"""Circuit breaker for LLM API resilience."""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-hook circuit breaker with three states.

    CLOSED: Requests flow normally. Failures counted.
    OPEN: After failure_threshold consecutive failures, all requests
          route to fallback immediately.
    HALF_OPEN: After recovery_timeout, one test request allowed.
               Success → closed. Failure → open again.
    """

    def __init__(self, *, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        if failure_threshold < 1:
            raise ValueError(f"failure_threshold must be >= 1, got {failure_threshold}")
        if recovery_timeout <= 0:
            raise ValueError(f"recovery_timeout must be > 0, got {recovery_timeout}")
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
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.HALF_OPEN:
                return False
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._total_successes += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            self._total_failures += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._consecutive_failures >= self._failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._last_failure_time = None

    def stats(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "consecutive_failures": self._consecutive_failures,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
        }
