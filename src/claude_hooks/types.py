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
    CACHE = "cache"      # Return last cached response for this hook
    CASCADE = "cascade"  # Try cheaper models before giving up


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
