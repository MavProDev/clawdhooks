# Coverage Map

## Audit: 2026-04-12

### Files Analyzed (19/19)
- src/clawd_hooks/__init__.py
- src/clawd_hooks/budget.py
- src/clawd_hooks/cache.py
- src/clawd_hooks/circuit.py
- src/clawd_hooks/context.py
- src/clawd_hooks/exceptions.py
- src/clawd_hooks/fallbacks.py
- src/clawd_hooks/pii.py
- src/clawd_hooks/router.py
- src/clawd_hooks/telemetry.py
- src/clawd_hooks/types.py
- src/clawd_hooks/adapters/__init__.py
- src/clawd_hooks/adapters/celery.py
- src/clawd_hooks/adapters/django.py
- src/clawd_hooks/adapters/fastapi.py
- src/clawd_hooks/providers/__init__.py
- src/clawd_hooks/providers/base.py
- src/clawd_hooks/providers/claude.py
- src/clawd_hooks/providers/openai.py

### CWE Categories Tested (20 of Top 25)
- CWE-20 (Input Validation) ✓
- CWE-74 (Injection) ✓
- CWE-77/78 (Command Injection) ✓
- CWE-79 (XSS) — N/A (SDK, not web UI)
- CWE-89 (SQL Injection) — N/A
- CWE-116 (Encoding/Escaping) ✓
- CWE-200 (Information Exposure) ✓
- CWE-209 (Error Message Info Exposure) ✓
- CWE-250 (Unnecessary Privileges) ✓
- CWE-327 (Broken Crypto) ✓
- CWE-345 (Integrity Verification) ✓
- CWE-353 (Missing Integrity Support) ✓
- CWE-362 (Race Condition) ✓
- CWE-400 (Uncontrolled Resource Consumption) ✓
- CWE-502 (Unsafe Deserialization) ✓
- CWE-532 (Log Info Leak) ✓
- CWE-704 (Incorrect Type Conversion) ✓
- CWE-754 (Improper Check for Exceptional Conditions) ✓
- CWE-770 (Allocation Without Limits) ✓
- CWE-916 (Weak Hash) ✓
- CWE-1104 (Unmaintained Third-Party) ✓
- CWE-1188 (Insecure Default) ✓
- CWE-1357 (Reliance on Insufficiently Trustworthy Component) ✓

### Domains with Zero Findings
(none — all tested squads produced findings)

### Under-Covered Areas
- **Memory safety (Squad 20)**: Not activated — Python-only codebase, no C/C++/Rust unsafe code
- **Blockchain/Web3 (Squad 16)**: Not activated — no relevant imports
- **Database (Squad 13)**: Not activated — SDK doesn't touch databases directly
- **Cloud/Container (Squad 17)**: Partial — no Dockerfile yet
- **OAuth/JWT/Sessions (Squad 10)**: Not activated — SDK has no auth layer

### Recommended Focus for Next Audit
- After adding CI/CD pipelines, re-audit with Squad 17 activated
- If adding a Docker image, activate container security checks
- Monitor for dependency CVEs via automated pip-audit runs
