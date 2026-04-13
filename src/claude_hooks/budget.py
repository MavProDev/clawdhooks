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
    tokens: list[tuple[float, int]] = field(default_factory=list)


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
        if calls_per_hour is not None and calls_per_hour <= 0:
            raise ValueError(f"calls_per_hour must be positive, got {calls_per_hour}")
        if tokens_per_hour is not None and tokens_per_hour <= 0:
            raise ValueError(f"tokens_per_hour must be positive, got {tokens_per_hour}")
        if global_max_cost_per_hour is not None and global_max_cost_per_hour <= 0:
            raise ValueError(f"global_max_cost_per_hour must be positive, got {global_max_cost_per_hour}")
        self._calls_per_hour = calls_per_hour
        self._tokens_per_hour = tokens_per_hour
        self._global_max_cost_per_hour = global_max_cost_per_hour
        self._windows: dict[str, _HookBudgetWindow] = {}
        self._global_costs: list[tuple[float, float]] = []
        self._lock = threading.Lock()

    def _get_window(self, hook_name: str) -> _HookBudgetWindow:
        if hook_name not in self._windows:
            self._windows[hook_name] = _HookBudgetWindow()
        return self._windows[hook_name]

    def _prune(self, cutoff: float, hook_name: str) -> None:
        window = self._get_window(hook_name)
        window.calls = [t for t in window.calls if t > cutoff]
        window.tokens = [(t, n) for t, n in window.tokens if t > cutoff]

    def _prune_global(self, cutoff: float) -> None:
        self._global_costs = [(t, c) for t, c in self._global_costs if t > cutoff]

    def record(self, hook_name: str, *, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        now = time.monotonic()
        cutoff = now - 3600
        with self._lock:
            self._prune(cutoff, hook_name)
            self._prune_global(cutoff)
            window = self._get_window(hook_name)
            window.calls.append(now)
            window.tokens.append((now, input_tokens + output_tokens))
            self._global_costs.append((now, cost_usd))

    def check(self, hook_name: str) -> bool:
        now = time.monotonic()
        cutoff = now - 3600

        with self._lock:
            if (self._calls_per_hour is None
                    and self._tokens_per_hour is None
                    and self._global_max_cost_per_hour is None):
                return True

            self._prune(cutoff, hook_name)
            self._prune_global(cutoff)

            window = self._get_window(hook_name)

            if self._calls_per_hour is not None:
                if len(window.calls) >= self._calls_per_hour:
                    return False

            if self._tokens_per_hour is not None:
                total_tokens = sum(n for _, n in window.tokens)
                if total_tokens >= self._tokens_per_hour:
                    return False

            if self._global_max_cost_per_hour is not None:
                total_cost = sum(c for _, c in self._global_costs)
                if total_cost >= self._global_max_cost_per_hour:
                    return False

            return True

    def remaining(self, hook_name: str) -> dict[str, Any]:
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
        with self._lock:
            self._windows[hook_name] = _HookBudgetWindow()
