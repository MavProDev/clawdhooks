# claude-hooks

**Add Claude to any Python app in one line.**

claude-hooks is a Python SDK for injecting Claude as middleware into existing applications. Not as a chatbot. Not as an agent. As a decision-making layer inside your code.

## Install

```bash
pip install claude-hooks
```

## Quick Start

```python
import os
from pydantic import BaseModel
from claude_hooks import HookRouter

router = HookRouter(api_key=os.environ["ANTHROPIC_API_KEY"])

class ModerationResult(BaseModel):
    action: str    # "allow", "flag", or "block"
    reason: str

@router.hook(model="haiku", fallback="local")
async def moderate(content: str) -> ModerationResult:
    """Evaluate if this content violates community guidelines."""
    return ModerationResult(action="allow", reason="fallback")

# Async
result = await moderate("Hello world!")

# Sync (no async/await needed)
result = moderate.sync("Hello world!")
```

## How It Works

1. **Decorate** any function with `@router.hook()`
2. **Define** input (function params) and output (Pydantic return type)
3. **Write** the system prompt as the docstring
4. **Call** the function — Claude handles the rest

The function body is your **local fallback** — it runs when Claude is unavailable.

## Features

- **Typed I/O** — Pydantic models in, Pydantic models out. No JSON parsing.
- **Sync + Async** — `await moderate(post)` or `moderate.sync(post)`. Your choice.
- **Fallback strategies** — `skip`, `default`, `raise`, or `local` (your function body).
- **Auto retry** — Configurable retries on failure before falling back.
- **Cost tracking** — `router.stats()` shows tokens, cost, and latency per hook.
- **Prompt caching** — System prompts cached automatically (90% cost reduction).
- **Model routing** — Use `"haiku"` for fast/cheap, `"opus"` for high-stakes.

## Fallback Strategies

| Strategy | Behavior |
|----------|----------|
| `skip` | Returns `None`. Your code decides what to do. |
| `default` | Returns a pre-defined default response. |
| `raise` | Raises the error. Pipeline must halt. |
| `local` | Runs your function body as a fallback. |

```python
# "local" fallback — function body runs when Claude is down
@router.hook(model="sonnet", fallback="local")
async def classify(text: str) -> Classification:
    """Classify this text."""
    return Classification(label="unknown", confidence=0.0)  # fallback
```

## Stats

```python
stats = router.stats()
print(stats)
# {
#   "total_calls": 42,
#   "total_cost_usd": 0.0315,
#   "total_input_tokens": 12600,
#   "total_output_tokens": 4200,
#   "hooks": {
#     "moderate": {"calls": 42, "cost_usd": 0.0315, "fallbacks": 2, ...}
#   }
# }
```

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

## License

MIT — MavPro Group LLC
