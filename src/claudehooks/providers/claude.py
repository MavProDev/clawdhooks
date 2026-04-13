"""Claude/Anthropic LLM provider."""
from __future__ import annotations

import json
import time
from typing import Any

import anthropic

from .base import LLMProvider, LLMResponse
from ..exceptions import HookProviderError

MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

MODEL_TIMEOUTS: dict[str, float] = {
    "haiku": 5.0,
    "sonnet": 10.0,
    "opus": 30.0,
}

MODEL_PRICING: dict[str, tuple[float, float]] = {
    # (input $/MTok, output $/MTok)
    "haiku": (1.0, 5.0),
    "sonnet": (3.0, 15.0),
    "opus": (5.0, 25.0),
}


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider using the official SDK."""

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "claude"

    def default_model(self) -> str:
        return MODEL_ALIASES["sonnet"]

    def resolve_model(self, model: str) -> str:
        """Resolve a model alias (e.g., 'sonnet') to a full model ID."""
        return MODEL_ALIASES.get(model, model)

    def model_timeout(self, model: str) -> float:
        """Return recommended timeout for the given model."""
        if model in MODEL_TIMEOUTS:
            return MODEL_TIMEOUTS[model]
        for alias, full_id in MODEL_ALIASES.items():
            if model == full_id:
                return MODEL_TIMEOUTS[alias]
        return 10.0

    def _get_pricing(self, model: str) -> tuple[float, float]:
        """Get (input, output) cost per MTok for a model."""
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]
        for alias, full_id in MODEL_ALIASES.items():
            if model == full_id:
                return MODEL_PRICING.get(alias, (0.0, 0.0))
        return (0.0, 0.0)

    async def complete(
        self,
        *,
        system_prompt: str,
        user_message: str,
        output_schema: dict[str, Any],
        model: str,
        timeout_seconds: float,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        resolved_model = self.resolve_model(model)

        tools = [
            {
                "name": "structured_response",
                "description": "Return the structured response matching the required schema.",
                "input_schema": output_schema,
            }
        ]

        start = time.monotonic()
        response = await self._client.messages.create(
            model=resolved_model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
            tool_choice={"type": "tool", "name": "structured_response"},
        )
        latency_ms = (time.monotonic() - start) * 1000

        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use_block is None:
            raise HookProviderError(
                "No structured response in Claude's response", provider=self.name
            )

        input_pricing, output_pricing = self._get_pricing(model)

        return LLMResponse(
            content=tool_use_block.input,
            raw_text=json.dumps(tool_use_block.input),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            cached_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            latency_ms=latency_ms,
            input_cost_per_mtok=input_pricing,
            output_cost_per_mtok=output_pricing,
        )
