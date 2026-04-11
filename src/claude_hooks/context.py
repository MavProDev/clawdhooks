"""Runtime context for hook invocations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .providers.base import LLMResponse
from .types import HookStatus


@dataclass
class HookContext:
    """Carries runtime metadata for a single hook invocation."""

    hook_name: str
    model: str
    status: HookStatus = HookStatus.OK
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    retries: int = 0
    used_fallback: bool = False
    fallback_strategy: str | None = None
    fallback_reason: str | None = None
    error: str | None = None

    def record_response(self, response: LLMResponse) -> None:
        """Record metrics from a successful LLM response."""
        self.input_tokens = response.input_tokens
        self.output_tokens = response.output_tokens
        self.cached_input_tokens = response.cached_input_tokens
        self.latency_ms = response.latency_ms
        self.cost_usd = response.cost_usd
        self.status = HookStatus.OK

    def record_fallback(self, strategy: str, *, reason: str) -> None:
        """Record that a fallback was used."""
        self.used_fallback = True
        self.fallback_strategy = strategy
        self.fallback_reason = reason
        self.status = HookStatus.FALLBACK

    def record_error(self, error: Exception) -> None:
        """Record an unrecoverable error."""
        self.status = HookStatus.ERROR
        self.error = str(error)

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to a dictionary."""
        return {
            "hook_name": self.hook_name,
            "model": self.model,
            "status": self.status.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "retries": self.retries,
            "used_fallback": self.used_fallback,
            "fallback_strategy": self.fallback_strategy,
            "fallback_reason": self.fallback_reason,
            "error": self.error,
        }
