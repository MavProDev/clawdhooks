"""Shared test fixtures for claude-hooks."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from claude_hooks.providers.base import LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    """In-memory mock provider for testing hooks without API calls."""

    def __init__(self, responses: list | None = None):
        self._responses = responses or []
        self._calls: list[dict] = []
        self._call_index = 0

    @property
    def name(self) -> str:
        return "mock"

    def default_model(self) -> str:
        return "mock-model"

    def model_timeout(self, model: str) -> float:
        return 5.0

    async def complete(self, **kwargs) -> LLMResponse:
        self._calls.append(kwargs)
        if self._call_index < len(self._responses):
            response = self._responses[self._call_index]
            self._call_index += 1
            if isinstance(response, Exception):
                raise response
            return response
        return LLMResponse(
            content={},
            raw_text="{}",
            input_tokens=100,
            output_tokens=50,
            model="mock-model",
        )


@pytest.fixture
def mock_provider():
    """Return a fresh MockProvider."""
    return MockProvider()


@pytest.fixture
def make_response():
    """Factory fixture for creating LLMResponse objects."""
    def _make(**kwargs) -> LLMResponse:
        defaults = dict(
            content={},
            raw_text="{}",
            input_tokens=100,
            output_tokens=50,
            model="mock-model",
            cached_input_tokens=0,
            latency_ms=100.0,
        )
        defaults.update(kwargs)
        return LLMResponse(**defaults)
    return _make


@pytest.fixture
def mock_anthropic_client():
    """Return a mocked anthropic.AsyncAnthropic client."""
    client = AsyncMock()

    # Build a realistic response object
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.input = {"action": "allow", "reason": "test"}

    usage = MagicMock()
    usage.input_tokens = 150
    usage.output_tokens = 60
    usage.cache_read_input_tokens = 100

    response = MagicMock()
    response.content = [tool_use_block]
    response.usage = usage
    response.model = "claude-sonnet-4-6"

    client.messages.create = AsyncMock(return_value=response)
    return client
