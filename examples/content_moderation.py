"""
Content Moderation Example
==========================

Demonstrates claude-hooks as middleware for moderating user-generated content.
Claude evaluates each post and returns allow/flag/block with reasoning.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/content_moderation.py
"""
import asyncio
import os

from pydantic import BaseModel

from claudehooks import HookRouter


# --- Schemas ---

class UserPost(BaseModel):
    title: str
    content: str
    author: str


class ModerationResult(BaseModel):
    action: str  # "allow", "flag", or "block"
    reason: str
    confidence: float


# --- Setup ---

router = HookRouter(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# --- Hook ---

@router.hook(model="haiku", fallback="local")
async def moderate(post: UserPost) -> ModerationResult:
    """You are a content moderator for an online community.

    Evaluate the post against these guidelines:
    - No hate speech, harassment, or threats
    - No spam or commercial solicitation
    - No explicit or graphic content

    Return your decision:
    - action: "allow" (clean), "flag" (needs human review), or "block" (clear violation)
    - reason: Brief explanation of your decision
    - confidence: 0.0 to 1.0 how confident you are
    """
    # Local fallback: keyword-based filter when Claude is unavailable
    blocked_words = ["spam", "buy now", "click here"]
    if any(word in post.content.lower() for word in blocked_words):
        return ModerationResult(action="flag", reason="keyword match", confidence=0.3)
    return ModerationResult(action="allow", reason="no keywords matched", confidence=0.2)


# --- Main ---

async def main():
    posts = [
        UserPost(title="Hello!", content="Just saying hi to everyone.", author="newuser"),
        UserPost(title="Great community", content="Love this place!", author="regular"),
        UserPost(
            title="Check this out",
            content="Buy now! Amazing deal click here!!!",
            author="spammer",
        ),
    ]

    for post in posts:
        result = await moderate(post)
        print(f"[{result.action.upper()}] '{post.title}' by {post.author}")
        print(f"  Reason: {result.reason} (confidence: {result.confidence})")
        print()

    # Print stats
    stats = router.stats()
    print("--- Stats ---")
    print(f"Total calls: {stats['total_calls']}")
    print(f"Total cost:  ${stats['total_cost_usd']:.6f}")
    print(f"Tokens used: {stats['total_input_tokens']} in / {stats['total_output_tokens']} out")


if __name__ == "__main__":
    asyncio.run(main())
