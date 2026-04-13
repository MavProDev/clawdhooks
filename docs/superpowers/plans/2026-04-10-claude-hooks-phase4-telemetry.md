# claude-hooks Phase 4: Telemetry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Add production-grade observability via OpenTelemetry. Every hook invocation creates a span with GenAI semantic conventions. Metrics track cost, latency, tokens, and fallback counts. Graceful no-op when OTel isn't installed.

**Architecture:** `HookTelemetry` class wraps OTel tracer + meter. No-op fallback when `opentelemetry` isn't installed. Router creates/ends spans around hook execution. OTel is an optional dependency (`pip install claude-hooks[telemetry]`).

**Tech Stack:** opentelemetry-api, opentelemetry-sdk (optional), existing pytest infrastructure.

---

## Task 1: Telemetry Module

**Files:**
- Create: `src/clawd_hooks/telemetry.py`
- Create: `tests/test_telemetry.py`
- Modify: `pyproject.toml` — add telemetry optional dependency

### Implementation `src/clawd_hooks/telemetry.py`:

```python
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
            self._tracer = trace.get_tracer("claude-hooks")
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
        return self._tracer.start_span(
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

        # Span attributes
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
        self._token_counter.add(
            ctx.input_tokens + ctx.output_tokens, attributes
        )
        if ctx.used_fallback:
            self._fallback_counter.add(
                1,
                {**attributes, "fallback_strategy": ctx.fallback_strategy or "unknown"},
            )
```

### Tests `tests/test_telemetry.py`:

```python
import pytest
from clawd_hooks.telemetry import HookTelemetry, _NoOpSpan, HAS_OTEL
from clawd_hooks.context import HookContext
from clawd_hooks.types import HookStatus


def test_noop_span_is_safe():
    span = _NoOpSpan()
    span.set_attribute("key", "value")
    span.set_status("OK")
    span.end()
    # context manager works
    with span:
        pass


def test_telemetry_disabled_returns_noop():
    t = HookTelemetry(enabled=False)
    assert t.enabled is False
    span = t.start_span("test", "sonnet")
    assert isinstance(span, _NoOpSpan)


def test_telemetry_end_span_noop_when_disabled():
    t = HookTelemetry(enabled=False)
    span = t.start_span("test", "sonnet")
    ctx = HookContext(hook_name="test", model="sonnet")
    # Should not raise
    t.end_span(span, ctx)


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
def test_telemetry_enabled_creates_real_span():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import opentelemetry.trace
    original_provider = opentelemetry.trace.get_tracer_provider()
    opentelemetry.trace.set_tracer_provider(provider)

    try:
        t = HookTelemetry(enabled=True)
        span = t.start_span("moderate", "sonnet")

        ctx = HookContext(hook_name="moderate", model="sonnet")
        ctx.input_tokens = 200
        ctx.output_tokens = 80
        ctx.cost_usd = 0.0018
        ctx.latency_ms = 350.0

        t.end_span(span, ctx)

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == "hook.moderate sonnet"
        assert s.attributes["hook.name"] == "moderate"
        assert s.attributes["gen_ai.system"] == "claude"
        assert s.attributes["gen_ai.usage.input_tokens"] == 200
        assert s.attributes["gen_ai.usage.output_tokens"] == 80
        assert s.attributes["hook.cost_usd"] == 0.0018
        assert s.attributes["hook.status"] == "ok"
    finally:
        opentelemetry.trace.set_tracer_provider(original_provider)


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
def test_telemetry_records_fallback_span():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import opentelemetry.trace
    original_provider = opentelemetry.trace.get_tracer_provider()
    opentelemetry.trace.set_tracer_provider(provider)

    try:
        t = HookTelemetry(enabled=True)
        span = t.start_span("moderate", "sonnet")

        ctx = HookContext(hook_name="moderate", model="sonnet")
        ctx.record_fallback("skip", reason="timeout")

        t.end_span(span, ctx)

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        s = spans[0]
        assert s.attributes["hook.used_fallback"] is True
        assert s.attributes["hook.fallback_strategy"] == "skip"
        assert s.attributes["hook.status"] == "fallback"
    finally:
        opentelemetry.trace.set_tracer_provider(original_provider)


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
def test_telemetry_error_span():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.trace import StatusCode

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import opentelemetry.trace
    original_provider = opentelemetry.trace.get_tracer_provider()
    opentelemetry.trace.set_tracer_provider(provider)

    try:
        t = HookTelemetry(enabled=True)
        span = t.start_span("moderate", "sonnet")

        ctx = HookContext(hook_name="moderate", model="sonnet")
        ctx.record_error(ValueError("bad input"))

        t.end_span(span, ctx)

        spans = exporter.get_finished_spans()
        s = spans[0]
        assert s.status.status_code == StatusCode.ERROR
        assert s.attributes["hook.status"] == "error"
    finally:
        opentelemetry.trace.set_tracer_provider(original_provider)
```

