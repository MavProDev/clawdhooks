"""HookRouter — central registry for all hooks."""
from __future__ import annotations

import asyncio
import functools
import inspect
import json
import threading
from typing import Any, Callable, TypeVar, get_type_hints

from pydantic import BaseModel

from .context import HookContext
from .exceptions import (
    HookError,
    HookProviderError,
    HookTimeoutError,
    HookValidationError,
)
from .fallbacks import resolve_fallback_async
from .providers.base import LLMProvider, LLMResponse
from .types import FallbackStrategy, HookConfig, HookStatus

T = TypeVar("T")


def _serialize_input(func: Callable, args: tuple, kwargs: dict) -> str:
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    params = dict(bound.arguments)

    if len(params) == 1:
        value = next(iter(params.values()))
        if isinstance(value, BaseModel):
            return value.model_dump_json()

    serialized = {}
    for key, value in params.items():
        if isinstance(value, BaseModel):
            serialized[key] = value.model_dump()
        elif hasattr(value, "__dict__") and not isinstance(value, (str, int, float, bool, list, dict)):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return json.dumps(serialized, default=str)


def _get_output_schema(func: Callable) -> tuple[type[BaseModel], dict[str, Any]]:
    hints = get_type_hints(func)
    return_type = hints.get("return")
    if return_type is None:
        raise TypeError(f"Hook '{func.__name__}' must have a return type annotation (Pydantic model)")
    if not (isinstance(return_type, type) and issubclass(return_type, BaseModel)):
        raise TypeError(
            f"Hook '{func.__name__}' return type must be a Pydantic BaseModel, got {return_type}"
        )
    return return_type, return_type.model_json_schema()


def _run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    result_container = {}

    def _run():
        try:
            result_container["result"] = asyncio.run(coro)
        except Exception as e:
            result_container["error"] = e

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()
    if "error" in result_container:
        raise result_container["error"]
    return result_container["result"]


