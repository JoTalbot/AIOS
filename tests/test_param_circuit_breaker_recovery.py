"""Parametrized circuit breaker recovery times."""
import pytest
from aios_core.circuit_breaker import CircuitBreaker, CircuitState
import time

@pytest.mark.parametrize("threshold", [1, 2, 3, 5])
def test_opens_after_threshold_failures(threshold):
    cb = CircuitBreaker(failure_threshold=threshold, recovery_timeout=0.01)
    for _ in range(threshold):
        try: cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        except ValueError: pass
    assert cb.state == CircuitState.OPEN
    time.sleep(0.02)
    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED

@pytest.mark.parametrize("successes", [1, 5, 10, 50])
def test_many_successes_keep_closed(successes):
    cb = CircuitBreaker(failure_threshold=5)
    for _ in range(successes):
        assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED
