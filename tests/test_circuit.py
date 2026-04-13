import time
import pytest
from claudehooks.circuit import CircuitBreaker, CircuitState


def test_initial_state_is_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.is_closed


def test_stays_closed_under_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED


def test_opens_at_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_open


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


def test_open_circuit_allows_check_returns_false():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.should_allow() is False


def test_closed_circuit_allows_check_returns_true():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
    assert cb.should_allow() is True


def test_half_open_after_recovery_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    time.sleep(0.15)
    assert cb.should_allow() is True
    assert cb.state == CircuitState.HALF_OPEN


def test_half_open_success_closes():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    cb.should_allow()
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    cb.should_allow()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_reset():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


def test_stats():
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=5.0)
    cb.record_success()
    cb.record_success()
    cb.record_failure()
    stats = cb.stats()
    assert stats["state"] == "closed"
    assert stats["consecutive_failures"] == 1
    assert stats["total_successes"] == 2
    assert stats["total_failures"] == 1
