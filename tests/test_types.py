from claudehooks.types import FallbackStrategy, HookStatus, HookConfig


def test_fallback_strategy_values():
    assert FallbackStrategy.SKIP.value == "skip"
    assert FallbackStrategy.DEFAULT.value == "default"
    assert FallbackStrategy.RAISE.value == "raise"
    assert FallbackStrategy.LOCAL.value == "local"
    assert FallbackStrategy.CACHE.value == "cache"
    assert FallbackStrategy.CASCADE.value == "cascade"


def test_hook_status_values():
    assert HookStatus.OK.value == "ok"
    assert HookStatus.FALLBACK.value == "fallback"
    assert HookStatus.ERROR.value == "error"
    assert HookStatus.TIMEOUT.value == "timeout"


def test_hook_config_defaults():
    config = HookConfig(name="test_hook")
    assert config.name == "test_hook"
    assert config.model is None
    assert config.timeout_seconds is None
    assert config.fallback == FallbackStrategy.SKIP
    assert config.system_prompt is None
    assert config.default_response is None
    assert config.max_retries == 1


def test_hook_config_custom():
    config = HookConfig(
        name="moderate",
        model="sonnet",
        timeout_seconds=5.0,
        fallback=FallbackStrategy.RAISE,
        max_retries=2,
    )
    assert config.model == "sonnet"
    assert config.timeout_seconds == 5.0
    assert config.fallback == FallbackStrategy.RAISE
    assert config.max_retries == 2
