"""Phase 2 integration tests — Budget + Circuit Breaker wired into HookRouter."""
import pytest
import asyncio
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
    router = HookRouter(provider=mock_provider, calls_per_hour=2)

    @router.hook(model="sonnet", fallback="skip")
    async def decide(q: str) -> Result:
        """Answer the question."""
        ...

    await decide("q1")
    await decide("q2")
    result = await decide("q3")
    assert result is None
    assert len(mock_provider._calls) == 2


@pytest.mark.asyncio
async def test_router_budget_raise_strategy(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"answer": "yes"}),
    ]
    router = HookRouter(provider=mock_provider, calls_per_hour=1)

    @router.hook(model="sonnet", fallback="raise")
    async def decide(q: str) -> Result:
        """Answer the question."""
        ...

    await decide("q1")
    with pytest.raises(HookBudgetError):
        await decide("q2")


@pytest.mark.asyncio
async def test_router_circuit_breaker_trips(mock_provider):
    mock_provider._responses = [
        Exception("fail 1"),
        Exception("fail 2"),
        Exception("fail 3"),
        Exception("fail 4"),
    ]
    router = HookRouter(provider=mock_provider, circuit_failure_threshold=3)

    @router.hook(model="sonnet", fallback="skip", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("q1")
    await decide("q2")
    await decide("q3")
    await decide("q4")
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

    await decide("q1")
    await decide("q2")
    await asyncio.sleep(0.15)
    result = await decide("q3")
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
