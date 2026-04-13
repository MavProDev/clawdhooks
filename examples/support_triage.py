"""
Customer Support Triage
=======================

Demonstrates claude-hooks for classifying support tickets by urgency,
category, and suggesting responses.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/support_triage.py
"""
import asyncio
import os

from pydantic import BaseModel

from claudehooks import HookRouter


class SupportTicket(BaseModel):
    subject: str
    body: str
    sender: str
    account_tier: str  # "free", "pro", "enterprise"


class TriageResult(BaseModel):
    urgency: str  # "low", "medium", "high", "critical"
    category: str
    sentiment: str  # "positive", "neutral", "frustrated", "angry"
    suggested_response: str
    escalate: bool


router = HookRouter(
    api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    calls_per_hour=120,
    cache_enabled=True,
    cache_ttl_seconds=600,
)


@router.hook(model="sonnet", fallback="local")
async def triage(ticket: SupportTicket) -> TriageResult:
    """You are a customer support triage system.

    Classify each ticket by:
    - urgency: "low" (general question), "medium" (issue affecting workflow),
      "high" (service disruption), "critical" (data loss or security)
    - category: billing, technical, account, feature_request, bug_report, other
    - sentiment: detect the customer's emotional state
    - suggested_response: a brief, empathetic first response
    - escalate: true if this needs human attention immediately

    Consider account_tier when assessing urgency:
    - enterprise tickets are always at least "medium" urgency
    - critical issues for any tier should be escalated
    """
    # Local fallback: keyword-based triage
    urgency = "medium" if ticket.account_tier == "enterprise" else "low"
    body_lower = ticket.body.lower()
    if any(w in body_lower for w in ["urgent", "down", "broken", "emergency"]):
        urgency = "high"
    category = "technical" if any(w in body_lower for w in ["error", "bug", "crash"]) else "other"

    return TriageResult(
        urgency=urgency,
        category=category,
        sentiment="neutral",
        suggested_response="Thank you for contacting support. We're looking into this.",
        escalate=urgency in ("high", "critical"),
    )


async def main():
    tickets = [
        SupportTicket(
            subject="Can't login",
            body="I keep getting an error when trying to login. It says 'invalid credentials' but my password is correct. This is urgent - I have a demo in 2 hours!",
            sender="frustrated_user@company.com",
            account_tier="enterprise",
        ),
        SupportTicket(
            subject="Feature request: dark mode",
            body="Would love to see a dark mode option. The current white theme is hard on the eyes during late-night coding sessions.",
            sender="nightowl@dev.io",
            account_tier="pro",
        ),
        SupportTicket(
            subject="Billing discrepancy",
            body="I was charged $49.99 but my plan should be $29.99. Please fix this immediately or I'm canceling.",
            sender="angry_customer@email.com",
            account_tier="free",
        ),
    ]

    for ticket in tickets:
        result = await triage(ticket)
        print(f"[{result.urgency.upper()}] {ticket.subject} ({ticket.sender})")
        print(f"  Category: {result.category} | Sentiment: {result.sentiment}")
        print(f"  Escalate: {'YES' if result.escalate else 'no'}")
        print(f"  Response: {result.suggested_response}")
        print()

    stats = router.stats()
    print(f"--- Stats: {stats['total_calls']} calls, ${stats['total_cost_usd']:.6f} ---")


if __name__ == "__main__":
    asyncio.run(main())
