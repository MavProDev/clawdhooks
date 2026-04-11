"""Celery task integration for claude-hooks."""
from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable

from ..router import HookRouter


def hook_task(
    router: HookRouter,
    *,
    model: str = "sonnet",
    fallback: str = "skip",
    system_prompt: str | None = None,
    max_retries: int = 1,
    **hook_kwargs: Any,
) -> Callable:
    """Decorator that wraps a function as both a claude hook and a Celery-compatible task.

    Usage:
        from claude_hooks.adapters.celery import hook_task

        @hook_task(router, model="haiku")
        def process_data(data: DataInput) -> ProcessResult:
            \"\"\"Process this data with Claude.\"\"\"
            return ProcessResult(status="fallback")  # local fallback

    The decorated function can be called directly (sync) or used as a Celery task.
    """

    def decorator(func: Callable) -> Callable:
        # Register as a hook
        hooked = router.hook(
            model=model,
            fallback=fallback,
            system_prompt=system_prompt,
            max_retries=max_retries,
            **hook_kwargs,
        )(func)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Sync wrapper for Celery task execution."""
            return hooked.sync(*args, **kwargs)

        # Preserve async access
        sync_wrapper.async_call = hooked
        sync_wrapper.hook_config = hooked.hook_config
        sync_wrapper.output_model = hooked.output_model

        return sync_wrapper

    return decorator
