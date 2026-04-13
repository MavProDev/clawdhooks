"""OpenAI GPT provider."""
from __future__ import annotations

import json
import time
from typing import Any

import openai

from .base import LLMProvider, LLMResponse
from ..exceptions import HookProviderError

MODEL_ALIASES: dict[str, str] = {
    "gpt4o": "gpt-4o",
    "gpt4o-mini": "gpt-4o-mini",
    "o3": "o3",
    "o3-mini": "o3-mini",
}

MODEL_TIMEOUTS: dict[str, float] = {
    "gpt4o-mini": 5.0,
    "gpt4o": 10.0,
    "o3-mini": 15.0,
    "o3": 30.0,
}

MODEL_PRICING: dict[str, tuple[float, float]] = {
    # (input $/MTok, output $/MTok) — approximate
    "gpt4o-mini": (0.15, 0.60),
    "gpt4o": (2.50, 10.00),
    "o3-mini": (1.10, 4.40),
    "o3": (10.00, 40.00),
}


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider using the official SDK."""

    def __init__(self, api_key: str):
        self._client = openai.AsyncOpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        return "openai"

    def default_model(self) -> str:
        return MODEL_ALIASES["gpt4o"]

    def resolve_model(self, model: str) -> str:
        return MODEL_ALIASES.get(model, model)

    def model_timeout(self, model: str) -> float:
        if model in MODEL_TIMEOUTS:
            return MODEL_TIMEOUTS[model]
        for alias, full_id in MODEL_ALIASES.items():
            if model == full_id:
                return MODEL_TIMEOUTS.get(alias, 10.0)
        return 10.0

    def _get_pricing(self, model: str) -> tuple[float, float]:
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
        input_pricing, output_pricing = self._get_pricing(model)

        start = time.monotonic()
        response = await self._client.chat.completions.create(
            model=resolved_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": output_schema,
                },
            },
        )
        latency_ms = (time.monotonic() - start) * 1000

        message = response.choices[0].message

        if message.refusal:
            raise HookProviderError(
                f"OpenAI refused the request: {message.refusal}",
                provider=self.name,
            )

        if not message.content:
            raise HookProviderError(
                "No content in OpenAI response",
                provider=self.name,
            )

        try:
            content = json.loads(message.content)
        except json.JSONDecodeError as e:
            raise HookProviderError(
                f"Invalid JSON in OpenAI response: {e}",
                provider=self.name,
            ) from e

        return LLMResponse(
            content=content,
            raw_text=message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=response.model,
            cached_input_tokens=0,
            latency_ms=latency_ms,
            input_cost_per_mtok=input_pricing,
            output_cost_per_mtok=output_pricing,
        )