class HookRouter:
    def __init__(self, *, provider: LLMProvider | None = None, api_key: str | None = None):
        if provider is not None:
            self._provider = provider
        elif api_key is not None:
            from .providers.claude import ClaudeProvider
            self._provider = ClaudeProvider(api_key=api_key)
        else:
            raise ValueError("Provide either a 'provider' instance or an 'api_key' for Claude.")
        self._hooks: dict[str, HookConfig] = {}
        self._stats: dict[str, list[HookContext]] = {}

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def hooks(self) -> dict[str, HookConfig]:
        return self._hooks

    def hook(
        self,
        *,
        model: str | None = None,
        timeout_seconds: float | None = None,
        fallback: str = "skip",
        system_prompt: str | None = None,
        default_response: Any = None,
        max_retries: int = 1,
    ) -> Callable:
        fallback_strategy = FallbackStrategy(fallback)

        def decorator(func: Callable) -> Callable:
            output_model, output_schema = _get_output_schema(func)
            prompt = system_prompt or (inspect.getdoc(func) or "")
            if not prompt:
                raise ValueError(
                    f"Hook '{func.__name__}' needs a system prompt. "
                    "Add a docstring or pass system_prompt=..."
                )

            # Detect stub functions — check if body is just ... or pass
            original_func = func
            try:
                source = inspect.getsource(func)
                lines = source.strip().split("\n")
                body_lines = []
                found_def = False
                in_docstring = False
                for line in lines:
                    stripped = line.strip()
                    if not found_def:
                        if stripped.startswith("def ") or stripped.startswith("async def "):
                            found_def = True
                        continue
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        if in_docstring:
                            in_docstring = False
                            continue
                        if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                            continue
                        in_docstring = True
                        continue
                    if in_docstring:
                        continue
                    if stripped:
                        body_lines.append(stripped)
                body = " ".join(body_lines).strip()
                if body in ("...", "pass", ""):
                    original_func = None
            except (OSError, TypeError):
                original_func = None

            config = HookConfig(
                name=func.__name__,
                model=model,
                timeout_seconds=timeout_seconds,
                fallback=fallback_strategy,
                system_prompt=prompt,
                default_response=default_response,
                max_retries=max_retries,
            )
            self._hooks[func.__name__] = config

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_hook(
                    config=config,
                    output_model=output_model,
                    output_schema=output_schema,
                    original_func=original_func,
                    args=args,
                    kwargs=kwargs,
                    bound_func=func,
                )

            async_wrapper.sync = lambda *a, **kw: _run_sync(async_wrapper(*a, **kw))
            async_wrapper.hook_config = config
            async_wrapper.output_model = output_model
            return async_wrapper

        return decorator

    async def _execute_hook(
        self,
        *,
        config: HookConfig,
        output_model: type[BaseModel],
        output_schema: dict[str, Any],
        original_func: Callable | None,
        args: tuple,
        kwargs: dict,
        bound_func: Callable,
    ) -> Any:
        resolved_model = config.model or self._provider.default_model()
        timeout = config.timeout_seconds or self._provider.model_timeout(resolved_model)
        ctx = HookContext(hook_name=config.name, model=resolved_model)
        user_message = _serialize_input(bound_func, args, kwargs)
        last_error: Exception | None = None
        attempts = 1 + config.max_retries

        for attempt in range(attempts):
            try:
                response = await asyncio.wait_for(
                    self._provider.complete(
                        system_prompt=config.system_prompt,
                        user_message=user_message,
                        output_schema=output_schema,
                        model=resolved_model,
                        timeout_seconds=timeout,
                    ),
                    timeout=timeout,
                )
                ctx.record_response(response)
                try:
                    result = output_model.model_validate(response.content)
                except Exception as validation_err:
                    if attempt < attempts - 1:
                        ctx.retries += 1
                        last_error = HookValidationError(
                            str(validation_err), raw_response=response.raw_text
                        )
                        continue
                    raise HookValidationError(
                        str(validation_err), raw_response=response.raw_text
                    ) from validation_err
                self._record_stats(ctx)
                return result
            except asyncio.TimeoutError:
                last_error = HookTimeoutError(
                    f"Hook '{config.name}' timed out after {timeout}s",
                    timeout_seconds=timeout,
                )
                if attempt < attempts - 1:
                    ctx.retries += 1
                    continue
            except (HookValidationError, HookError) as e:
                last_error = e
                if attempt < attempts - 1:
                    ctx.retries += 1
                    continue
            except Exception as e:
                last_error = HookProviderError(str(e), provider=self._provider.name)
                if attempt < attempts - 1:
                    ctx.retries += 1
                    continue

        ctx.record_fallback(config.fallback.value, reason=str(last_error))
        self._record_stats(ctx)
        return await resolve_fallback_async(
            strategy=config.fallback,
            error=last_error,
            original_func=original_func,
            args=args,
            kwargs=kwargs,
            default_response=config.default_response,
        )

    def _record_stats(self, ctx: HookContext) -> None:
        if ctx.hook_name not in self._stats:
            self._stats[ctx.hook_name] = []
        self._stats[ctx.hook_name].append(ctx)

    def stats(self) -> dict[str, Any]:
        total_calls = 0
        total_cost = 0.0
        total_input = 0
        total_output = 0
        hook_stats = {}
        for hook_name, contexts in self._stats.items():
            calls = len(contexts)
            cost = sum(c.cost_usd for c in contexts)
            inp = sum(c.input_tokens for c in contexts)
            out = sum(c.output_tokens for c in contexts)
            fallbacks = sum(1 for c in contexts if c.used_fallback)
            total_calls += calls
            total_cost += cost
            total_input += inp
            total_output += out
            hook_stats[hook_name] = {
                "calls": calls,
                "cost_usd": cost,
                "input_tokens": inp,
                "output_tokens": out,
                "fallbacks": fallbacks,
                "avg_latency_ms": (
                    sum(c.latency_ms for c in contexts) / calls if calls else 0
                ),
            }
        return {
            "total_calls": total_calls,
            "total_cost_usd": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "hooks": hook_stats,
        }
