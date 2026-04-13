# Known Patterns

This file records project-specific patterns identified across FORTRESS audits. Patterns are advisory only — they inform validation but never suppress findings.

---

### PATTERN-001
- **Type:** architecture-decision
- **Scope:** `src/clawd_hooks/**`
- **Description:** claude-hooks is an SDK library, not a service. It has no auth model of its own. API keys are passed as parameters to providers and held in memory only for the lifetime of the router instance.
- **First recorded:** 2026-04-12
- **Last confirmed:** 2026-04-12
- **Audit count:** 1
- **Confidence:** high
- **Decay status:** active

### PATTERN-002
- **Type:** architecture-decision
- **Scope:** `src/clawd_hooks/router.py`
- **Description:** Docstrings are intentionally used as system prompts (by design — the whole point of the SDK). Developers must understand their function docstrings become LLM system prompts and should not contain secrets.
- **First recorded:** 2026-04-12
- **Last confirmed:** 2026-04-12
- **Audit count:** 1
- **Confidence:** high
- **Decay status:** active

### PATTERN-003
- **Type:** framework-behavior
- **Scope:** `src/clawd_hooks/providers/**`
- **Description:** Both Claude (tool_use) and OpenAI (json_schema strict) providers use structured output enforcement. Pydantic validates response shape. String VALUES inside validated fields are still untrusted and should be sanitized by the user's Pydantic field_validators before use in SQL/HTML/commands.
- **First recorded:** 2026-04-12
- **Last confirmed:** 2026-04-12
- **Audit count:** 1
- **Confidence:** high
- **Decay status:** active
