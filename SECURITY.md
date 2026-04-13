# Security Policy

## Supported versions

claudehooks is currently in alpha (`0.x`). Only the latest released version receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report them privately using **GitHub's private security advisory feature**:

1. Go to https://github.com/MavProDev/claudehooks/security/advisories/new
2. Fill in the advisory form with as much detail as you can
3. Submit — only the maintainers will see it

### What to include

- A clear description of the vulnerability
- Steps to reproduce (or a minimal proof of concept)
- The affected version(s) of claudehooks
- The potential impact (what an attacker could do)
- Any suggested fix, if you have one

### What to expect

- **Acknowledgment**: within 72 hours
- **Initial assessment**: within 7 days
- **Fix timeline**: depends on severity — critical issues get a patched release ASAP; lower-severity issues are scheduled for the next regular release
- **Public disclosure**: coordinated with you, typically after a fix is available

### Scope

In-scope:
- The `claudehooks` Python package and its adapters (`fastapi`, `django`, `celery`)
- PII filtering logic
- Credential handling
- Prompt injection vectors specific to claudehooks' decorator pattern

Out-of-scope:
- Vulnerabilities in upstream dependencies (report those to the respective projects)
- General LLM safety issues unrelated to claudehooks' code
- Social engineering or physical attacks

## Security audit

claudehooks underwent a FORTRESS adversarial security audit (9 phases, 448 attack personas) in April 2026. All 27 identified findings were resolved before the v0.1.0 public release.

Thank you for helping keep claudehooks and its users safe.
