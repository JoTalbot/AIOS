"""Full tests for circuit breaker pattern."""

from aios_core.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_half_open_transitions():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

    def failing():
        raise ValueError("fail")

    try:
        cb.call(failing)
    except ValueError:
        pass
    assert cb.state == CircuitState.OPEN
    import time
    time.sleep(0.02)
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    assert cb.state == CircuitState.CLOSED
