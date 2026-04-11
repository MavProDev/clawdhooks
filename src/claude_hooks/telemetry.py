"""OpenTelemetry integration for claude-hooks."""
from __future__ import annotations

from typing import Any

from .context import HookContext
from .types import HookStatus

try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import StatusCode

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


class _NoOpSpan:
    """No-op span when OpenTelemetry is not installed."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any, description: str | None = None) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class HookTelemetry:
    """OpenTelemetry instrumentation for hook invocations.

    Creates spans and records metrics for each hook call.
    Degrades to no-op when opentelemetry is not installed.
    """

    def __init__(self, *, enabled: bool = True):
        self._enabled = enabled and HAS_OTEL
        if self._enabled:
            self._meter = metrics.get_meter("claude-hooks")
            self._duration_histogram = self._meter.create_histogram(
                "hook.duration_ms",
                unit="ms",
                description="Hook invocation duration in milliseconds",
            )
            self._cost_counter = self._meter.create_counter(
                "hook.cost_usd",
                unit="usd",
                description="Cumulative hook invocation cost in USD",
            )
            self._token_counter = self._meter.create_counter(
                "hook.tokens",
                description="Total tokens used by hook invocations",
            )
            self._fallback_counter = self._meter.create_counter(
                "hook.fallback_count",
                description="Number of fallback invocations",
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start_span(self, hook_name: str, model: str) -> Any:
        """Start a new span for a hook invocation."""
        if not self._enabled:
            return _NoOpSpan()
        tracer = trace.get_tracer("claude-hooks")
        return tracer.start_span(
            f"hook.{hook_name} {model}",
            attributes={
                "hook.name": hook_name,
                "gen_ai.system": "claude",
                "gen_ai.request.model": model,
            },
        )

    def end_span(self, span: Any, ctx: HookContext) -> None:
        """End a span and record metrics from the hook context."""
        if not self._enabled:
            return

        span.set_attribute("gen_ai.response.model", ctx.model)
        span.set_attribute("gen_ai.usage.input_tokens", ctx.input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", ctx.output_tokens)
        span.set_attribute("hook.cost_usd", ctx.cost_usd)
        span.set_attribute("hook.latency_ms", ctx.latency_ms)
        span.set_attribute("hook.retries", ctx.retries)
        span.set_attribute("hook.used_fallback", ctx.used_fallback)
        span.set_attribute("hook.status", ctx.status.value)

        if ctx.fallback_strategy:
            span.set_attribute("hook.fallback_strategy", ctx.fallback_strategy)

        if ctx.cached_input_tokens > 0:
            span.set_attribute("gen_ai.usage.cached_tokens", ctx.cached_input_tokens)

        if ctx.status == HookStatus.ERROR:
            span.set_status(StatusCode.ERROR, ctx.error or "unknown error")
        else:
            span.set_status(StatusCode.OK)

        span.end()

        # Record metrics
        attributes = {"hook.name": ctx.hook_name, "model": ctx.model}
        self._duration_histogram.record(ctx.latency_ms, attributes)
        self._cost_counter.add(ctx.cost_usd, attributes)
        self._token_counter.add(ctx.input_tokens + ctx.output_tokens, attributes)
        if ctx.used_fallback:
            self._fallback_counter.add(
                1,
                {**attributes, "fallback_strategy": ctx.fallback_strategy or "unknown"},
            )
