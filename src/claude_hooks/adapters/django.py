"""Django middleware integration for claude-hooks."""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


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
                if self._router is None:
                    logger.warning(
                        "CLAUDE_HOOKS_ROUTER not found in Django settings. "
                        "Claude hooks will not be available."
                    )
            except ImportError:
                logger.error("Django not available — cannot load CLAUDE_HOOKS_ROUTER")
        return self._router

    def __call__(self, request: Any) -> Any:
        router = self._get_router()
        if router is not None:
            request.claude_hooks_router = router
        response = self.get_response(request)
        return response
