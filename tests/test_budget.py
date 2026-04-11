import time
import pytest
from claude_hooks.budget import BudgetTracker


def test_budget_tracker_allows_under_limit():
    tracker = BudgetTracker(calls_per_hour=10, tokens_per_hour=1000)
    assert tracker.check("hook_a") is True


def test_budget_tracker_blocks_over_call_limit():
    tracker = BudgetTracker(calls_per_hour=3, tokens_per_hour=100000)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    assert tracker.check("hook_a") is False


def test_budget_tracker_blocks_over_token_limit():
    tracker = BudgetTracker(calls_per_hour=1000, tokens_per_hour=100)
    tracker.record("hook_a", input_tokens=60, output_tokens=50, cost_usd=0.01)
    assert tracker.check("hook_a") is False


def test_budget_tracker_independent_per_hook():
    tracker = BudgetTracker(calls_per_hour=2, tokens_per_hour=100000)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    tracker.record("hook_a", input_tokens=10, output_tokens=5, cost_usd=0.001)
    assert tracker.check("hook_a") is False
    assert tracker.check("hook_b") is True


def test_budget_tracker_global_cost_limit():
    tracker = BudgetTracker(
        calls_per_hour=1000,
        tokens_per_hour=1000000,
        global_max_cost_per_hour=0.05,
    )
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.03)
    tracker.record("hook_b", input_tokens=100, output_tokens=50, cost_usd=0.03)
    assert tracker.check("hook_a") is False
    assert tracker.check("hook_b") is False


def test_budget_tracker_no_limits_always_allows():
    tracker = BudgetTracker()
    for _ in range(100):
        tracker.record("hook_a", input_tokens=1000, output_tokens=500, cost_usd=1.0)
    assert tracker.check("hook_a") is True


def test_budget_tracker_remaining():
    tracker = BudgetTracker(calls_per_hour=10, tokens_per_hour=1000)
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.01)
    remaining = tracker.remaining("hook_a")
    assert remaining["calls"] == 9
    assert remaining["tokens"] == 850


def test_budget_tracker_reset():
    tracker = BudgetTracker(calls_per_hour=3, tokens_per_hour=1000)
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.01)
    tracker.record("hook_a", input_tokens=100, output_tokens=50, cost_usd=0.01)
    tracker.reset("hook_a")
    assert tracker.check("hook_a") is True
    remaining = tracker.remaining("hook_a")
    assert remaining["calls"] == 3
