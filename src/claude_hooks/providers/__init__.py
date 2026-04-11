"""LLM provider abstractions."""
from .base import LLMProvider, LLMResponse
from .claude import ClaudeProvider

try:
    from .openai import OpenAIProvider
except ImportError:
    OpenAIProvider = None  # type: ignore[assignment,misc]

__all__ = ["LLMProvider", "LLMResponse", "ClaudeProvider", "OpenAIProvider"]
