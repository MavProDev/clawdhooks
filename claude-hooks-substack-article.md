---
**SEO Title:** claude-hooks: Add Claude to Any Python App in One Line
**Subtitle:** The gap between "build an agent" and "use the raw API" that nobody filled. Until now.
**Meta Description:** claude-hooks is an open-source Python SDK that adds Claude to existing applications as middleware via decorators. One decorator, one schema, typed I/O, budget controls, fallbacks, telemetry. Not an agent. Not a chatbot. Middleware.
**URL Slug:** claude-hooks-add-claude-to-any-python-app
**Substack Tags:** Python, AI, Claude, Open Source, Developer Tools, Middleware, SDK
**Author:** @ReelDad
---

# claude-hooks: Add Claude to Any Python App in One Line

There are 23 million Python developers in the world.

Most of them are not building AI agents.

They have web servers. Data pipelines. Monitoring systems. CI/CD tools. Content platforms. Applications that already work. Applications that already ship. Applications that already make money.

They want Claude to make one decision. Maybe two. Content moderation on user posts. Anomaly detection on incoming data. Triage on support tickets. Structured extraction from documents. A yes/no/wait on a fraud check.

That's it. No chain-of-thought reasoning loop. No tool-calling agent with memory and goals. No graph of nodes orchestrating a multi-step workflow. Just a function call that goes to Claude and comes back typed.

There is no good way to do this today.

That's the problem.

---

## The Binary

The AI tooling ecosystem offers two options.

**Option A: Raw API.** You write the HTTP call yourself. You write the retry logic. You write the JSON parsing. You write the error handling. You write the cost tracking. You write the timeout management. You write the fallback behavior. You write the observability instrumentation. You do this for every function that needs Claude. Every team does this independently. Every team makes different mistakes.

**Option B: Agent framework.** LangChain. CrewAI. Claude Agent SDK. You adopt the framework. You restructure your application around its abstractions. You learn its chain syntax or graph topology or agent loop. You accept its dependency tree. You accept its opinions about how your code should be organized. You get features you did not ask for and cannot easily remove.

A 480-point Hacker News thread on LangChain captured it precisely. One developer noted the pattern: standard use cases work, but the moment you need something original, you navigate five layers of abstraction to change a minute detail. Another developer put it more directly: most LLM applications require nothing more than string handling, API calls, loops, and maybe a vector database.

The gap between Option A and Option B is where most developers live. It is also where most AI projects die. MIT research puts the failure rate of GenAI pilots reaching production at 95%.

---

## The SDK

I am building **claude-hooks**. An open-source Python SDK. Three primitives. No framework.

```python
from claude_hooks import hook, HookRouter

router = HookRouter(api_key=os.environ["ANTHROPIC_API_KEY"])

@router.hook(
    model="claude-sonnet-4-6",
    timeout_ms=2000,
    fallback="skip"
)
async def moderate_content(content: UserPost) -> ModerationResult:
    """Claude decides if this post violates community guidelines."""
    ...

# In your request handler:
result = await moderate_content(post)
if result.action == "block":
    return Response(status=403, body=result.reason)
```

That's the entire integration. `@router.hook` is a decorator. `UserPost` and `ModerationResult` are Pydantic models. The SDK handles prompt assembly, API calls, schema validation, retries, caching, cost tracking, model routing, fallbacks, and OpenTelemetry telemetry. Your code does not change shape. Your architecture does not change shape. You added Claude to a function.

The decorator pattern is not new. Flask uses `@app.route`. Celery uses `@app.task`. FastAPI uses `@app.middleware`. Tenacity uses `@retry`. Developers understand this. There is nothing to learn except where to put the decorator and what schema to define.

---

## What Ships

**HookRouter.** One per application. Manages all hooks. Enforces budgets. Tracks costs. Handles fallbacks. Exports telemetry.

**@hook decorator.** Turns any function into a Claude injection point. Defines model, timeout, fallback strategy, budget limits, cache behavior, and permission scope. The function signature becomes the schema.

**HookContext.** The typed payload flowing through every hook. Carries runtime state in, structured decisions out.

**Six fallback strategies.** `skip` returns None. `cache` returns the last cached response. `default` returns a pre-defined response. `raise` throws an exception. `local` runs a local function. `cascade` escalates to a cheaper model. Your app never crashes because Claude is slow.

**Circuit breaker.** Three states: closed (normal), open (all requests route to fallback), half-open (test one request, close on success). LLM APIs go down. Your app does not.

**Model routing.** Not every decision needs Opus. Haiku at $1/MTok for classification. Sonnet at $3/MTok for extraction. Opus at $5/MTok for audits. Conditional escalation: start with Haiku, escalate to Sonnet if confidence drops below threshold. Research shows this achieves 95% of expensive-model performance using the expensive model for only 14% of queries.

**Framework adapters.** FastAPI, Celery, Django, MCP. Drop-in. No wrappers around wrappers.

---

## The Cost Math

