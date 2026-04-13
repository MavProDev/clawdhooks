import pytest
from pydantic import BaseModel
from claudehooks.router import HookRouter
from claudehooks.providers.base import LLMResponse
from claudehooks.types import FallbackStrategy


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float


def test_router_creation_with_provider(mock_provider):
    router = HookRouter(provider=mock_provider)
    assert router.provider.name == "mock"


def test_router_requires_provider_or_key():
    with pytest.raises(ValueError, match="Provide either"):
        HookRouter()


def test_router_hook_registers(mock_provider):
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def analyze(text: str) -> SentimentResult:
        """Analyze the sentiment of this text."""
        ...

    assert "analyze" in router.hooks
    assert router.hooks["analyze"].model == "sonnet"
    assert router.hooks["analyze"].fallback == FallbackStrategy.SKIP


def test_router_hook_with_config(mock_provider):
    router = HookRouter(provider=mock_provider)

    @router.hook(model="opus", timeout_seconds=20.0, fallback="raise", max_retries=2)
    async def critical_decision(data: str) -> SentimentResult:
        """Make a critical decision."""
        ...

    config = router.hooks["critical_decision"]
    assert config.model == "opus"
    assert config.timeout_seconds == 20.0
    assert config.fallback == FallbackStrategy.RAISE
    assert config.max_retries == 2


def test_router_hook_uses_docstring_as_prompt(mock_provider):
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def analyze(text: str) -> SentimentResult:
        """You are a sentiment analyzer. Classify the sentiment."""
        ...

    assert router.hooks["analyze"].system_prompt == (
        "You are a sentiment analyzer. Classify the sentiment."
    )


def test_router_hook_explicit_prompt_overrides_docstring(mock_provider):
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", system_prompt="Custom prompt here.")
    async def analyze(text: str) -> SentimentResult:
        """This docstring is ignored."""
        ...

    assert router.hooks["analyze"].system_prompt == "Custom prompt here."


def test_router_stats_empty(mock_provider):
    router = HookRouter(provider=mock_provider)
    stats = router.stats()
    assert stats["total_calls"] == 0
    assert stats["total_cost_usd"] == 0.0
    assert stats["total_input_tokens"] == 0
    assert stats["total_output_tokens"] == 0
    assert stats["hooks"] == {}
