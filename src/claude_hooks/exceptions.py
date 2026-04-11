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
