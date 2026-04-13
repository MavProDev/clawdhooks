# claudehooks

**Add Claude to any Python app in one line.**

> Not as a chatbot. Not as an agent. As middleware.

claudehooks is a Python SDK for injecting Claude as a decision-making layer inside existing applications. Decorate any function, write the prompt as a docstring, and Claude handles the rest — with typed I/O, automatic fallbacks, cost controls, circuit breakers, caching, PII filtering, and full observability.

## Install

```bash
pip install claudehooks
```

## Quick Start

```python
import os
from pydantic import BaseModel
from claudehooks import HookRouter

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

# Sync (no event loop needed)
result = moderate.sync("Hello world!")
```

## How It Works

- **Decorate** any async function with `@router.hook()`
- **Define** input as function parameters and output as a Pydantic return type
- **Write** the system prompt as the function's docstring
- **Call** the function — Claude responds with a validated, typed result; the function body is your local fallback

## Features

### Typed I/O

Input parameters are serialized automatically. Return types are Pydantic models — no JSON parsing, no `.get("field")`, no `KeyError`.

```python
class ClassificationResult(BaseModel):
    label: str
    confidence: float
    tags: list[str]

@router.hook(model="sonnet")
async def classify(text: str, categories: list[str]) -> ClassificationResult:
    """Classify the text into one of the provided categories."""
    ...
```

### Sync + Async

Every hook exposes both calling styles:

```python
# Async (native)
result = await classify("Buy now!", ["spam", "promo", "normal"])

# Sync (no async/await, safe from any context)
result = classify.sync("Buy now!", ["spam", "promo", "normal"])
```

### Fallback Strategies

Six strategies control what happens when Claude is unavailable, times out, or exceeds budget:

| Strategy    | Behavior                                                        |
|-------------|-----------------------------------------------------------------|
| `skip`      | Returns `None` — your code decides what to do next             |
| `default`   | Returns a pre-defined `default_response` value                  |
| `raise`     | Raises the exception — pipeline halts                           |
| `local`     | Runs your function body as a local fallback                     |
| `cache`     | Returns the most recent cached response for this hook           |
| `cascade`   | Automatically degrades: opus → sonnet → haiku until one works   |

```python
# "local" — function body runs when Claude is unavailable
@router.hook(model="sonnet", fallback="local")
async def classify(text: str) -> Classification:
    """Classify this support ticket."""
    return Classification(label="general", confidence=0.0)  # fallback body

# "default" — return a fixed safe value
@router.hook(model="haiku", fallback="default",
             default_response={"action": "allow", "reason": "fallback"})
async def moderate(content: str) -> ModerationResult:
    """Evaluate this content."""
    ...

# "cascade" — try cheaper models automatically
@router.hook(model="opus", fallback="cascade")
async def summarize(doc: str) -> Summary:
    """Summarize this document."""
    ...
```

### Cost Control

Per-hook and global spending limits enforce a sliding 1-hour window. Hooks that exceed limits fall back immediately without calling the API.

```python
router = HookRouter(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    calls_per_hour=500,
    tokens_per_hour=200_000,
    global_max_cost_per_hour=5.00,   # USD
)
```

Use `BudgetTracker` directly for custom integrations:

```python
from claudehooks import BudgetTracker

tracker = BudgetTracker(calls_per_hour=100, global_max_cost_per_hour=2.0)
if tracker.check("my_hook"):
    tracker.record("my_hook", input_tokens=500, output_tokens=200, cost_usd=0.001)
remaining = tracker.remaining("my_hook")
```

### Circuit Breaker

Each hook has an independent circuit breaker. After `failure_threshold` consecutive failures, the circuit opens and requests are routed to fallback immediately — no API calls, no waiting. After `recovery_timeout` seconds, one test request is allowed through.

```python
router = HookRouter(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    circuit_failure_threshold=5,
    circuit_recovery_timeout=30.0,   # seconds
)
```

States: `CLOSED` (normal) → `OPEN` (all fallback) → `HALF_OPEN` (one probe) → `CLOSED`.

```python
from claudehooks import CircuitBreaker, CircuitState

cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
if cb.should_allow():
    # make request
    cb.record_success()
else:
    # use fallback
print(cb.stats())
# {"state": "closed", "consecutive_failures": 0, ...}
```

### Response Caching

LRU cache with TTL eliminates redundant API calls for identical inputs. Cache keys are SHA-256 hashes of normalized input. Cache hits are free and instant.

```python
router = HookRouter(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    cache_enabled=True,
    cache_max_size=256,
    cache_ttl_seconds=600.0,   # 10 minutes
)
```

Use `fallback="cache"` to serve stale responses when the API is unavailable:

```python
@router.hook(model="sonnet", fallback="cache")
async def analyze(text: str) -> Analysis:
    """Analyze this text."""
    ...
```

Use `HookCache` directly:

```python
from claudehooks import HookCache

cache = HookCache(max_size=128, ttl_seconds=300.0)
cache.put("input text", {"label": "spam"})
value = cache.get("input text")
```

### Model Cascade

`fallback="cascade"` automatically degrades through the Claude model family when the primary model fails, giving you the best answer you can get rather than an error:

```
opus → sonnet → haiku
```

If `model="sonnet"` and sonnet fails, haiku is tried next. If `model="opus"`, sonnet then haiku are tried. Results are cached on success.

### Observability

Full OpenTelemetry integration follows the [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/). Spans are emitted per hook invocation. Metrics track duration, cost, tokens, and fallbacks.

```python
router = HookRouter(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    telemetry_enabled=True,
)
```

