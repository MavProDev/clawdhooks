# claude-hooks Phase 1: Core SDK — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working `claude-hooks` SDK that lets any Python developer add Claude as middleware to existing applications with a single decorator — typed input/output, automatic fallbacks, sync+async support.

**Architecture:** Three primitives — `@hook` decorator (turns a function into a Claude decision point), `HookRouter` (registry that manages provider, config, and stats), and `HookContext` (runtime metadata). A `LLMProvider` abstraction keeps Claude as default but allows future providers (OpenAI). Pydantic models define input/output schemas. Docstrings become system prompts. Function bodies become local fallbacks.

**Tech Stack:** Python 3.11+, Pydantic 2.x, anthropic SDK, pytest + pytest-asyncio, asyncio

---

## File Structure

```
ClawdHooks/
  src/
    clawd_hooks/
      __init__.py          # Public API: hook, HookRouter, HookContext
      exceptions.py        # HookError, HookTimeoutError, HookValidationError, HookProviderError
      types.py             # FallbackStrategy enum, HookStatus enum, HookConfig dataclass
      providers/
        __init__.py         # Re-export LLMProvider, LLMResponse
        base.py             # LLMProvider ABC, LLMResponse dataclass
        claude.py           # ClaudeProvider — Anthropic SDK wrapper
      context.py            # HookContext — runtime metadata per invocation
      fallbacks.py          # FallbackHandler — skip, default, raise, local strategies
      router.py             # HookRouter — registry, config, stats, decorator factory
      hook.py               # @hook decorator — schema extraction, prompt assembly, lifecycle
  tests/
    __init__.py
    conftest.py             # MockProvider, fixtures, helpers
    test_exceptions.py
    test_types.py
    test_provider_base.py
    test_provider_claude.py
    test_context.py
    test_fallbacks.py
    test_router.py
    test_hook.py
    test_integration.py
  examples/
    content_moderation.py   # Complete working example
  pyproject.toml
  LICENSE
  .gitignore
  README.md
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `src/clawd_hooks/__init__.py` (empty placeholder)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Initialize git repository**

Run:
```bash
cd "C:/Users/reeld/OneDrive/Desktop/Claude Projects/ClawdHooks"
git init
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "claude-hooks"
version = "0.1.0"
description = "Add Claude as middleware to any Python app with a single decorator"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "MavPro Group LLC" },
]
keywords = ["claude", "anthropic", "llm", "middleware", "decorator", "ai"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = [
    "anthropic>=0.40.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.5",
]
pii = [
    "presidio-analyzer>=2.2",
    "presidio-anonymizer>=2.2",
]

[project.urls]
Homepage = "https://github.com/mavprogroup/claude-hooks"
Documentation = "https://github.com/mavprogroup/claude-hooks#readme"
Repository = "https://github.com/mavprogroup/claude-hooks"
Issues = "https://github.com/mavprogroup/claude-hooks/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/clawd_hooks"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py311"
line-length = 100
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
env/
.env
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/
*.log
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Create LICENSE**

```
MIT License

Copyright (c) 2026 MavPro Group LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 5: Create placeholder files and directory structure**

```bash
mkdir -p src/clawd_hooks/providers tests examples
touch src/clawd_hooks/__init__.py
touch src/clawd_hooks/providers/__init__.py
touch tests/__init__.py
```

- [ ] **Step 6: Create virtual environment and install dev dependencies**

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"
```

- [ ] **Step 7: Verify pytest runs (no tests yet)**

Run: `pytest -v`
Expected: "no tests ran" with exit code 5 (no tests collected — that's correct)

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore LICENSE src/ tests/ examples/ docs/
git commit -m "chore: initialize claude-hooks project scaffold"
```

---

## Task 2: Exceptions

**Files:**
- Create: `src/clawd_hooks/exceptions.py`
- Create: `tests/test_exceptions.py`

- [ ] **Step 1: Write test for exceptions**

```python
# tests/test_exceptions.py
from clawd_hooks.exceptions import (
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clawd_hooks.exceptions'`

- [ ] **Step 3: Implement exceptions**

```python
# src/clawd_hooks/exceptions.py
"""Custom exceptions for claude-hooks."""


class HookError(Exception):
    """Base exception for all claude-hooks errors."""


class HookTimeoutError(HookError):
    """Raised when a hook call exceeds its timeout."""

    def __init__(self, message: str, *, timeout_seconds: float):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class HookBudgetError(HookError):
    """Raised when a hook exceeds its budget limit."""

    def __init__(self, message: str, *, hook_name: str, limit: int, current: int):
        super().__init__(message)
        self.hook_name = hook_name
        self.limit = limit
        self.current = current


class HookValidationError(HookError):
    """Raised when Claude's response fails output schema validation."""

    def __init__(self, message: str, *, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


class HookProviderError(HookError):
    """Raised when the LLM provider encounters an error."""

    def __init__(self, message: str, *, provider: str):
        super().__init__(message)
        self.provider = provider
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exceptions.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/clawd_hooks/exceptions.py tests/test_exceptions.py
git commit -m "feat: add custom exception hierarchy"
```

---

## Task 3: Types & Enums

**Files:**
- Create: `src/clawd_hooks/types.py`
- Create: `tests/test_types.py`

- [ ] **Step 1: Write test for types**

```python
# tests/test_types.py
from clawd_hooks.types import FallbackStrategy, HookStatus, HookConfig


def test_fallback_strategy_values():
    assert FallbackStrategy.SKIP.value == "skip"
    assert FallbackStrategy.DEFAULT.value == "default"
    assert FallbackStrategy.RAISE.value == "raise"
    assert FallbackStrategy.LOCAL.value == "local"


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clawd_hooks.types'`

- [ ] **Step 3: Implement types**

```python
# src/clawd_hooks/types.py
"""Shared types and configuration for claude-hooks."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FallbackStrategy(Enum):
    """What to do when Claude is unavailable, slow, or over budget."""

    SKIP = "skip"        # Return None — caller decides
    DEFAULT = "default"  # Return a pre-defined default response
    RAISE = "raise"      # Raise the exception — pipeline must halt
    LOCAL = "local"      # Run the original function body as fallback


class HookStatus(Enum):
    """Outcome of a hook invocation."""

    OK = "ok"            # Claude responded successfully
    FALLBACK = "fallback"  # Fallback was used
    ERROR = "error"      # Unrecoverable error
    TIMEOUT = "timeout"  # Claude timed out


@dataclass
class HookConfig:
    """Configuration for a single hook."""

    name: str
    model: str | None = None
    timeout_seconds: float | None = None
    fallback: FallbackStrategy = FallbackStrategy.SKIP
    system_prompt: str | None = None
    default_response: Any = None
    max_retries: int = 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_types.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/clawd_hooks/types.py tests/test_types.py
git commit -m "feat: add types, enums, and HookConfig"
```

---

## Task 4: Provider Abstraction

**Files:**
- Create: `src/clawd_hooks/providers/base.py`
- Modify: `src/clawd_hooks/providers/__init__.py`
- Create: `tests/test_provider_base.py`

- [ ] **Step 1: Write test for provider base**

```python
# tests/test_provider_base.py
import pytest
from clawd_hooks.providers.base import LLMProvider, LLMResponse


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_provider_base.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement provider base**

```python
# src/clawd_hooks/providers/base.py
"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Update providers __init__.py**

```python
# src/clawd_hooks/providers/__init__.py
"""LLM provider abstractions."""
from .base import LLMProvider, LLMResponse

__all__ = ["LLMProvider", "LLMResponse"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_provider_base.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/clawd_hooks/providers/ tests/test_provider_base.py
git commit -m "feat: add LLMProvider abstraction and LLMResponse"
```

---

## Task 5: Claude Provider

**Files:**
- Create: `src/clawd_hooks/providers/claude.py`
- Modify: `src/clawd_hooks/providers/__init__.py`
- Create: `tests/test_provider_claude.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create conftest with shared fixtures**

```python
# tests/conftest.py
"""Shared test fixtures for claude-hooks."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from clawd_hooks.providers.base import LLMProvider, LLMResponse


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
```

- [ ] **Step 2: Write test for Claude provider**

```python
# tests/test_provider_claude.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from clawd_hooks.providers.claude import ClaudeProvider, MODEL_ALIASES, MODEL_PRICING


def test_model_aliases():
    assert "haiku" in MODEL_ALIASES
    assert "sonnet" in MODEL_ALIASES
    assert "opus" in MODEL_ALIASES


def test_provider_name():
    with patch("clawd_hooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert provider.name == "claude"


def test_default_model():
    with patch("clawd_hooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert "sonnet" in provider.default_model()


def test_resolve_model_alias():
    with patch("clawd_hooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert provider.resolve_model("haiku") == MODEL_ALIASES["haiku"]
    assert provider.resolve_model("sonnet") == MODEL_ALIASES["sonnet"]
    assert provider.resolve_model("opus") == MODEL_ALIASES["opus"]


def test_resolve_model_passthrough():
    with patch("clawd_hooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    full_id = "claude-sonnet-4-6"
    assert provider.resolve_model(full_id) == full_id


def test_model_timeout_defaults():
    with patch("clawd_hooks.providers.claude.anthropic"):
        provider = ClaudeProvider(api_key="test-key")
    assert provider.model_timeout("haiku") == 5.0
    assert provider.model_timeout("sonnet") == 10.0
    assert provider.model_timeout("opus") == 30.0
    assert provider.model_timeout("unknown-model") == 10.0


@pytest.mark.asyncio
async def test_complete_sends_correct_request(mock_anthropic_client):
    with patch("clawd_hooks.providers.claude.anthropic") as mock_anthropic:
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
    # Response with no tool_use block
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I can't do that"

    mock_anthropic_client.messages.create.return_value.content = [text_block]

    with patch("clawd_hooks.providers.claude.anthropic") as mock_anthropic:
        mock_anthropic.AsyncAnthropic.return_value = mock_anthropic_client
        provider = ClaudeProvider(api_key="test-key")
    provider._client = mock_anthropic_client

    from clawd_hooks.exceptions import HookProviderError

    with pytest.raises(HookProviderError, match="No structured response"):
        await provider.complete(
            system_prompt="test",
            user_message="test",
            output_schema={"type": "object"},
            model="sonnet",
            timeout_seconds=10.0,
        )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_provider_claude.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clawd_hooks.providers.claude'`

- [ ] **Step 4: Implement Claude provider**

```python
# src/clawd_hooks/providers/claude.py
"""Claude/Anthropic LLM provider."""
from __future__ import annotations

import json
import time
from typing import Any

import anthropic

from .base import LLMProvider, LLMResponse
from ..exceptions import HookProviderError

MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

MODEL_TIMEOUTS: dict[str, float] = {
    "haiku": 5.0,
    "sonnet": 10.0,
    "opus": 30.0,
}

MODEL_PRICING: dict[str, tuple[float, float]] = {
    # (input $/MTok, output $/MTok)
    "haiku": (1.0, 5.0),
    "sonnet": (3.0, 15.0),
    "opus": (5.0, 25.0),
}


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider using the official SDK."""

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "claude"

    def default_model(self) -> str:
        return MODEL_ALIASES["sonnet"]

    def resolve_model(self, model: str) -> str:
        """Resolve a model alias (e.g., 'sonnet') to a full model ID."""
        return MODEL_ALIASES.get(model, model)

    def model_timeout(self, model: str) -> float:
        """Return recommended timeout for the given model."""
        # Check alias first, then full model ID
        if model in MODEL_TIMEOUTS:
            return MODEL_TIMEOUTS[model]
        # Check if it's a full model ID matching an alias
        for alias, full_id in MODEL_ALIASES.items():
            if model == full_id:
                return MODEL_TIMEOUTS[alias]
        return 10.0  # sensible default

    def _get_pricing(self, model: str) -> tuple[float, float]:
        """Get (input, output) cost per MTok for a model."""
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]
        for alias, full_id in MODEL_ALIASES.items():
            if model == full_id:
                return MODEL_PRICING.get(alias, (0.0, 0.0))
        return (0.0, 0.0)

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
        resolved_model = self.resolve_model(model)

        tools = [
            {
                "name": "structured_response",
                "description": "Return the structured response matching the required schema.",
                "input_schema": output_schema,
            }
        ]

        start = time.monotonic()
        response = await self._client.messages.create(
            model=resolved_model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
            tools=tools,
            tool_choice={"type": "tool", "name": "structured_response"},
        )
        latency_ms = (time.monotonic() - start) * 1000

        # Extract tool_use block
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use_block is None:
            raise HookProviderError(
                "No structured response in Claude's response", provider=self.name
            )

        input_pricing, output_pricing = self._get_pricing(model)

        return LLMResponse(
            content=tool_use_block.input,
            raw_text=json.dumps(tool_use_block.input),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            cached_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            latency_ms=latency_ms,
            input_cost_per_mtok=input_pricing,
            output_cost_per_mtok=output_pricing,
        )
```

- [ ] **Step 5: Update providers __init__.py**

```python
# src/clawd_hooks/providers/__init__.py
"""LLM provider abstractions."""
from .base import LLMProvider, LLMResponse
from .claude import ClaudeProvider

__all__ = ["LLMProvider", "LLMResponse", "ClaudeProvider"]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_provider_claude.py -v`
Expected: 8 passed

- [ ] **Step 7: Commit**

```bash
git add src/clawd_hooks/providers/ tests/test_provider_claude.py tests/conftest.py
git commit -m "feat: add ClaudeProvider with tool_use structured output"
```

---

## Task 6: HookContext

**Files:**
- Create: `src/clawd_hooks/context.py`
- Create: `tests/test_context.py`

- [ ] **Step 1: Write test for HookContext**

```python
# tests/test_context.py
import time
import pytest
from clawd_hooks.context import HookContext
from clawd_hooks.types import HookStatus


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement HookContext**

```python
# src/clawd_hooks/context.py
"""Runtime context for hook invocations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .providers.base import LLMResponse
from .types import HookStatus


@dataclass
class HookContext:
    """Carries runtime metadata for a single hook invocation."""

    hook_name: str
    model: str
    status: HookStatus = HookStatus.OK
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    retries: int = 0
    used_fallback: bool = False
    fallback_strategy: str | None = None
    fallback_reason: str | None = None
    error: str | None = None

    def record_response(self, response: LLMResponse) -> None:
        """Record metrics from a successful LLM response."""
        self.input_tokens = response.input_tokens
        self.output_tokens = response.output_tokens
        self.cached_input_tokens = response.cached_input_tokens
        self.latency_ms = response.latency_ms
        self.cost_usd = response.cost_usd
        self.status = HookStatus.OK

    def record_fallback(self, strategy: str, *, reason: str) -> None:
        """Record that a fallback was used."""
        self.used_fallback = True
        self.fallback_strategy = strategy
        self.fallback_reason = reason
        self.status = HookStatus.FALLBACK

    def record_error(self, error: Exception) -> None:
        """Record an unrecoverable error."""
        self.status = HookStatus.ERROR
        self.error = str(error)

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to a dictionary."""
        return {
            "hook_name": self.hook_name,
            "model": self.model,
            "status": self.status.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "retries": self.retries,
            "used_fallback": self.used_fallback,
            "fallback_strategy": self.fallback_strategy,
            "fallback_reason": self.fallback_reason,
            "error": self.error,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/clawd_hooks/context.py tests/test_context.py
git commit -m "feat: add HookContext for runtime invocation metadata"
```

---

## Task 7: Fallback Strategies

**Files:**
- Create: `src/clawd_hooks/fallbacks.py`
- Create: `tests/test_fallbacks.py`

- [ ] **Step 1: Write test for fallbacks**

```python
# tests/test_fallbacks.py
import pytest
from pydantic import BaseModel
from clawd_hooks.fallbacks import resolve_fallback
from clawd_hooks.types import FallbackStrategy
from clawd_hooks.exceptions import HookTimeoutError, HookProviderError


class MockOutput(BaseModel):
    action: str
    reason: str


def test_skip_returns_none():
    result = resolve_fallback(
        strategy=FallbackStrategy.SKIP,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=None,
        args=(),
        kwargs={},
        default_response=None,
    )
    assert result is None


def test_default_returns_configured_value():
    default = MockOutput(action="allow", reason="default")
    result = resolve_fallback(
        strategy=FallbackStrategy.DEFAULT,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=None,
        args=(),
        kwargs={},
        default_response=default,
    )
    assert result == default
    assert result.action == "allow"


def test_default_raises_if_no_default_configured():
    with pytest.raises(ValueError, match="No default_response configured"):
        resolve_fallback(
            strategy=FallbackStrategy.DEFAULT,
            error=HookTimeoutError("timeout", timeout_seconds=5.0),
            original_func=None,
            args=(),
            kwargs={},
            default_response=None,
        )


def test_raise_reraises_original_error():
    original_error = HookProviderError("API down", provider="claude")
    with pytest.raises(HookProviderError, match="API down"):
        resolve_fallback(
            strategy=FallbackStrategy.RAISE,
            error=original_error,
            original_func=None,
            args=(),
            kwargs={},
            default_response=None,
        )


def test_local_calls_original_function():
    def my_fallback(text: str) -> MockOutput:
        return MockOutput(action="allow", reason="local fallback")

    result = resolve_fallback(
        strategy=FallbackStrategy.LOCAL,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=my_fallback,
        args=("hello",),
        kwargs={},
        default_response=None,
    )
    assert result.action == "allow"
    assert result.reason == "local fallback"


def test_local_returns_none_if_func_is_stub():
    def stub_func(text: str):
        ...

    result = resolve_fallback(
        strategy=FallbackStrategy.LOCAL,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=stub_func,
        args=("hello",),
        kwargs={},
        default_response=None,
    )
    assert result is None


@pytest.mark.asyncio
async def test_local_handles_async_fallback():
    from clawd_hooks.fallbacks import resolve_fallback_async

    async def async_fallback(text: str) -> MockOutput:
        return MockOutput(action="allow", reason="async local")

    result = await resolve_fallback_async(
        strategy=FallbackStrategy.LOCAL,
        error=HookTimeoutError("timeout", timeout_seconds=5.0),
        original_func=async_fallback,
        args=("hello",),
        kwargs={},
        default_response=None,
    )
    assert result.action == "allow"
    assert result.reason == "async local"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fallbacks.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement fallbacks**

```python
# src/clawd_hooks/fallbacks.py
"""Fallback strategies for when Claude is unavailable."""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable

from .types import FallbackStrategy


def resolve_fallback(
    *,
    strategy: FallbackStrategy,
    error: Exception,
    original_func: Callable | None,
    args: tuple,
    kwargs: dict,
    default_response: Any,
) -> Any:
    """Resolve a fallback synchronously. Returns the fallback value or raises."""
    if strategy == FallbackStrategy.SKIP:
        return None

    if strategy == FallbackStrategy.DEFAULT:
        if default_response is None:
            raise ValueError(
                f"No default_response configured for fallback. Original error: {error}"
            )
        return default_response

    if strategy == FallbackStrategy.RAISE:
        raise error

    if strategy == FallbackStrategy.LOCAL:
        if original_func is None:
            return None
        return original_func(*args, **kwargs)

    raise ValueError(f"Unknown fallback strategy: {strategy}")


async def resolve_fallback_async(
    *,
    strategy: FallbackStrategy,
    error: Exception,
    original_func: Callable | None,
    args: tuple,
    kwargs: dict,
    default_response: Any,
) -> Any:
    """Resolve a fallback, handling both sync and async original functions."""
    if strategy == FallbackStrategy.SKIP:
        return None

    if strategy == FallbackStrategy.DEFAULT:
        if default_response is None:
            raise ValueError(
                f"No default_response configured for fallback. Original error: {error}"
            )
        return default_response

    if strategy == FallbackStrategy.RAISE:
        raise error

    if strategy == FallbackStrategy.LOCAL:
        if original_func is None:
            return None
        result = original_func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    raise ValueError(f"Unknown fallback strategy: {strategy}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fallbacks.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/clawd_hooks/fallbacks.py tests/test_fallbacks.py
git commit -m "feat: add fallback strategies (skip, default, raise, local)"
```

---

## Task 8: HookRouter

**Files:**
- Create: `src/clawd_hooks/router.py`
- Create: `tests/test_router.py`

- [ ] **Step 1: Write test for HookRouter**

```python
# tests/test_router.py
import pytest
from pydantic import BaseModel
from clawd_hooks.router import HookRouter
from clawd_hooks.providers.base import LLMResponse
from clawd_hooks.types import FallbackStrategy


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float


def test_router_creation_with_provider(mock_provider):
    router = HookRouter(provider=mock_provider)
    assert router.provider.name == "mock"


def test_router_creation_with_api_key():
    # This just tests that the parameter is accepted — real API key not needed for test
    # The ClaudeProvider import happens internally
    with pytest.raises(Exception):
        # Will fail because anthropic client can't connect with fake key
        # but the router itself should be constructable
        router = HookRouter(api_key="sk-test-fake-key")


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_router.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement HookRouter**

```python
# src/clawd_hooks/router.py
"""HookRouter — central registry for all hooks."""
from __future__ import annotations

import functools
import inspect
import json
import asyncio
import threading
from typing import Any, Callable, TypeVar, get_type_hints

from pydantic import BaseModel

from .providers.base import LLMProvider, LLMResponse
from .context import HookContext
from .types import FallbackStrategy, HookConfig, HookStatus
from .fallbacks import resolve_fallback_async
from .exceptions import (
    HookError,
    HookTimeoutError,
    HookValidationError,
    HookProviderError,
)

T = TypeVar("T")


def _is_stub(func: Callable) -> bool:
    """Check if a function body is just ... or pass (returns None with no side effects)."""
    source_lines = []
    try:
        source = inspect.getsource(func)
        lines = source.strip().split("\n")
        # Skip decorator lines, def line, and docstring
        in_body = False
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if not in_body:
                if stripped.startswith("def ") or stripped.startswith("async def "):
                    in_body = True
                continue
            # Skip docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if in_docstring:
                    in_docstring = False
                    continue
                if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                    continue  # single-line docstring
                in_docstring = True
                continue
            if in_docstring:
                continue
            source_lines.append(stripped)

        body = " ".join(source_lines).strip()
        return body in ("...", "pass", "")
    except (OSError, TypeError):
        return True  # Can't inspect source — assume stub


def _serialize_input(func: Callable, args: tuple, kwargs: dict) -> str:
    """Serialize function arguments to a JSON string for the LLM."""
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    params = dict(bound.arguments)

    # Single Pydantic model param — serialize directly
    if len(params) == 1:
        value = next(iter(params.values()))
        if isinstance(value, BaseModel):
            return value.model_dump_json()

    # Multiple params — serialize as dict
    serialized = {}
    for key, value in params.items():
        if isinstance(value, BaseModel):
            serialized[key] = value.model_dump()
        elif hasattr(value, "__dict__"):
            serialized[key] = str(value)
        else:
            serialized[key] = value

    return json.dumps(serialized, default=str)


def _get_output_schema(func: Callable) -> tuple[type[BaseModel] | None, dict[str, Any]]:
    """Extract the output Pydantic model and its JSON schema from return type hint."""
    hints = get_type_hints(func)
    return_type = hints.get("return")

    if return_type is None:
        raise TypeError(f"Hook '{func.__name__}' must have a return type annotation (Pydantic model)")

    if not (isinstance(return_type, type) and issubclass(return_type, BaseModel)):
        raise TypeError(
            f"Hook '{func.__name__}' return type must be a Pydantic BaseModel, got {return_type}"
        )

    return return_type, return_type.model_json_schema()


def _run_sync(coro):
    """Run an async coroutine synchronously."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Event loop already running — run in a thread
    result_container = {}

    def _run():
        try:
            result_container["result"] = asyncio.run(coro)
        except Exception as e:
            result_container["error"] = e

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()

    if "error" in result_container:
        raise result_container["error"]
    return result_container["result"]


class HookRouter:
    """Central registry that manages all hooks, providers, and stats."""

    def __init__(
        self,
        *,
        provider: LLMProvider | None = None,
        api_key: str | None = None,
    ):
        if provider is not None:
            self._provider = provider
        elif api_key is not None:
            from .providers.claude import ClaudeProvider
            self._provider = ClaudeProvider(api_key=api_key)
        else:
            raise ValueError("Provide either a 'provider' instance or an 'api_key' for Claude.")

        self._hooks: dict[str, HookConfig] = {}
        self._stats: dict[str, list[HookContext]] = {}

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def hooks(self) -> dict[str, HookConfig]:
        return self._hooks

    def hook(
        self,
        *,
        model: str | None = None,
        timeout_seconds: float | None = None,
        fallback: str = "skip",
        system_prompt: str | None = None,
        default_response: Any = None,
        max_retries: int = 1,
    ) -> Callable:
        """Decorator that registers a function as a Claude hook."""
        fallback_strategy = FallbackStrategy(fallback)

        def decorator(func: Callable) -> Callable:
            # Extract output schema
            output_model, output_schema = _get_output_schema(func)

            # Determine system prompt: explicit param > docstring
            prompt = system_prompt or (inspect.getdoc(func) or "")
            if not prompt:
                raise ValueError(
                    f"Hook '{func.__name__}' needs a system prompt. "
                    "Add a docstring or pass system_prompt=..."
                )

            # Determine if original func is a stub
            is_stub = _is_stub(func)
            original_func = None if is_stub else func

            # Register config
            config = HookConfig(
                name=func.__name__,
                model=model,
                timeout_seconds=timeout_seconds,
                fallback=fallback_strategy,
                system_prompt=prompt,
                default_response=default_response,
                max_retries=max_retries,
            )
            self._hooks[func.__name__] = config

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_hook(
                    config=config,
                    output_model=output_model,
                    output_schema=output_schema,
                    original_func=original_func,
                    args=args,
                    kwargs=kwargs,
                    bound_func=func,
                )

            # Add sync convenience method
            async_wrapper.sync = lambda *a, **kw: _run_sync(async_wrapper(*a, **kw))

            # Store metadata on the wrapper for introspection
            async_wrapper.hook_config = config
            async_wrapper.output_model = output_model

            return async_wrapper

        return decorator

    async def _execute_hook(
        self,
        *,
        config: HookConfig,
        output_model: type[BaseModel],
        output_schema: dict[str, Any],
        original_func: Callable | None,
        args: tuple,
        kwargs: dict,
        bound_func: Callable,
    ) -> Any:
        """Execute the full hook lifecycle: call Claude, validate, fallback."""
        ctx = HookContext(
            hook_name=config.name,
            model=config.model or self._provider.default_model(),
        )

        resolved_model = config.model or self._provider.default_model()
        timeout = config.timeout_seconds or self._provider.model_timeout(resolved_model)

        # Serialize input
        user_message = _serialize_input(bound_func, args, kwargs)

        last_error: Exception | None = None
        attempts = 1 + config.max_retries

        for attempt in range(attempts):
            try:
                response = await asyncio.wait_for(
                    self._provider.complete(
                        system_prompt=config.system_prompt,
                        user_message=user_message,
                        output_schema=output_schema,
                        model=resolved_model,
                        timeout_seconds=timeout,
                    ),
                    timeout=timeout,
                )
                ctx.record_response(response)

                # Validate response against Pydantic model
                try:
                    result = output_model.model_validate(response.content)
                except Exception as validation_err:
                    if attempt < attempts - 1:
                        ctx.retries += 1
                        last_error = HookValidationError(
                            str(validation_err), raw_response=response.raw_text
                        )
                        continue
                    raise HookValidationError(
                        str(validation_err), raw_response=response.raw_text
                    ) from validation_err

                self._record_stats(ctx)
                return result

            except asyncio.TimeoutError:
                last_error = HookTimeoutError(
                    f"Hook '{config.name}' timed out after {timeout}s",
                    timeout_seconds=timeout,
                )
                if attempt < attempts - 1:
                    ctx.retries += 1
                    continue

            except HookValidationError:
                raise  # Already handled above

            except HookError:
                last_error = last_error  # Already a hook error
                if attempt < attempts - 1:
                    ctx.retries += 1
                    continue

            except Exception as e:
                last_error = HookProviderError(str(e), provider=self._provider.name)
                if attempt < attempts - 1:
                    ctx.retries += 1
                    continue

        # All attempts failed — use fallback
        ctx.record_fallback(config.fallback.value, reason=str(last_error))
        self._record_stats(ctx)

        return await resolve_fallback_async(
            strategy=config.fallback,
            error=last_error,
            original_func=original_func,
            args=args,
            kwargs=kwargs,
            default_response=config.default_response,
        )

    def _record_stats(self, ctx: HookContext) -> None:
        """Record a hook invocation in stats."""
        if ctx.hook_name not in self._stats:
            self._stats[ctx.hook_name] = []
        self._stats[ctx.hook_name].append(ctx)

    def stats(self) -> dict[str, Any]:
        """Return aggregated stats across all hooks."""
        total_calls = 0
        total_cost = 0.0
        total_input = 0
        total_output = 0
        hook_stats = {}

        for hook_name, contexts in self._stats.items():
            calls = len(contexts)
            cost = sum(c.cost_usd for c in contexts)
            inp = sum(c.input_tokens for c in contexts)
            out = sum(c.output_tokens for c in contexts)
            fallbacks = sum(1 for c in contexts if c.used_fallback)

            total_calls += calls
            total_cost += cost
            total_input += inp
            total_output += out

            hook_stats[hook_name] = {
                "calls": calls,
                "cost_usd": cost,
                "input_tokens": inp,
                "output_tokens": out,
                "fallbacks": fallbacks,
                "avg_latency_ms": (
                    sum(c.latency_ms for c in contexts) / calls if calls else 0
                ),
            }

        return {
            "total_calls": total_calls,
            "total_cost_usd": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "hooks": hook_stats,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_router.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/clawd_hooks/router.py tests/test_router.py
git commit -m "feat: add HookRouter with registration, lifecycle, and stats"
```

---

## Task 9: @hook Decorator End-to-End Tests

**Files:**
- Create: `tests/test_hook.py`

This task tests the full decorator flow with the MockProvider — no API calls.

- [ ] **Step 1: Write end-to-end hook tests**

```python
# tests/test_hook.py
import pytest
from pydantic import BaseModel
from clawd_hooks.router import HookRouter
from clawd_hooks.providers.base import LLMResponse
from clawd_hooks.types import FallbackStrategy
from clawd_hooks.exceptions import HookTimeoutError, HookProviderError


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
    assert call["system_prompt"] == "Evaluate this post against community guidelines."
    assert '"title": "Hello"' in call["user_message"]


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

    @router.hook(model="sonnet", fallback="raise")
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
    assert call["system_prompt"] == "You are extremely strict. Block everything."


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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_hook.py -v`
Expected: 12 passed (these test the router+decorator from Task 8 — all implementation is already done)

If any fail, debug and fix the router code. Common issues:
- `_is_stub` may need adjustment for test functions defined inline
- Async fallback handling edge cases

- [ ] **Step 3: Commit**

```bash
git add tests/test_hook.py
git commit -m "test: add comprehensive hook decorator tests"
```

---

## Task 10: Public API & Integration Test

**Files:**
- Modify: `src/clawd_hooks/__init__.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""Integration test: end-to-end hook lifecycle with MockProvider."""
import pytest
from pydantic import BaseModel
from clawd_hooks import HookRouter, HookContext
from clawd_hooks.providers.base import LLMResponse
from clawd_hooks.exceptions import HookError, HookTimeoutError


class SupportTicket(BaseModel):
    subject: str
    body: str
    sender: str


class TriageResult(BaseModel):
    urgency: str
    category: str
    suggested_response: str


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float


@pytest.mark.asyncio
async def test_full_lifecycle_success(mock_provider, make_response):
    """Test the complete happy path: register hook, call it, get typed result."""
    mock_provider._responses = [
        make_response(
            content={
                "urgency": "high",
                "category": "billing",
                "suggested_response": "Escalate to billing team immediately.",
            },
            input_tokens=300,
            output_tokens=100,
            input_cost_per_mtok=3.0,
            output_cost_per_mtok=15.0,
        )
    ]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def triage_ticket(ticket: SupportTicket) -> TriageResult:
        """You are a support ticket triage system. Classify the ticket by urgency
        (low/medium/high), category, and suggest a response."""
        ...

    ticket = SupportTicket(
        subject="Charged twice",
        body="I was charged twice for my subscription this month.",
        sender="angry_customer@example.com",
    )

    result = await triage_ticket(ticket)

    # Typed result
    assert isinstance(result, TriageResult)
    assert result.urgency == "high"
    assert result.category == "billing"

    # Stats recorded
    stats = router.stats()
    assert stats["total_calls"] == 1
    assert stats["total_cost_usd"] > 0
    assert stats["hooks"]["triage_ticket"]["calls"] == 1


@pytest.mark.asyncio
async def test_multiple_hooks_independent_stats(mock_provider, make_response):
    """Test that multiple hooks track stats independently."""
    mock_provider._responses = [
        make_response(content={"sentiment": "positive", "confidence": 0.95}),
        make_response(
            content={
                "urgency": "low",
                "category": "general",
                "suggested_response": "Standard reply.",
            }
        ),
        make_response(content={"sentiment": "negative", "confidence": 0.87}),
    ]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="haiku")
    async def analyze_sentiment(text: str) -> SentimentResult:
        """Analyze the sentiment of this text."""
        ...

    @router.hook(model="sonnet")
    async def triage(ticket: SupportTicket) -> TriageResult:
        """Triage this support ticket."""
        ...

    await analyze_sentiment("Great product!")
    await triage(SupportTicket(subject="Hi", body="Question", sender="user@test.com"))
    await analyze_sentiment("Terrible service")

    stats = router.stats()
    assert stats["total_calls"] == 3
    assert stats["hooks"]["analyze_sentiment"]["calls"] == 2
    assert stats["hooks"]["triage"]["calls"] == 1


@pytest.mark.asyncio
async def test_fallback_with_local_function(mock_provider):
    """Test that a real function body serves as local fallback."""
    mock_provider._responses = [Exception("API down")]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", fallback="local")
    async def analyze_sentiment(text: str) -> SentimentResult:
        """Analyze sentiment."""
        # Simple keyword fallback
        if any(word in text.lower() for word in ["great", "good", "love"]):
            return SentimentResult(sentiment="positive", confidence=0.5)
        return SentimentResult(sentiment="neutral", confidence=0.3)

    result = await analyze_sentiment("Great product!")
    assert result.sentiment == "positive"
    assert result.confidence == 0.5

    stats = router.stats()
    assert stats["hooks"]["analyze_sentiment"]["fallbacks"] == 1


def test_sync_workflow(mock_provider, make_response):
    """Test the sync interface works without any async knowledge."""
    mock_provider._responses = [
        make_response(content={"sentiment": "positive", "confidence": 0.9})
    ]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="haiku")
    async def analyze(text: str) -> SentimentResult:
        """Analyze sentiment."""
        ...

    # User calls .sync() — no async/await needed
    result = analyze.sync("Hello world")
    assert isinstance(result, SentimentResult)
    assert result.sentiment == "positive"
```

- [ ] **Step 2: Implement public API**

```python
# src/clawd_hooks/__init__.py
"""claude-hooks: Add Claude as middleware to any Python app with a single decorator."""
from .router import HookRouter
from .context import HookContext
from .types import FallbackStrategy, HookConfig, HookStatus
from .providers.base import LLMProvider, LLMResponse
from .providers.claude import ClaudeProvider
from .exceptions import (
    HookError,
    HookTimeoutError,
    HookBudgetError,
    HookValidationError,
    HookProviderError,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "HookRouter",
    "HookContext",
    # Types
    "FallbackStrategy",
    "HookConfig",
    "HookStatus",
    # Providers
    "LLMProvider",
    "LLMResponse",
    "ClaudeProvider",
    # Exceptions
    "HookError",
    "HookTimeoutError",
    "HookBudgetError",
    "HookValidationError",
    "HookProviderError",
]
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: 4 passed

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass (exceptions, types, provider, context, fallbacks, router, hook, integration)

- [ ] **Step 5: Commit**

```bash
git add src/clawd_hooks/__init__.py tests/test_integration.py
git commit -m "feat: wire up public API and add integration tests"
```

---

## Task 11: Example Application & README

**Files:**
- Create: `examples/content_moderation.py`
- Create: `README.md`

- [ ] **Step 1: Create working example**

```python
# examples/content_moderation.py
"""
Content Moderation Example
==========================

Demonstrates claude-hooks as middleware for moderating user-generated content.
Claude evaluates each post and returns allow/flag/block with reasoning.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/content_moderation.py
"""
import asyncio
import os

from pydantic import BaseModel

from clawd_hooks import HookRouter


# --- Schemas ---

class UserPost(BaseModel):
    title: str
    content: str
    author: str


class ModerationResult(BaseModel):
    action: str  # "allow", "flag", or "block"
    reason: str
    confidence: float


# --- Setup ---

router = HookRouter(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# --- Hook ---

@router.hook(model="haiku", fallback="local")
async def moderate(post: UserPost) -> ModerationResult:
    """You are a content moderator for an online community.

    Evaluate the post against these guidelines:
    - No hate speech, harassment, or threats
    - No spam or commercial solicitation
    - No explicit or graphic content

    Return your decision:
    - action: "allow" (clean), "flag" (needs human review), or "block" (clear violation)
    - reason: Brief explanation of your decision
    - confidence: 0.0 to 1.0 how confident you are
    """
    # Local fallback: keyword-based filter when Claude is unavailable
    blocked_words = ["spam", "buy now", "click here"]
    if any(word in post.content.lower() for word in blocked_words):
        return ModerationResult(action="flag", reason="keyword match", confidence=0.3)
    return ModerationResult(action="allow", reason="no keywords matched", confidence=0.2)


# --- Main ---

async def main():
    posts = [
        UserPost(title="Hello!", content="Just saying hi to everyone.", author="newuser"),
        UserPost(title="Great community", content="Love this place!", author="regular"),
        UserPost(
            title="Check this out",
            content="Buy now! Amazing deal click here!!!",
            author="spammer",
        ),
    ]

    for post in posts:
        result = await moderate(post)
        print(f"[{result.action.upper()}] '{post.title}' by {post.author}")
        print(f"  Reason: {result.reason} (confidence: {result.confidence})")
        print()

    # Print stats
    stats = router.stats()
    print("--- Stats ---")
    print(f"Total calls: {stats['total_calls']}")
    print(f"Total cost:  ${stats['total_cost_usd']:.6f}")
    print(f"Tokens used: {stats['total_input_tokens']} in / {stats['total_output_tokens']} out")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Create README**

```markdown
# claude-hooks

**Add Claude to any Python app in one line.**

claude-hooks is a Python SDK for injecting Claude as middleware into existing applications. Not as a chatbot. Not as an agent. As a decision-making layer inside your code.

## Install

```bash
pip install claude-hooks
```

## Quick Start

```python
import os
from pydantic import BaseModel
from clawd_hooks import HookRouter

router = HookRouter(api_key=os.environ["ANTHROPIC_API_KEY"])

class ModerationResult(BaseModel):
    action: str    # "allow", "flag", or "block"
    reason: str

@router.hook(model="haiku", fallback="local")
async def moderate(content: str) -> ModerationResult:
    """Evaluate if this content violates community guidelines."""
    return ModerationResult(action="allow", reason="fallback")

# Async
result = await moderate("Hello world!")

# Sync (no async/await needed)
result = moderate.sync("Hello world!")
```

## How It Works

1. **Decorate** any function with `@router.hook()`
2. **Define** input (function params) and output (Pydantic return type)
3. **Write** the system prompt as the docstring
4. **Call** the function — Claude handles the rest

The function body is your **local fallback** — it runs when Claude is unavailable.

## Features

- **Typed I/O** — Pydantic models in, Pydantic models out. No JSON parsing.
- **Sync + Async** — `await moderate(post)` or `moderate.sync(post)`. Your choice.
- **Fallback strategies** — `skip`, `default`, `raise`, or `local` (your function body).
- **Auto retry** — Configurable retries on failure before falling back.
- **Cost tracking** — `router.stats()` shows tokens, cost, and latency per hook.
- **Prompt caching** — System prompts cached automatically (90% cost reduction).
- **Model routing** — Use `"haiku"` for fast/cheap, `"opus"` for high-stakes.

## Fallback Strategies

| Strategy | Behavior |
|----------|----------|
| `skip` | Returns `None`. Your code decides what to do. |
| `default` | Returns a pre-defined default response. |
| `raise` | Raises the error. Pipeline must halt. |
| `local` | Runs your function body as a fallback. |

```python
# "local" fallback — function body runs when Claude is down
@router.hook(model="sonnet", fallback="local")
async def classify(text: str) -> Classification:
    """Classify this text."""
    return Classification(label="unknown", confidence=0.0)  # fallback
```

## Stats

```python
stats = router.stats()
print(stats)
# {
#   "total_calls": 42,
#   "total_cost_usd": 0.0315,
#   "total_input_tokens": 12600,
#   "total_output_tokens": 4200,
#   "hooks": {
#     "moderate": {"calls": 42, "cost_usd": 0.0315, "fallbacks": 2, ...}
#   }
# }
```

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

## License

MIT — MavPro Group LLC
```

- [ ] **Step 3: Commit**

```bash
git add examples/content_moderation.py README.md
git commit -m "docs: add content moderation example and README"
```

- [ ] **Step 4: Run full test suite one final time**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass. Phase 1 complete.

- [ ] **Step 5: Tag the release**

```bash
git tag v0.1.0-alpha
```

---

## Phase 1 Complete Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Example runs (with mocked provider or real API key)
- [ ] `pip install -e .` works
- [ ] Public API exports are clean: `from clawd_hooks import HookRouter, HookContext`
- [ ] sync and async both work
- [ ] All four fallback strategies work
- [ ] Stats tracking works
- [ ] README is accurate

---

# Phases 2–7 Roadmap

These phases build on Phase 1. Each will get its own detailed plan when we begin it.

## Phase 2: Budget Engine & Circuit Breaker

**Goal:** Prevent cost overruns and handle API outages gracefully.

**Files:**
- `src/clawd_hooks/budget.py` — Token bucket rate limiter, per-hook + global budgets
- `src/clawd_hooks/circuit.py` — Circuit breaker (closed/open/half-open)
- Modify: `router.py` — Wire budget gate + circuit breaker into lifecycle Step 2 (Gate)

**Key features:**
- Per-hook `calls_per_hour` and `tokens_per_hour` limits
- Global `max_cost_per_hour` and `max_cost_per_day` on the router
- Circuit breaker: trips after N consecutive failures, auto-recovers after cooldown
- Budget gate runs before API call — hook falls back immediately if over budget

**Estimated:** ~600 LOC + tests

---

## Phase 3: Caching & Model Routing

**Goal:** Reduce costs through caching and smart model selection.

**Files:**
- `src/clawd_hooks/cache.py` — LRU cache + hash-based semantic cache
- `src/clawd_hooks/routing.py` — Confidence-based model escalation
- Modify: `fallbacks.py` — Add `cache` and `cascade` strategies

**Key features:**
- LRU cache with configurable TTL per hook
- Hash-based similarity for stable classification hooks
- `cache` fallback strategy: return last cached response on failure
- `cascade` fallback: degrade to cheaper model (Opus → Sonnet → Haiku)
- Confidence-based escalation: start with Haiku, promote to Sonnet if `confidence < threshold`

**Estimated:** ~800 LOC + tests

---

## Phase 4: Telemetry & Observability

**Goal:** Production-grade observability via OpenTelemetry.

**Files:**
- `src/clawd_hooks/telemetry.py` — OTel spans, metrics, GenAI semantic conventions

**Key features:**
- Span per hook invocation: `hook.moderate claude-sonnet-4-6`
- Standard GenAI attributes: `gen_ai.usage.input_tokens`, etc.
- Custom attributes: `hook.name`, `hook.fallback_strategy`, `hook.cache_hit`
- Metrics export: `hook.cost.usd`, `hook.fallback.count`, `gen_ai.client.operation.duration`
- Opt-in content capture for debugging
- Compatible with Langfuse, Helicone, Prometheus, Grafana, Datadog, etc.

**Estimated:** ~500 LOC + tests

---

## Phase 5: Framework Adapters

**Goal:** Drop-in integration with FastAPI, Django, and Celery.

**Files:**
- `src/clawd_hooks/adapters/fastapi.py` — Middleware + dependency injection
- `src/clawd_hooks/adapters/django.py` — Django middleware class
- `src/clawd_hooks/adapters/celery.py` — Celery task decorator wrapper

**Key features:**
- FastAPI: `app.add_middleware(ClawdHooksMiddleware, router=router)` auto-hooks request handlers
- Django: `MIDDLEWARE = ["clawd_hooks.adapters.django.ClawdHooksMiddleware"]`
- Celery: `@router.celery_hook(model="haiku")` wraps Celery tasks

**Estimated:** ~800 LOC + tests

---

## Phase 6: PII Filtering & OpenAI Provider

**Goal:** Enterprise data governance + multi-provider support.

**Files:**
- `src/clawd_hooks/pii.py` — PII detection/anonymization (optional dependency)
- `src/clawd_hooks/providers/openai.py` — OpenAI GPT provider

**Key features:**
- PII pre-filter: detect and tokenize PII before sending to Claude
- PII post-filter: restore original identifiers in responses
- Optional install: `pip install claude-hooks[pii]`
- OpenAI provider: GPT-4o, o3, etc. via same `LLMProvider` interface
- Model aliases: `"gpt4o"`, `"o3"`, etc.

**Estimated:** ~800 LOC + tests

---

## Phase 7: Examples, Docs & PyPI

**Goal:** Ship it. Seven complete examples, Sphinx docs, PyPI package.

**Files:**
- `examples/` — 6 more complete demos (data pipeline, code review, triage, extraction, decision engine, anomaly detection)
- `docs/` — Sphinx documentation with tutorials
- Finalize `pyproject.toml`, `CHANGELOG.md`

**Key deliverables:**
- Each example is a self-contained script with README
- Sphinx docs with quickstart, API reference, tutorials
- `python -m build` produces wheel
- `twine upload` to PyPI
- GitHub repo with CI (GitHub Actions: lint, test, build)

**Estimated:** ~2,500 LOC

---

# Total Scope Across All Phases

| Phase | Focus | Est. LOC |
|-------|-------|----------|
| 1 | Core SDK (this plan) | ~1,300 |
| 2 | Budget + Circuit Breaker | ~600 |
| 3 | Caching + Routing | ~800 |
| 4 | Telemetry | ~500 |
| 5 | Framework Adapters | ~800 |
| 6 | PII + OpenAI | ~800 |
| 7 | Examples + Docs + PyPI | ~2,500 |
| **Total** | | **~7,300** |
