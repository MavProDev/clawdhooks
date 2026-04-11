"""Fallback strategies for when Claude is unavailable."""
from __future__ import annotations

import inspect
from typing import Any, Callable

from .types import FallbackStrategy


def resolve_fallback(
    *,
    strategy: FallbackStrategy,
    error: Exception,
    original_func: Callable | None,
    args: tuple,
    kwargs: dict,
    default_response: Any,
) -> Any:
    """Resolve a fallback synchronously. Returns the fallback value or raises."""
    if strategy == FallbackStrategy.SKIP:
        return None

    if strategy == FallbackStrategy.DEFAULT:
        if default_response is None:
            raise ValueError(
                f"No default_response configured for fallback. Original error: {error}"
            )
        return default_response

    if strategy == FallbackStrategy.RAISE:
        raise error

    if strategy == FallbackStrategy.LOCAL:
        if original_func is None:
            return None
        return original_func(*args, **kwargs)

    raise ValueError(f"Unknown fallback strategy: {strategy}")


async def resolve_fallback_async(
    *,
    strategy: FallbackStrategy,
    error: Exception,
    original_func: Callable | None,
    args: tuple,
    kwargs: dict,
    default_response: Any,
) -> Any:
    """Resolve a fallback, handling both sync and async original functions."""
    if strategy == FallbackStrategy.SKIP:
        return None

    if strategy == FallbackStrategy.DEFAULT:
        if default_response is None:
            raise ValueError(
                f"No default_response configured for fallback. Original error: {error}"
            )
        return default_response

    if strategy == FallbackStrategy.RAISE:
        raise error

    if strategy == FallbackStrategy.LOCAL:
        if original_func is None:
            return None
        result = original_func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    raise ValueError(f"Unknown fallback strategy: {strategy}")
