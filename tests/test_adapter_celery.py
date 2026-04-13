import pytest
from pydantic import BaseModel
from claudehooks.adapters.celery import hook_task


class TaskResult(BaseModel):
    status: str
    message: str


def test_hook_task_decorator_exists():
    assert callable(hook_task)


def test_hook_task_registers_hook(mock_provider, make_response):
    from claudehooks import HookRouter

    mock_provider._responses = [
        make_response(content={"status": "done", "message": "processed"})
    ]
    router = HookRouter(provider=mock_provider)

    @hook_task(router, model="haiku")
    def process(data: str) -> TaskResult:
        """Process this data."""
        return TaskResult(status="fallback", message="local")

    assert "process" in router.hooks


def test_hook_task_sync_call(mock_provider, make_response):
    from claudehooks import HookRouter

    mock_provider._responses = [
        make_response(content={"status": "done", "message": "processed"})
    ]
    router = HookRouter(provider=mock_provider)

    @hook_task(router, model="haiku")
    def process(data: str) -> TaskResult:
        """Process this data."""
        return TaskResult(status="fallback", message="local")

    result = process("test data")
    assert isinstance(result, TaskResult)
    assert result.status == "done"


def test_hook_task_fallback(mock_provider):
    from claudehooks import HookRouter

    mock_provider._responses = [Exception("fail")]
    router = HookRouter(provider=mock_provider)

    @hook_task(router, model="haiku", fallback="local", max_retries=0)
    def process(data: str) -> TaskResult:
        """Process this data."""
        return TaskResult(status="fallback", message="local")

    result = process("test")
    assert result.status == "fallback"
    assert result.message == "local"


@pytest.mark.asyncio
async def test_hook_task_async_access(mock_provider, make_response):
    from claudehooks import HookRouter

    mock_provider._responses = [
        make_response(content={"status": "done", "message": "async"})
    ]
    router = HookRouter(provider=mock_provider)

    @hook_task(router, model="haiku")
    def process(data: str) -> TaskResult:
        """Process this data."""
        ...

    result = await process.async_call("test")
    assert result.status == "done"
    assert result.message == "async"
