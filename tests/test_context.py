import pytest
from claude_hooks.context import HookContext
from claude_hooks.types import HookStatus


def test_context_creation():
    ctx = HookContext(hook_name="moderate", model="sonnet")
    assert ctx.hook_name == "moderate"
    assert ctx.model == "sonnet"
    assert ctx.status == HookStatus.OK
    assert ctx.input_tokens == 0
    assert ctx.output_tokens == 0
    assert ctx.cost_usd == 0.0
    assert ctx.latency_ms == 0.0
    assert ctx.cached_input_tokens == 0
    assert ctx.retries == 0
    assert ctx.used_fallback is False


def test_context_from_response(make_response):
    resp = make_response(
        content={"action": "block"},
        input_tokens=200,
        output_tokens=80,
        cached_input_tokens=150,
        latency_ms=350.0,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    ctx = HookContext(hook_name="moderate", model="sonnet")
    ctx.record_response(resp)

    assert ctx.input_tokens == 200
    assert ctx.output_tokens == 80
    assert ctx.cached_input_tokens == 150
    assert ctx.latency_ms == 350.0
    assert ctx.cost_usd == resp.cost_usd
    assert ctx.status == HookStatus.OK


def test_context_record_fallback():
    ctx = HookContext(hook_name="moderate", model="sonnet")
    ctx.record_fallback("skip", reason="timeout")

    assert ctx.used_fallback is True
    assert ctx.fallback_strategy == "skip"
    assert ctx.fallback_reason == "timeout"
    assert ctx.status == HookStatus.FALLBACK


def test_context_record_error():
    ctx = HookContext(hook_name="moderate", model="sonnet")
    ctx.record_error(ValueError("bad input"))

    assert ctx.status == HookStatus.ERROR
    assert ctx.error == "bad input"


def test_context_to_dict():
    ctx = HookContext(hook_name="moderate", model="sonnet")
    d = ctx.to_dict()
    assert d["hook_name"] == "moderate"
    assert d["model"] == "sonnet"
    assert "status" in d
    assert "cost_usd" in d
