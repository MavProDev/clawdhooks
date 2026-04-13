"""FastAPI/Starlette integration for claude-hooks."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..router import HookRouter

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class ClaudeHooksMiddleware(BaseHTTPMiddleware):
        """Starlette/FastAPI middleware that attaches a HookRouter to request state.

        Usage:
            app = FastAPI()
            router = HookRouter(api_key="...")
            app.add_middleware(ClaudeHooksMiddleware, router=router)
        """

        def __init__(self, app, *, router: HookRouter):
            super().__init__(app)
            self.router = router

        async def dispatch(self, request: Request, call_next):
            request.state.claudehooks_router = self.router
            response = await call_next(request)
            return response

    async def get_router(request: Request):
        """FastAPI dependency that retrieves the HookRouter from request state.

        Usage:
            @app.get("/stats")
            async def stats(router: HookRouter = Depends(get_router)):
                return router.stats()
        """
        router = getattr(request.state, "claudehooks_router", None)
        if router is None:
            raise RuntimeError(
                "HookRouter not found on request. "
                "Add ClaudeHooksMiddleware to your FastAPI app."
            )
        return router

except ImportError:

    class ClaudeHooksMiddleware:  # type: ignore[no-redef]
        """Stub when FastAPI/Starlette is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "FastAPI/Starlette is required for ClaudeHooksMiddleware. "
                "Install with: pip install claudehooks[fastapi]"
            )

    async def get_router(request=None):  # type: ignore[misc]
        """Stub when FastAPI is not installed."""
        raise ImportError(
            "FastAPI/Starlette is required for get_router. "
            "Install with: pip install claudehooks[fastapi]"
        )
