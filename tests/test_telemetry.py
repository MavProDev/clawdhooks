import pytest
from claude_hooks.telemetry import HookTelemetry, _NoOpSpan, HAS_OTEL
from claude_hooks.context import HookContext
from claude_hooks.types import HookStatus


def test_noop_span_is_safe():
    span = _NoOpSpan()
    span.set_attribute("key", "value")
    span.set_status("OK")
    span.end()
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
    t.end_span(span, ctx)


if HAS_OTEL:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    import opentelemetry.trace

    # Set up a single global provider for all OTel tests — OTel 1.20+ only allows
    # setting the provider once per process. We use a shared InMemorySpanExporter
    # and reset it between tests.
    _otel_exporter = InMemorySpanExporter()
    _otel_provider = TracerProvider()
    _otel_provider.add_span_processor(SimpleSpanProcessor(_otel_exporter))
    opentelemetry.trace.set_tracer_provider(_otel_provider)

    @pytest.fixture(autouse=False)
    def otel_exporter():
        """Provide a fresh (cleared) InMemorySpanExporter for each test."""
        _otel_exporter.clear()
        return _otel_exporter


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
def test_telemetry_enabled_creates_real_span(otel_exporter):
    t = HookTelemetry(enabled=True)
    span = t.start_span("moderate", "sonnet")

    ctx = HookContext(hook_name="moderate", model="sonnet")
    ctx.input_tokens = 200
    ctx.output_tokens = 80
    ctx.cost_usd = 0.0018
    ctx.latency_ms = 350.0

    t.end_span(span, ctx)

    spans = otel_exporter.get_finished_spans()
    assert len(spans) == 1
    s = spans[0]
    assert s.name == "hook.moderate sonnet"
    assert s.attributes["hook.name"] == "moderate"
    assert s.attributes["gen_ai.system"] == "claude"
    assert s.attributes["gen_ai.usage.input_tokens"] == 200
    assert s.attributes["gen_ai.usage.output_tokens"] == 80
    assert s.attributes["hook.cost_usd"] == 0.0018
    assert s.attributes["hook.status"] == "ok"


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
def test_telemetry_records_fallback_span(otel_exporter):
    t = HookTelemetry(enabled=True)
    span = t.start_span("moderate", "sonnet")

    ctx = HookContext(hook_name="moderate", model="sonnet")
    ctx.record_fallback("skip", reason="timeout")

    t.end_span(span, ctx)

    spans = otel_exporter.get_finished_spans()
    assert len(spans) == 1
    s = spans[0]
    assert s.attributes["hook.used_fallback"] is True
    assert s.attributes["hook.fallback_strategy"] == "skip"
    assert s.attributes["hook.status"] == "fallback"


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
def test_telemetry_error_span(otel_exporter):
    from opentelemetry.trace import StatusCode

    t = HookTelemetry(enabled=True)
    span = t.start_span("moderate", "sonnet")

    ctx = HookContext(hook_name="moderate", model="sonnet")
    ctx.record_error(ValueError("bad input"))

    t.end_span(span, ctx)

    spans = otel_exporter.get_finished_spans()
    s = spans[0]
    assert s.status.status_code == StatusCode.ERROR
    assert s.attributes["hook.status"] == "error"
