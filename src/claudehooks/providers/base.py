"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: dict[str, Any]
    raw_text: str
    input_tokens: int
    output_tokens: int
    model: str
    cached_input_tokens: int = 0
    latency_ms: float = 0.0
    input_cost_per_mtok: float = 0.0
    output_cost_per_mtok: float = 0.0

    @property
    def cost_usd(self) -> float:
        """Calculate the cost of this response in USD."""
        if self.input_cost_per_mtok == 0 and self.output_cost_per_mtok == 0:
            return 0.0
        input_cost = (self.input_tokens / 1_000_000) * self.input_cost_per_mtok
        output_cost = (self.output_tokens / 1_000_000) * self.output_cost_per_mtok
        return input_cost + output_cost


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
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
        """Send a completion request and return structured output."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'claude', 'openai')."""
        ...

    @abstractmethod
    def default_model(self) -> str:
        """Return the default model identifier."""
        ...

    @abstractmethod
    def model_timeout(self, model: str) -> float:
        """Return the recommended timeout in seconds for a given model."""
        ...
