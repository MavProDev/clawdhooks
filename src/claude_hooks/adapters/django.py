"""Django middleware integration for claude-hooks."""
from __future__ import annotations

from typing import Any, Callable


class ClaudeHooksMiddleware:
    """Django middleware that attaches a HookRouter to each request.

    Usage in settings.py:
        CLAUDE_HOOKS_ROUTER = HookRouter(api_key="...")

        MIDDLEWARE = [
            ...
            'claude_hooks.adapters.django.ClaudeHooksMiddleware',
        ]

    Access in views:
        def my_view(request):
            router = request.claude_hooks_router
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self._router = None

    def _get_router(self):
        if self._router is None:
            try:
                from django.conf import settings
                self._router = getattr(settings, "CLAUDE_HOOKS_ROUTER", None)
            except ImportError:
                pass
        return self._router

    def __call__(self, request: Any) -> Any:
        router = self._get_router()
        if router is not None:
            request.claude_hooks_router = router
        response = self.get_response(request)
        return response