### pyproject.toml change:

Add to `[project.optional-dependencies]`:
```toml
telemetry = [
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
]
```

Add to the `dev` list:
```
"opentelemetry-api>=1.20",
"opentelemetry-sdk>=1.20",
```

After modifying pyproject.toml, run: `pip install -e ".[dev]"` to install OTel.

### Commit: `"feat: add HookTelemetry with OpenTelemetry spans and metrics"`

---

## Task 2: Wire Telemetry into Router

**Files:**
- Modify: `src/clawd_hooks/router.py`
- Create: `tests/test_router_phase4.py`

### Router changes:

**1. Add import:**
```python
from .telemetry import HookTelemetry
```

**2. Add __init__ param:**
```python
telemetry_enabled: bool = False,
```

And in body:
```python
self._telemetry = HookTelemetry(enabled=telemetry_enabled)
```

**3. In _execute_hook, right after creating HookContext:**
```python
span = self._telemetry.start_span(config.name, resolved_model)
```

**4. Before EVERY return in _execute_hook (there are multiple), add:**
```python
self._telemetry.end_span(span, ctx)
```

This means adding `self._telemetry.end_span(span, ctx)` before:
- Budget gate fallback return
- Circuit breaker gate fallback return
- Cache hit return
- Successful API response return
- Cache fallback return (both branches)
- Cascade fallback return (both branches)
- Standard fallback return

**Simplification:** Wrap the entire body of _execute_hook in a try/finally that always calls end_span:

```python
async def _execute_hook(self, ...) -> Any:
    ...
    span = self._telemetry.start_span(config.name, resolved_model)
    try:
        # ... all existing logic ...
    finally:
        self._telemetry.end_span(span, ctx)
```

This ensures the span is always ended, regardless of which path returns.

But the ctx needs to be created before the try block.

### Tests:

```python
import pytest
from pydantic import BaseModel
from clawd_hooks.router import HookRouter
from clawd_hooks.telemetry import HAS_OTEL


class Result(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_telemetry_disabled_by_default(mock_provider, make_response):
    mock_provider._responses = [make_response(content={"answer": "yes"})]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    result = await decide("test")
    assert result.answer == "yes"
    assert router._telemetry.enabled is False


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
@pytest.mark.asyncio
async def test_telemetry_creates_spans(mock_provider, make_response):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    import opentelemetry.trace

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    original = opentelemetry.trace.get_tracer_provider()
    opentelemetry.trace.set_tracer_provider(provider)

    try:
        mock_provider._responses = [
            make_response(
                content={"answer": "yes"},
                input_tokens=150,
                output_tokens=60,
                input_cost_per_mtok=3.0,
                output_cost_per_mtok=15.0,
            )
        ]
        router = HookRouter(provider=mock_provider, telemetry_enabled=True)

        @router.hook(model="sonnet")
        async def decide(q: str) -> Result:
            """Answer."""
            ...

        await decide("test")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        s = spans[0]
        assert "hook.decide" in s.name
        assert s.attributes["hook.name"] == "decide"
        assert s.attributes["gen_ai.usage.input_tokens"] == 150
    finally:
        opentelemetry.trace.set_tracer_provider(original)
```

### Commit: `"feat: wire telemetry into router lifecycle"`
### Tag: `v0.4.0-alpha`
