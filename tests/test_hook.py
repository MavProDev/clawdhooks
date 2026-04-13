import pytest
from pydantic import BaseModel
from claudehooks.router import HookRouter
from claudehooks.providers.base import LLMResponse
from claudehooks.types import FallbackStrategy
from claudehooks.exceptions import HookTimeoutError, HookProviderError


class ModerationResult(BaseModel):
    action: str
    reason: str


class UserPost(BaseModel):
    title: str
    content: str
    author: str


@pytest.mark.asyncio
async def test_hook_basic_call(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"action": "allow", "reason": "clean content"})
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def moderate(post: UserPost) -> ModerationResult:
        """Evaluate this post against community guidelines."""
        ...

    post = UserPost(title="Hello", content="Nice day", author="user1")
    result = await moderate(post)

    assert isinstance(result, ModerationResult)
    assert result.action == "allow"
    assert result.reason == "clean content"

    # Verify provider was called with correct args
    assert len(mock_provider._calls) == 1
    call = mock_provider._calls[0]
    assert call["system_prompt"].startswith("Evaluate this post against community guidelines.")
    assert '"title": "Hello"' in call["user_message"] or '"title":"Hello"' in call["user_message"]


@pytest.mark.asyncio
async def test_hook_with_multiple_params(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"action": "flag", "reason": "politics"})
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="haiku")
    async def classify(text: str, categories: list[str]) -> ModerationResult:
        """Classify the text into one of the given categories."""
        ...

    result = await classify("election results", ["sports", "politics", "tech"])

    assert result.action == "flag"
    call = mock_provider._calls[0]
    assert "election results" in call["user_message"]
    assert "politics" in call["user_message"]


@pytest.mark.asyncio
async def test_hook_fallback_skip_on_error(mock_provider):
    mock_provider._responses = [Exception("API error")]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", fallback="skip")
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        ...

    result = await moderate("hello")
    assert result is None


@pytest.mark.asyncio
async def test_hook_fallback_default(mock_provider):
    default = ModerationResult(action="allow", reason="default fallback")
    mock_provider._responses = [Exception("API error")]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", fallback="default", default_response=default)
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        ...

    result = await moderate("hello")
    assert result.action == "allow"
    assert result.reason == "default fallback"


@pytest.mark.asyncio
async def test_hook_fallback_raise(mock_provider):
    mock_provider._responses = [Exception("API error")]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", fallback="raise", max_retries=0)
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        ...

    with pytest.raises(HookProviderError):
        await moderate("hello")


@pytest.mark.asyncio
async def test_hook_fallback_local_uses_function_body(mock_provider):
    mock_provider._responses = [Exception("API error")]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", fallback="local")
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        return ModerationResult(action="allow", reason="local rule")

    result = await moderate("hello")
    assert result.action == "allow"
    assert result.reason == "local rule"


@pytest.mark.asyncio
async def test_hook_retries_on_failure(mock_provider, make_response):
    mock_provider._responses = [
        Exception("first fail"),
        make_response(content={"action": "allow", "reason": "retry worked"}),
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", max_retries=1)
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        ...

    result = await moderate("hello")
    assert result.action == "allow"
    assert len(mock_provider._calls) == 2


@pytest.mark.asyncio
async def test_hook_explicit_system_prompt(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"action": "block", "reason": "strict mode"})
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", system_prompt="You are extremely strict. Block everything.")
    async def moderate(text: str) -> ModerationResult:
        """This docstring is ignored."""
        ...

    await moderate("hello")
    call = mock_provider._calls[0]
    assert call["system_prompt"].startswith("You are extremely strict. Block everything.")


@pytest.mark.asyncio
async def test_hook_stats_tracked(mock_provider, make_response):
    mock_provider._responses = [
        make_response(
            content={"action": "allow", "reason": "ok"},
            input_tokens=200,
            output_tokens=80,
            input_cost_per_mtok=3.0,
            output_cost_per_mtok=15.0,
        )
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        ...

    await moderate("hello")

    stats = router.stats()
    assert stats["total_calls"] == 1
    assert stats["total_input_tokens"] == 200
    assert stats["total_output_tokens"] == 80
    assert stats["total_cost_usd"] > 0
    assert "moderate" in stats["hooks"]


def test_hook_sync_call(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"action": "allow", "reason": "sync works"})
    ]
    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def moderate(text: str) -> ModerationResult:
        """Moderate this text."""
        ...

    result = moderate.sync("hello")
    assert isinstance(result, ModerationResult)
    assert result.action == "allow"


def test_hook_requires_return_type(mock_provider):
    router = HookRouter(provider=mock_provider)

    with pytest.raises(TypeError, match="return type"):
        @router.hook(model="sonnet")
        async def bad_hook(text: str):
            """No return type."""
            ...


def test_hook_requires_pydantic_return(mock_provider):
    router = HookRouter(provider=mock_provider)

    with pytest.raises(TypeError, match="Pydantic BaseModel"):
        @router.hook(model="sonnet")
        async def bad_hook(text: str) -> str:
            """Returns a string, not a model."""
            ...
