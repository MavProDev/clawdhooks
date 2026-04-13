import pytest
from claudehooks.providers.base import LLMProvider, LLMResponse


def test_llm_response_creation():
    resp = LLMResponse(
        content={"action": "allow"},
        raw_text='{"action": "allow"}',
        input_tokens=100,
        output_tokens=50,
        model="test-model",
    )
    assert resp.content == {"action": "allow"}
    assert resp.input_tokens == 100
    assert resp.output_tokens == 50
    assert resp.model == "test-model"
    assert resp.cached_input_tokens == 0
    assert resp.latency_ms == 0.0


def test_llm_response_with_cache():
    resp = LLMResponse(
        content={},
        raw_text="{}",
        input_tokens=100,
        output_tokens=50,
        model="test-model",
        cached_input_tokens=80,
        latency_ms=150.5,
    )
    assert resp.cached_input_tokens == 80
    assert resp.latency_ms == 150.5


def test_llm_response_cost_usd():
    resp = LLMResponse(
        content={},
        raw_text="{}",
        input_tokens=1000,
        output_tokens=500,
        model="test-model",
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    # 1000 input tokens at $3/MTok = $0.003
    # 500 output tokens at $15/MTok = $0.0075
    assert resp.cost_usd == pytest.approx(0.0105)


def test_llm_response_cost_usd_zero_when_no_pricing():
    resp = LLMResponse(
        content={},
        raw_text="{}",
        input_tokens=1000,
        output_tokens=500,
        model="test-model",
    )
    assert resp.cost_usd == 0.0


def test_llm_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        LLMProvider()
