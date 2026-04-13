"""Integration test: end-to-end hook lifecycle with MockProvider."""
import pytest
from pydantic import BaseModel
from claudehooks import HookRouter, HookContext
from claudehooks.providers.base import LLMResponse
from claudehooks.exceptions import HookError, HookTimeoutError


class SupportTicket(BaseModel):
    subject: str
    body: str
    sender: str


class TriageResult(BaseModel):
    urgency: str
    category: str
    suggested_response: str


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float


@pytest.mark.asyncio
async def test_full_lifecycle_success(mock_provider, make_response):
    """Test the complete happy path: register hook, call it, get typed result."""
    mock_provider._responses = [
        make_response(
            content={
                "urgency": "high",
                "category": "billing",
                "suggested_response": "Escalate to billing team immediately.",
            },
            input_tokens=300,
            output_tokens=100,
            input_cost_per_mtok=3.0,
            output_cost_per_mtok=15.0,
        )
    ]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet")
    async def triage_ticket(ticket: SupportTicket) -> TriageResult:
        """You are a support ticket triage system. Classify the ticket by urgency
        (low/medium/high), category, and suggest a response."""
        ...

    ticket = SupportTicket(
        subject="Charged twice",
        body="I was charged twice for my subscription this month.",
        sender="angry_customer@example.com",
    )

    result = await triage_ticket(ticket)

    # Typed result
    assert isinstance(result, TriageResult)
    assert result.urgency == "high"
    assert result.category == "billing"

    # Stats recorded
    stats = router.stats()
    assert stats["total_calls"] == 1
    assert stats["total_cost_usd"] > 0
    assert stats["hooks"]["triage_ticket"]["calls"] == 1


@pytest.mark.asyncio
async def test_multiple_hooks_independent_stats(mock_provider, make_response):
    """Test that multiple hooks track stats independently."""
    mock_provider._responses = [
        make_response(content={"sentiment": "positive", "confidence": 0.95}),
        make_response(
            content={
                "urgency": "low",
                "category": "general",
                "suggested_response": "Standard reply.",
            }
        ),
        make_response(content={"sentiment": "negative", "confidence": 0.87}),
    ]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="haiku")
    async def analyze_sentiment(text: str) -> SentimentResult:
        """Analyze the sentiment of this text."""
        ...

    @router.hook(model="sonnet")
    async def triage(ticket: SupportTicket) -> TriageResult:
        """Triage this support ticket."""
        ...

    await analyze_sentiment("Great product!")
    await triage(SupportTicket(subject="Hi", body="Question", sender="user@test.com"))
    await analyze_sentiment("Terrible service")

    stats = router.stats()
    assert stats["total_calls"] == 3
    assert stats["hooks"]["analyze_sentiment"]["calls"] == 2
    assert stats["hooks"]["triage"]["calls"] == 1


@pytest.mark.asyncio
async def test_fallback_with_local_function(mock_provider):
    """Test that a real function body serves as local fallback."""
    mock_provider._responses = [Exception("API down")]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="sonnet", fallback="local")
    async def analyze_sentiment(text: str) -> SentimentResult:
        """Analyze sentiment."""
        # Simple keyword fallback
        if any(word in text.lower() for word in ["great", "good", "love"]):
            return SentimentResult(sentiment="positive", confidence=0.5)
        return SentimentResult(sentiment="neutral", confidence=0.3)

    result = await analyze_sentiment("Great product!")
    assert result.sentiment == "positive"
    assert result.confidence == 0.5

    stats = router.stats()
    assert stats["hooks"]["analyze_sentiment"]["fallbacks"] == 1


def test_sync_workflow(mock_provider, make_response):
    """Test the sync interface works without any async knowledge."""
    mock_provider._responses = [
        make_response(content={"sentiment": "positive", "confidence": 0.9})
    ]

    router = HookRouter(provider=mock_provider)

    @router.hook(model="haiku")
    async def analyze(text: str) -> SentimentResult:
        """Analyze sentiment."""
        ...

    # User calls .sync() — no async/await needed
    result = analyze.sync("Hello world")
    assert isinstance(result, SentimentResult)
    assert result.sentiment == "positive"