Span attributes include:

- `hook.name`, `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`
- `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cached_tokens`
- `hook.cost_usd`, `hook.latency_ms`, `hook.retries`, `hook.used_fallback`, `hook.status`

Metrics emitted:

- `hook.duration_ms` — histogram of invocation latency
- `hook.cost_usd` — cumulative cost counter
- `hook.tokens` — cumulative token counter
- `hook.fallback_count` — fallback invocation counter

Requires: `pip install claudehooks[telemetry]`. Degrades to no-op when not installed.

```python
from claudehooks import HookTelemetry

telemetry = HookTelemetry(enabled=True)
span = telemetry.start_span("my_hook", "claude-haiku-3")
# ... do work ...
telemetry.end_span(span, ctx)
```

### PII Filtering

Anonymize sensitive data before it leaves your system. PII tokens are replaced before the API call and restored in the response.

```python
from claudehooks import PIIFilter

f = PIIFilter()
anonymized, mapping = f.anonymize("Contact john@example.com or call 555-123-4567")
# anonymized = "Contact EMAIL_1 or call PHONE_1"
# mapping = {"EMAIL_1": "john@example.com", "PHONE_1": "555-123-4567"}

restored = f.deanonymize(anonymized, mapping)
# restored = "Contact john@example.com or call 555-123-4567"
```

Detects: email addresses, phone numbers, SSNs, credit card numbers. Uses [Microsoft Presidio](https://microsoft.github.io/presidio/) when installed for broader coverage (50+ entity types), falls back to regex otherwise.

Requires: `pip install claudehooks[pii]` for Presidio. Regex detection works without it.

### Multi-Provider

Claude is the default. OpenAI GPT models are supported via the same decorator interface.

```python
from claudehooks import HookRouter, OpenAIProvider

openai_provider = OpenAIProvider(api_key=os.environ["OPENAI_API_KEY"])
router = HookRouter(provider=openai_provider)

@router.hook(model="gpt4o-mini", fallback="local")
async def classify(text: str) -> Classification:
    """Classify this text."""
    return Classification(label="unknown", confidence=0.0)
```

Supported OpenAI models: `gpt4o`, `gpt4o-mini`, `o3`, `o3-mini`.

Implement `LLMProvider` to add any other model:

```python
from claudehooks import LLMProvider, LLMResponse

class MyProvider(LLMProvider):
    @property
    def name(self) -> str: return "my-provider"
    def default_model(self) -> str: return "my-model"
    def resolve_model(self, model: str) -> str: return model
    def model_timeout(self, model: str) -> float: return 10.0
    async def complete(self, *, system_prompt, user_message,
                       output_schema, model, timeout_seconds, **kw) -> LLMResponse:
        ...
```

### Framework Adapters

**FastAPI** — attach the router as Starlette middleware and retrieve it as a dependency:

```python
from fastapi import FastAPI, Depends
from claudehooks.adapters.fastapi import ClaudeHooksMiddleware, get_router

app = FastAPI()
app.add_middleware(ClaudeHooksMiddleware, router=router)

@app.get("/stats")
async def stats(router=Depends(get_router)):
    return router.stats()
```

**Django** — configure in `settings.py`:

```python
# settings.py
from claudehooks import HookRouter
CLAUDE_HOOKS_ROUTER = HookRouter(api_key=os.environ["ANTHROPIC_API_KEY"])

MIDDLEWARE = [
    ...
    "claudehooks.adapters.django.ClaudeHooksMiddleware",
]

# views.py
def my_view(request):
    router = request.claudehooks_router
```

**Celery** — wrap tasks with `hook_task` for sync execution in workers:

```python
from claudehooks.adapters.celery import hook_task

@hook_task(router, model="haiku", fallback="local")
def process_ticket(ticket: SupportTicket) -> TriageResult:
    """Triage this support ticket."""
    return TriageResult(priority="low", team="general")

# Called as a normal sync function inside Celery tasks
result = process_ticket(ticket)
```

## Stats

`router.stats()` returns a complete breakdown of every hook, including budget headroom and circuit breaker state:

```python
stats = router.stats()
# {
#   "total_calls": 87,
#   "total_cost_usd": 0.0412,
#   "total_input_tokens": 24600,
#   "total_output_tokens": 8700,
#   "hooks": {
#     "moderate": {
#       "calls": 87, "cost_usd": 0.0412,
#       "input_tokens": 24600, "output_tokens": 8700,
#       "fallbacks": 3, "avg_latency_ms": 412.7
#     }
#   },
#   "budget": {
#     "moderate": {"calls": 413, "tokens": 175400}
#   },
#   "circuit_breakers": {
#     "moderate": {"state": "closed", "consecutive_failures": 0, ...}
#   }
# }
```

## Examples

Four working examples are included in `/examples`:

- **`content_moderation.py`** — Real-time content moderation with `skip` fallback and batch processing
- **`support_triage.py`** — Support ticket classification with priority routing and `local` fallback
- **`document_extraction.py`** — Structured data extraction from unstructured text using `sonnet`
- **`data_pipeline.py`** — High-throughput pipeline with caching, budget limits, and circuit breakers

## Optional Dependencies

```bash
pip install claudehooks[telemetry]   # OpenTelemetry spans + metrics
pip install claudehooks[pii]         # PII filtering via Microsoft Presidio
pip install claudehooks[openai]      # OpenAI GPT provider
pip install claudehooks[fastapi]     # FastAPI/Starlette middleware adapter
```

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

## License

MIT — MavPro Group LLC
