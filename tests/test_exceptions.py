from claude_hooks.exceptions import (
    HookError,
    HookTimeoutError,
    HookBudgetError,
    HookValidationError,
    HookProviderError,
)


def test_hook_error_is_base():
    err = HookError("something broke")
    assert isinstance(err, Exception)
    assert str(err) == "something broke"


def test_timeout_error_inherits_hook_error():
    err = HookTimeoutError("too slow", timeout_seconds=5.0)
    assert isinstance(err, HookError)
    assert err.timeout_seconds == 5.0


def test_budget_error_inherits_hook_error():
    err = HookBudgetError("over budget", hook_name="moderate", limit=100, current=105)
    assert isinstance(err, HookError)
    assert err.hook_name == "moderate"
    assert err.limit == 100
    assert err.current == 105


def test_validation_error_inherits_hook_error():
    err = HookValidationError("bad output", raw_response='{"garbage": true}')
    assert isinstance(err, HookError)
    assert err.raw_response == '{"garbage": true}'


def test_provider_error_inherits_hook_error():
    err = HookProviderError("API down", provider="claude")
    assert isinstance(err, HookError)
    assert err.provider == "claude"
