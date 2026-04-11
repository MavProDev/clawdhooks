import pytest
from claude_hooks.adapters.django import ClaudeHooksMiddleware


def test_django_middleware_class_exists():
    assert ClaudeHooksMiddleware is not None


def test_django_middleware_init():
    def mock_get_response(request):
        return "response"

    middleware = ClaudeHooksMiddleware(mock_get_response)
    assert middleware.get_response == mock_get_response


def test_django_middleware_attaches_router(mock_provider):
    from claude_hooks import HookRouter

    router = HookRouter(provider=mock_provider)

    def mock_get_response(request):
        # Verify router is attached
        assert hasattr(request, "claude_hooks_router")
        assert request.claude_hooks_router is router
        return "response"

    middleware = ClaudeHooksMiddleware(mock_get_response)
    middleware._router = router  # Simulate settings configuration

    class MockRequest:
        pass

    request = MockRequest()
    response = middleware(request)
    assert response == "response"


def test_django_middleware_works_without_router():
    def mock_get_response(request):
        assert not hasattr(request, "claude_hooks_router")
        return "response"

    middleware = ClaudeHooksMiddleware(mock_get_response)

    class MockRequest:
        pass

    response = middleware(MockRequest())
    assert response == "response"
