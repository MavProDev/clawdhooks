import pytest
from claudehooks.adapters.fastapi import ClaudeHooksMiddleware, get_router

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


def test_middleware_class_exists():
    assert ClaudeHooksMiddleware is not None


def test_get_router_exists():
    assert callable(get_router)


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_middleware_attaches_router(mock_provider, make_response):
    from claudehooks import HookRouter

    mock_provider._responses = [make_response(content={"sentiment": "positive", "score": 0.9})]
    router = HookRouter(provider=mock_provider)

    app = FastAPI()
    app.add_middleware(ClaudeHooksMiddleware, router=router)

    class SentimentResult(BaseModel):
        sentiment: str
        score: float

    @router.hook(model="haiku")
    async def analyze(text: str) -> SentimentResult:
        """Analyze sentiment."""
        ...

    @app.post("/analyze")
    async def analyze_endpoint(text: str):
        result = await analyze(text)
        return {"sentiment": result.sentiment, "score": result.score}

    client = TestClient(app)
    response = client.post("/analyze?text=great")
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"] == "positive"


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_middleware_handles_hook_errors(mock_provider):
    from claudehooks import HookRouter

    mock_provider._responses = [Exception("API down")]
    router = HookRouter(provider=mock_provider)

    app = FastAPI()
    app.add_middleware(ClaudeHooksMiddleware, router=router)

    class Result(BaseModel):
        answer: str

    @router.hook(model="sonnet", fallback="skip", max_retries=0)
    async def decide(q: str) -> Result:
        """Answer."""
        ...

    @app.get("/decide")
    async def decide_endpoint(q: str):
        result = await decide(q)
        if result is None:
            return {"answer": "unavailable"}
        return {"answer": result.answer}

    client = TestClient(app)
    response = client.get("/decide?q=test")
    assert response.status_code == 200
    assert response.json()["answer"] == "unavailable"


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
def test_get_router_dependency(mock_provider, make_response):
    from fastapi import FastAPI, Depends, Request
    from claudehooks import HookRouter

    router = HookRouter(provider=mock_provider)

    app = FastAPI()
    app.add_middleware(ClaudeHooksMiddleware, router=router)

    @app.get("/stats")
    async def stats_endpoint(hook_router: HookRouter = Depends(get_router)):
        return hook_router.stats()

    client = TestClient(app)
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_calls" in data