AI costs kill projects silently. One engineering team plugged a model into their product assuming costs would stay negligible. Traffic settled at 1.2 million messages per day. The first full-month invoice came in near $15K. The second, $35K. By month three, $60K.

claude-hooks makes this structurally impossible.

Per-hook budgets. Global ceilings. Automatic model tiering. Prompt caching (90% reduction on system prompts). Semantic caching (61-69% hit rate on stable classifications). Batch mode (50% discount for non-urgent decisions). The full stack:

| Optimization Layer | Savings |
|---|---|
| Prompt caching | 90% on cached tokens |
| Model routing | 40-60% via Haiku default |
| Semantic caching | 60-70% on stable classifications |
| Batch API | 50% on non-urgent hooks |
| **Stacked maximum** | **~95% total reduction** |

Per-decision economics for a typical middleware call (2,000-token cached system prompt, 500-token input, 200-token JSON output):

| Model + Optimization | Cost Per Decision | vs Human ($5/decision) |
|---|---|---|
| Haiku 4.5 + batch + cache | $0.0009 | 5,556x cheaper |
| Sonnet 4.6 + batch + cache | $0.0026 | 1,923x cheaper |
| Opus 4.6 + batch + cache | $0.0044 | 1,136x cheaper |

Sub-penny decisions. That is the middleware value proposition.

---

## The Landscape

I researched every tool that touches this space. The findings are clear.

**Instructor** (11.7k GitHub stars, 3M+ monthly PyPI downloads) proves the demand. Pure structured extraction via Pydantic. Client patching, not decorators. No cost tracking, no fallbacks, no observability, no model routing.

**magentic** (2.4k stars) is the closest to the decorator pattern. Its `@prompt` decorator replaces a function body with an LLM call. Clean. No operational features. No budget controls. No circuit breakers.

**Mirascope** (~1.5k stars) calls itself "The LLM Anti-Framework." Provider-agnostic decorators. No middleware operations layer.

**Marvin** (6.1k stars) had the right decorators in v2 (`@ai_fn`, `@ai_model`). Then pivoted to agents in v3 with `marvin.cast()` and Threads. The decorator space lost its best contender.

**LangChain** (133k stars) dominates mindshare but generates the most complaints. Its middleware parameter in `create_agent()` is mutually exclusive with custom `state_schema`. It remains agent-centric.

**LiteLLM** (39.2k stars) is middleware but at the proxy layer. Routes between 100+ providers. Cost tracking per key. No application-level decorator integration.

**Pydantic AI** (16.2k stars) is the strongest bridge tool. Built by the Pydantic team. Lightweight enough for simple calls. Still oriented toward agent patterns with its `Agent()` abstraction.

| Tool | Best At | Missing For Middleware |
|---|---|---|
| Instructor | Structured extraction | Ops: cost, fallback, routing, telemetry |
| magentic | Decorator pattern | Ops: all of them |
| Mirascope | Provider-agnostic calls | Ops: all of them |
| LiteLLM | Provider routing/proxy | Application-level decorators |
| Pydantic AI | Type-safe AI bridge | Middleware focus, still agent-first |
| LangChain | Agent orchestration | Everything (too much for middleware) |
| **claude-hooks** | **All of the above** | **That's the point** |

---

## The Anthropic Observation

Anthropic's current SDK story is: build an agent, or use the raw API.

The Agent SDK (6.1k stars, v0.1.54) bundles the Claude Code CLI for autonomous agents. The base Python SDK (v0.93.0) provides `client.messages.create()` and tool use. Neither addresses the middleware use case.

MCP defines how Claude accesses external tools and data. claude-hooks defines how external tools and data access Claude. They are complementary. The MCP adapter makes every MCP tool a potential hook trigger, and every hook a potential MCP resource.

Every claude-hooks installation generates sustained, automated, high-volume API calls baked into production infrastructure. A single content moderation deployment generates more API revenue per month than thousands of chat users. The LLM market is projected to grow from $5.6B (2024) to $35.4B by 2030. Model API spending doubled from $3.5B to $8.4B in six months.

The economics work. The timing works.

---

## What Ships Day One

Seven complete example applications with tests, documented schemas, and READMEs:

1. **Content moderation.** FastAPI + Haiku. Falls back to keyword matching.
2. **Data pipeline anomaly detection.** Celery + batch mode.
3. **Code review gate.** GitHub Actions + PR review.
4. **Customer support triage.** Email classification + routing.
5. **Document extraction.** Invoice/contract structured extraction.
6. **Real-time decision engine.** Fraud detection with model escalation.
7. **FORTRESS codebase audit.** Each audit persona as a hook with typed I/O.

Total estimated scope: ~8,800 lines of code. One developer. Shippable in 3-4 weeks.

```
pip install claude-hooks
```

---

## The Pitch

Agent frameworks ask: "How do I build an AI app?"

claude-hooks asks: "How do I add AI to my app?"

That's 10x more developers.

One decorator. One schema. Claude is in your loop.

---

*@ReelDad builds tools for developers who ship. claude-hooks is open source under MavPro Group LLC.*
