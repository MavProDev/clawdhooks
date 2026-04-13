import pytest
from pydantic import BaseModel
from claudehooks.fallbacks import resolve_fallback, resolve_fallback_async
from claudehooks.types import FallbackStrategy
from claudehooks.exceptions import HookTimeoutError, HookProviderError


class MockOutput(BaseModel):
    action: str
    reason: str


def test_skip_returns_none():
    result = resolve_fallback(
        strategy=FallbackStrategy.SKIP,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=None,
        args=(),
        kwargs={},
        default_response=None,
    )
    assert result is None


def test_default_returns_configured_value():
    default = MockOutput(action="allow", reason="default")
    result = resolve_fallback(
        strategy=FallbackStrategy.DEFAULT,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=None,
        args=(),
        kwargs={},
        default_response=default,
    )
    assert result == default
    assert result.action == "allow"


def test_default_raises_if_no_default_configured():
    with pytest.raises(ValueError, match="No default_response configured"):
        resolve_fallback(
            strategy=FallbackStrategy.DEFAULT,
            error=HookTimeoutError("timeout", timeout_seconds=5.0),
            original_func=None,
            args=(),
            kwargs={},
            default_response=None,
        )


def test_raise_reraises_original_error():
    original_error = HookProviderError("API down", provider="claude")
    with pytest.raises(HookProviderError, match="API down"):
        resolve_fallback(
            strategy=FallbackStrategy.RAISE,
            error=original_error,
            original_func=None,
            args=(),
            kwargs={},
            default_response=None,
        )


def test_local_calls_original_function():
    def my_fallback(text: str) -> MockOutput:
        return MockOutput(action="allow", reason="local fallback")

    result = resolve_fallback(
        strategy=FallbackStrategy.LOCAL,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=my_fallback,
        args=("hello",),
        kwargs={},
        default_response=None,
    )
    assert result.action == "allow"
    assert result.reason == "local fallback"


def test_local_returns_none_if_func_is_stub():
    def stub_func(text: str):
        ...

    result = resolve_fallback(
        strategy=FallbackStrategy.LOCAL,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=stub_func,
        args=("hello",),
        kwargs={},
        default_response=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_local_handles_async_fallback():
    async def async_fallback(text: str) -> MockOutput:
        return MockOutput(action="allow", reason="async local")

    result = await resolve_fallback_async(
        strategy=FallbackStrategy.LOCAL,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=async_fallback,
        args=("hello",),
        kwargs={},
        default_response=None,
    )
    assert result.action == "allow"
    assert result.reason == "async local"
