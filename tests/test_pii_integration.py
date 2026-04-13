"""PII integration tests — PIIFilter wired into HookRouter pipeline."""
import pytest
from pydantic import BaseModel
from claude_hooks.router import HookRouter


class AnalysisResult(BaseModel):
    summary: str
    risk_level: str


@pytest.mark.asyncio
async def test_pii_filter_anonymizes_input(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"summary": "User at EMAIL_1 is safe", "risk_level": "low"})
    ]
    router = HookRouter(provider=mock_provider, pii_filter=True)

    @router.hook(model="sonnet")
    async def analyze(text: str) -> AnalysisResult:
        """Analyze this text."""
        ...

    result = await analyze("Contact john@example.com for details")

    # Verify the API received anonymized input
    call = mock_provider._calls[0]
    assert "john@example.com" not in call["user_message"]
    assert "EMAIL_1" in call["user_message"]


@pytest.mark.asyncio
async def test_pii_filter_deanonymizes_output(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"summary": "User at EMAIL_1 is safe", "risk_level": "low"})
    ]
    router = HookRouter(provider=mock_provider, pii_filter=True)

    @router.hook(model="sonnet")
    async def analyze(text: str) -> AnalysisResult:
        """Analyze this text."""
        ...

    result = await analyze("Contact john@example.com for details")

    # Result should have original email restored
    assert "john@example.com" in result.summary


@pytest.mark.asyncio
async def test_pii_filter_disabled_by_default(mock_provider, make_response):
    mock_provider._responses = [
        make_response(content={"summary": "all good", "risk_level": "low"})
    ]
    router = HookRouter(provider=mock_provider)  # pii_filter=False default

    @router.hook(model="sonnet")
    async def analyze(text: str) -> AnalysisResult:
        """Analyze this text."""
        ...

    await analyze("Contact john@example.com")

    # Without PII filter, raw email goes through
    call = mock_provider._calls[0]
    assert "john@example.com" in call["user_message"]
