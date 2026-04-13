"""Phase 3 integration tests — Cache + Cascade wired into HookRouter."""
import pytest
from pydantic import BaseModel
from claudehooks.router import HookRouter


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
    r2 = await decide("what is 2+2")

    assert r1.answer == "first"
    assert r2.answer == "first"
    assert len(mock_provider._calls) == 1


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
    await decide("question 2")
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

    await decide("q1")
    result = await decide("q2")
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

    result = await decide("q1")
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
    assert len(mock_provider._calls) == 2


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
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    await decide("same")
    await decide("same")
    assert len(mock_provider._calls) == 2
