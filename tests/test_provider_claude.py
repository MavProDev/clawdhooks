import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from claudehooks.providers.claude import ClaudeProvider, MODEL_ALIASES, MODEL_PRICING


def test_model_aliases():
    assert "haiku" in MODEL_ALIASES
    assert "sonnet" in MODEL_ALIASES
    assert "opus" in MODEL_ALIASES


def test_provider_name():
    with patch("claudehooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert provider.name == "claude"


def test_default_model():
    with patch("claudehooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert "sonnet" in provider.default_model()


def test_resolve_model_alias():
    with patch("claudehooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert provider.resolve_model("haiku") == MODEL_ALIASES["haiku"]
    assert provider.resolve_model("sonnet") == MODEL_ALIASES["sonnet"]
    assert provider.resolve_model("opus") == MODEL_ALIASES["opus"]


def test_resolve_model_passthrough():
    with patch("claudehooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    full_id = "claude-sonnet-4-6"
    assert provider.resolve_model(full_id) == full_id


def test_model_timeout_defaults():
    with patch("claudehooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert provider.model_timeout("haiku") == 5.0
    assert provider.model_timeout("sonnet") == 10.0
    assert provider.model_timeout("opus") == 30.0
    assert provider.model_timeout("unknown-model") == 10.0


@pytest.mark.asyncio
async def test_complete_sends_correct_request(mock_anthropic_client):
    with patch("claudehooks.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_anthropic_client
        provider = ClaudeProvider(api_key="test-key")

    provider._client = mock_anthropic_client

    schema = {"type": "object", "properties": {"action": {"type": "string"}}}

    result = await provider.complete(
        system_prompt="You are a moderator.",
        user_message='{"text": "hello"}',
        output_schema=schema,
        model="sonnet",
        timeout_seconds=10.0,
    )

    # Verify the API was called
    mock_anthropic_client.messages.create.assert_called_once()
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]

    # Verify model was resolved
    assert call_kwargs["model"] == MODEL_ALIASES["sonnet"]

    # Verify system prompt has cache_control
    assert call_kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}

    # Verify tool was created from schema
    assert call_kwargs["tools"][0]["name"] == "structured_response"
    assert call_kwargs["tools"][0]["input_schema"] == schema

    # Verify tool_choice forces structured output
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "structured_response"}

    # Verify response parsing
    assert result.content == {"action": "allow", "reason": "test"}
    assert result.input_tokens == 150
    assert result.output_tokens == 60
    assert result.cached_input_tokens == 100
    assert result.model == "claude-sonnet-4-6"
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_complete_raises_on_no_tool_use(mock_anthropic_client):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I can't do that"

    mock_anthropic_client.messages.create.return_value.content = [text_block]

    with patch("claudehooks.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_anthropic_client
        provider = ClaudeProvider(api_key="test-key")
    provider._client = mock_anthropic_client

    from claudehooks.exceptions import HookProviderError

    with pytest.raises(HookProviderError, match="No structured response"):
        await provider.complete(
            system_prompt="test",
            user_message="test",
            output_schema={"type": "object"},
            model="sonnet",
            timeout_seconds=10.0,
        )
