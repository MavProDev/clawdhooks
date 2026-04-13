from clawdhooks.adapters.django import ClawdHooksMiddleware


def test_django_middleware_class_exists():
    assert ClawdHooksMiddleware is not None


def test_django_middleware_init():
    def mock_get_response(request):
        return "response"

    middleware = ClawdHooksMiddleware(mock_get_response)
    assert middleware.get_response == mock_get_response


def test_django_middleware_attaches_router(mock_provider):
    from clawdhooks import HookRouter

    router = HookRouter(provider=mock_provider)

    def mock_get_response(request):
        # Verify router is attached
        assert hasattr(request, "clawdhooks_router")
        assert request.clawdhooks_router is router
        return "response"

    middleware = ClawdHooksMiddleware(mock_get_response)
    middleware._router = router  # Simulate settings configuration

    class MockRequest:
        pass

    request = MockRequest()
    response = middleware(request)
    assert response == "response"


def test_django_middleware_works_without_router():
    def mock_get_response(request):
        assert not hasattr(request, "clawdhooks_router")
        return "response"

    middleware = ClawdHooksMiddleware(mock_get_response)

    class MockRequest:
        pass

    response = middleware(MockRequest())
    assert response == "response"
