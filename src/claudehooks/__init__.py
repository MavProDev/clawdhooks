"""claudehooks: Add Claude as middleware to any Python app with a single decorator."""
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
from .pii import PIIFilter
from .cache import HookCache
from .telemetry import HookTelemetry
from .budget import BudgetTracker
from .circuit import CircuitBreaker, CircuitState

# OpenAI provider — optional, requires: pip install claudehooks[openai]
try:
    from .providers.openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None  # type: ignore[assignment,misc]

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
    "OpenAIProvider",
    # Exceptions
    "HookError",
    "HookTimeoutError",
    "HookBudgetError",
    "HookValidationError",
    "HookProviderError",
    # Advanced features
    "PIIFilter",
    "HookCache",
    "HookTelemetry",
    "BudgetTracker",
    "CircuitBreaker",
    "CircuitState",
    # Version
    "__version__",
]
