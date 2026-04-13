# Contributing to claudehooks

Thanks for your interest in contributing! This document covers how to set up a dev environment, run the tests, and submit changes.

## Quick setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/claudehooks.git
cd claudehooks

# 2. Create a virtual environment (Python 3.11+)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev extras
pip install -e ".[dev]"

# 4. Verify everything works
pytest
ruff check src tests
```

If `pytest` passes and `ruff` is clean, you're ready to go.

## Running the tests

```bash
# Full test suite with coverage
pytest --cov=claudehooks --cov-report=term-missing

# A single file
pytest tests/test_router.py -v

# A single test
pytest tests/test_router.py::test_hook_decorator_basic -v
```

Tests should **never** make real network calls to Anthropic or OpenAI. If you need LLM-like behavior in a test, mock it at the provider boundary.

## Linting and formatting

```bash
# Check
ruff check src tests

# Auto-fix
ruff check src tests --fix
```

We use `ruff` for both linting and import sorting. Configuration is in `pyproject.toml`.

## Submitting a change

1. **Open an issue first** for anything non-trivial — it saves both of us time if the change isn't a good fit.
2. **Create a branch** named `feat/short-description`, `fix/short-description`, or `docs/short-description`.
3. **Write tests** for new behavior or bug fixes. Coverage should not drop.
4. **Keep commits focused** — one logical change per commit. No drive-by reformatting.
5. **Update the README** if you add or change a public API.
6. **Open a PR** against `master` using the PR template.

## What we look for in PRs

- ✅ Clear motivation and scope
- ✅ Tests for new or changed behavior
- ✅ No new dependencies without discussion
- ✅ Public API changes documented
- ✅ Passes CI on Python 3.11, 3.12, and 3.13

## What we'll push back on

- ❌ Adding features that don't have a clear use case
- ❌ Sprawling refactors bundled with bug fixes
- ❌ Breaking public APIs without a migration path
- ❌ Silently catching exceptions or hiding errors
- ❌ "Clever" code that saves 2 lines but costs clarity

## Code of Conduct

By participating in this project, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Found a vulnerability? **Do not open a public issue.** See [SECURITY.md](SECURITY.md) for how to report it privately.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
