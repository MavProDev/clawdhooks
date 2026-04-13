"""Phase 4 Task 2: Telemetry wired into HookRouter."""
import pytest
from pydantic import BaseModel
from claudehooks.router import HookRouter
from claudehooks.telemetry import HAS_OTEL


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


@pytest.mark.asyncio
async def test_telemetry_enabled_does_not_break_flow(mock_provider, make_response):
    """Verify that enabling telemetry doesn't affect hook behavior."""
    mock_provider._responses = [make_response(content={"answer": "yes"})]
    router = HookRouter(provider=mock_provider, telemetry_enabled=True)

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    result = await decide("test")
    assert result.answer == "yes"


@pytest.mark.asyncio
async def test_telemetry_with_fallback(mock_provider):
    """Verify telemetry works with fallback paths."""
    mock_provider._responses = [Exception("fail")]
    router = HookRouter(provider=mock_provider, telemetry_enabled=True)

    @router.hook(model="sonnet", fallback="skip", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    result = await decide("test")
    assert result is None  # fallback to skip


@pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
@pytest.mark.asyncio
async def test_telemetry_creates_spans(mock_provider, make_response, otel_exporter):
    """Verify router wires telemetry spans correctly (requires shared OTel provider)."""
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

    spans = otel_exporter.get_finished_spans()
    assert len(spans) == 1
    s = spans[0]
    assert "hook.decide" in s.name
    assert s.attributes["hook.name"] == "decide"
    assert s.attributes["gen_ai.usage.input_tokens"] == 150
