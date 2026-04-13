import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from claudehooks.providers.openai import OpenAIProvider, MODEL_ALIASES, MODEL_PRICING


def test_model_aliases():
    assert "gpt4o" in MODEL_ALIASES
    assert "gpt4o-mini" in MODEL_ALIASES
    assert "o3" in MODEL_ALIASES


def test_provider_name():
    with patch("claudehooks.providers.openai.openai"):
        provider = OpenAIProvider(api_key="test-key")
    assert provider.name == "openai"


def test_default_model():
    with patch("claudehooks.providers.openai.openai"):
        provider = OpenAIProvider(api_key="test-key")
    default = provider.default_model()
    assert "gpt" in default or "4o" in default


def test_resolve_model_alias():
    with patch("claudehooks.providers.openai.openai"):
        provider = OpenAIProvider(api_key="test-key")
    assert provider.resolve_model("gpt4o") == MODEL_ALIASES["gpt4o"]
    assert provider.resolve_model("gpt4o-mini") == MODEL_ALIASES["gpt4o-mini"]


def test_resolve_model_passthrough():
    with patch("claudehooks.providers.openai.openai"):
        provider = OpenAIProvider(api_key="test-key")
    full_id = "gpt-4o-2024-08-06"
    assert provider.resolve_model(full_id) == full_id


def test_model_timeout_defaults():
    with patch("claudehooks.providers.openai.openai"):
        provider = OpenAIProvider(api_key="test-key")
    assert provider.model_timeout("gpt4o") == 10.0
    assert provider.model_timeout("gpt4o-mini") == 5.0
    assert provider.model_timeout("o3") == 30.0
    assert provider.model_timeout("unknown") == 10.0


@pytest.mark.asyncio
async def test_complete_sends_correct_request():
    mock_client = AsyncMock()

    # Build realistic response
    message = MagicMock()
    message.content = '{"action": "allow", "reason": "clean"}'
    message.refusal = None

    choice = MagicMock()
    choice.message = message

    usage = MagicMock()
    usage.prompt_tokens = 150
    usage.completion_tokens = 60

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response.model = "gpt-4o-2024-08-06"

    mock_client.chat.completions.create = AsyncMock(return_value=response)

    with patch("claudehooks.providers.openai.openai") as mock_openai:
        mock_openai.AsyncOpenAI.return_value = mock_client
        provider = OpenAIProvider(api_key="test-key")
    provider._client = mock_client

    schema = {"type": "object", "properties": {"action": {"type": "string"}, "reason": {"type": "string"}}}

    result = await provider.complete(
        system_prompt="You are a moderator.",
        user_message='{"text": "hello"}',
        output_schema=schema,
        model="gpt4o",
        timeout_seconds=10.0,
    )

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]

    assert call_kwargs["model"] == MODEL_ALIASES["gpt4o"]
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["messages"][0]["content"] == "You are a moderator."
    assert call_kwargs["messages"][1]["role"] == "user"
    assert call_kwargs["response_format"]["type"] == "json_schema"

    assert result.content == {"action": "allow", "reason": "clean"}
    assert result.input_tokens == 150
    assert result.output_tokens == 60
    assert result.model == "gpt-4o-2024-08-06"
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_complete_raises_on_refusal():
    mock_client = AsyncMock()

    message = MagicMock()
    message.content = None
    message.refusal = "I cannot help with that."

    choice = MagicMock()
    choice.message = message

    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 20

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response.model = "gpt-4o"

    mock_client.chat.completions.create = AsyncMock(return_value=response)

    with patch("claudehooks.providers.openai.openai") as mock_openai:
        mock_openai.AsyncOpenAI.return_value = mock_client
        provider = OpenAIProvider(api_key="test-key")
    provider._client = mock_client

    from claudehooks.exceptions import HookProviderError

    with pytest.raises(HookProviderError, match="refused"):
        await provider.complete(
            system_prompt="test",
            user_message="test",
            output_schema={"type": "object"},
            model="gpt4o",
            timeout_seconds=10.0,
        )
